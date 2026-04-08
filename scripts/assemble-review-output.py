#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
ASSETS_DIR = ROOT_DIR / "assets"
CLEAN_REPORT = "未发现值得报告的高置信度问题"
SEVERITY_ORDER = ["高级", "中级", "低级"]
SEVERITY_TO_COUNT_KEY = {
    "高级": "高危",
    "中级": "中危",
    "低级": "低危",
}
SEVERITY_TO_LABEL = {
    "高级": "高",
    "中级": "中",
    "低级": "低",
}
TYPE_ORDER = ["业务逻辑", "安全", "代码质量", "性能"]
LLM_USAGE_NOT_COLLECTED = {
    "collected": False,
    "reason": "本次审查未接入统一 usage 统计链路",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def clone_json_template(template_name: str) -> Any:
    return json.loads(json.dumps(load_json(ASSETS_DIR / template_name), ensure_ascii=False))


def normalize_issue(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": issue.get("title", ""),
        "type": issue.get("type", "代码质量"),
        "severity": issue.get("severity", "中级"),
        "description": issue.get("description", ""),
        "location": issue.get("location", ""),
        "start_line": int(issue.get("start_line") or 0),
        "end_line": int(issue.get("end_line") or 0),
        "evidence": issue.get("evidence", issue.get("description", "")),
        "suggestion": issue.get("suggestion", ""),
    }


def normalize_file_result(item: dict[str, Any]) -> dict[str, Any]:
    issues = [normalize_issue(issue) for issue in item.get("issues", [])]
    status_code = int(item.get("status_code") or (1 if issues else 0))
    report = item.get("report") or CLEAN_REPORT
    if not issues and status_code != 0:
        status_code = 0
    if not issues and report == "":
        report = CLEAN_REPORT
    return {
        "file_path": item.get("file_path", ""),
        "status_code": status_code,
        "issues": issues,
        "report": report,
    }


def severity_sort_key(issue: dict[str, Any]) -> int:
    severity = issue.get("severity", "低级")
    if severity in SEVERITY_ORDER:
        return SEVERITY_ORDER.index(severity)
    return len(SEVERITY_ORDER)


def count_issues(file_results: list[dict[str, Any]]) -> tuple[Counter[str], Counter[str], int, int]:
    severity_counter: Counter[str] = Counter({"高危": 0, "中危": 0, "低危": 0})
    type_counter: Counter[str] = Counter({key: 0 for key in TYPE_ORDER})
    issue_count = 0
    failed_count = 0

    for file_result in file_results:
        if file_result["status_code"] != 0:
            failed_count += 1
        for issue in file_result["issues"]:
            issue_count += 1
            severity_counter[SEVERITY_TO_COUNT_KEY.get(issue["severity"], "低危")] += 1
            type_counter[issue.get("type", "代码质量")] += 1

    return severity_counter, type_counter, issue_count, failed_count


def make_priority_summary_table(severity_counter: Counter[str]) -> str:
    rows = [
        ("高", severity_counter["高危"]),
        ("中", severity_counter["中危"]),
        ("低", severity_counter["低危"]),
    ]
    return "\n".join(f"| {label} | {count} |" for label, count in rows)


def make_risk_type_table(type_counter: Counter[str]) -> str:
    return "\n".join(f"| {issue_type} | {type_counter[issue_type]} |" for issue_type in TYPE_ORDER)


def file_issue_stats(file_result: dict[str, Any]) -> tuple[int, int, int, int, str]:
    high = sum(1 for issue in file_result["issues"] if issue["severity"] == "高级")
    medium = sum(1 for issue in file_result["issues"] if issue["severity"] == "中级")
    low = sum(1 for issue in file_result["issues"] if issue["severity"] == "低级")
    top_type = file_result["issues"][0]["type"] if file_result["issues"] else "无"
    return len(file_result["issues"]), high, medium, low, top_type


def make_file_issue_summary_table(file_results: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for file_result in file_results:
        total, high, medium, low, top_type = file_issue_stats(file_result)
        rows.append(
            f"| {file_result['file_path']} | {total} | {high} | {medium} | {low} | {top_type} |"
        )
    return "\n".join(rows) if rows else "| 无 | 0 | 0 | 0 | 0 | 无 |"


def flatten_issues(file_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for file_result in file_results:
        for issue in sorted(file_result["issues"], key=severity_sort_key):
            flattened.append({"file_path": file_result["file_path"], "issue": issue})
    return flattened


def make_global_key_findings(flattened_issues: list[dict[str, Any]]) -> str:
    if not flattened_issues:
        return f"- **{CLEAN_REPORT}**"
    findings: list[str] = []
    for index, entry in enumerate(flattened_issues[:5], start=1):
        issue = entry["issue"]
        findings.append(
            f"{index}. **{issue['title']}**（`{entry['file_path']}`，{SEVERITY_TO_LABEL.get(issue['severity'], '低')}）- {issue['description']}"
        )
    return "\n".join(findings)


def make_issues_table(flattened_issues: list[dict[str, Any]]) -> str:
    if not flattened_issues:
        return f"| 1 | {CLEAN_REPORT} | - | - | - | - | - | - |"
    rows: list[str] = []
    for index, entry in enumerate(flattened_issues, start=1):
        issue = entry["issue"]
        rows.append(
            "| {index} | {title} | {file_path} | {location} | {issue_type} | {severity} | {impact} | {suggestion} |".format(
                index=index,
                title=issue["title"].replace("|", "\\|"),
                file_path=entry["file_path"].replace("|", "\\|"),
                location=issue["location"].replace("|", "\\|"),
                issue_type=issue["type"],
                severity=SEVERITY_TO_LABEL.get(issue["severity"], "低"),
                impact=issue["description"].replace("|", "\\|"),
                suggestion=issue["suggestion"].replace("|", "\\|"),
            )
        )
    return "\n".join(rows)


def make_repo_file_report_index(file_results: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for index, file_result in enumerate(file_results, start=1):
        relative_report = Path("review_output") / f"{file_result['file_path']}_review.json"
        file_judgement = "存在正式问题" if file_result["status_code"] != 0 else CLEAN_REPORT
        rows.append(
            f"| {index} | {file_result['file_path']} | {len(file_result['issues'])} | {file_judgement} | {relative_report.as_posix()} |"
        )
    return "\n".join(rows) if rows else "| 1 | - | 0 | 无 | - |"


def make_diff_file_report_index(file_results: list[dict[str, Any]], commit_dir: Path, output_dir: Path) -> str:
    rows: list[str] = []
    review_result_path = (commit_dir / "review_result.json").relative_to(output_dir)
    for index, file_result in enumerate(file_results, start=1):
        file_judgement = "存在正式问题" if file_result["status_code"] != 0 else CLEAN_REPORT
        rows.append(
            f"| {index} | {file_result['file_path']} | {len(file_result['issues'])} | {file_judgement} | {review_result_path.as_posix()} |"
        )
    return "\n".join(rows) if rows else "| 1 | - | 0 | 无 | - |"


def make_references_line(values: list[str], empty_label: str = "无") -> str:
    return "、".join(values) if values else empty_label


def top_risk_types(type_counter: Counter[str]) -> str:
    ordered = [(issue_type, type_counter[issue_type]) for issue_type in TYPE_ORDER if type_counter[issue_type] > 0]
    if not ordered:
        return "无"
    ordered.sort(key=lambda item: (-item[1], TYPE_ORDER.index(item[0])))
    return "、".join(issue_type for issue_type, _ in ordered[:3])


def priority_files(file_results: list[dict[str, Any]]) -> str:
    risky = [item for item in file_results if item["status_code"] != 0]
    if not risky:
        return "无"
    risky.sort(key=lambda item: (-len(item["issues"]), item["file_path"]))
    return "、".join(item["file_path"] for item in risky[:5])


def repo_conclusion(issue_count: int, severity_counter: Counter[str]) -> tuple[str, str]:
    if issue_count == 0:
        return CLEAN_REPORT, "建议当前状态合并 / 部署"
    if severity_counter["高危"] > 0:
        return "不建议当前状态直接合并 / 部署", "否"
    return "存在需处理问题，建议修复后再合并 / 部署", "否"


def render_repo_summary(file_results: list[dict[str, Any]], severity_counter: Counter[str], type_counter: Counter[str], issue_count: int) -> str:
    conclusion, readiness = repo_conclusion(issue_count, severity_counter)
    return "\n".join(
        [
            f"结论：{conclusion}",
            f"建议当前状态合并/部署：{readiness}",
            f"问题总数：{issue_count}",
            f"高危：{severity_counter['高危']}，中危：{severity_counter['中危']}，低危：{severity_counter['低危']}",
            f"主要风险类型：{top_risk_types(type_counter)}",
            f"有问题文件数：{sum(1 for item in file_results if item['status_code'] != 0)}",
            f"未发现问题文件数：{sum(1 for item in file_results if item['status_code'] == 0)}",
        ]
    ) + "\n"


def validate_diff_review_result(review_result_path: Path) -> None:
    validator_path = SCRIPT_DIR / "validate-review-json.py"
    completed = subprocess.run(
        [sys.executable, str(validator_path), str(review_result_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stdout.strip() or completed.stderr.strip() or "校验失败"
        raise RuntimeError(f"review_result.json 校验未通过: {detail}")


def fill_template(template: str, values: dict[str, str]) -> str:
    filled = template
    for key, value in values.items():
        filled = filled.replace(f"{{{key}}}", value)
    return filled


def build_repo_result(repo_path: str, summary: str, file_results: list[dict[str, Any]]) -> dict[str, Any]:
    template = clone_json_template("repo-result-template.json")
    severity_counter, type_counter, issue_count, _ = count_issues(file_results)
    template["repo_path"] = repo_path
    template["repo_summary"] = summary
    template["file_count"] = len(file_results)
    template["issue_count"] = issue_count
    template["severity_count_dict"] = dict(severity_counter)
    template["type_count_dict"] = dict(type_counter)
    template["llm_usage"] = dict(LLM_USAGE_NOT_COLLECTED)
    return template


def write_repo_review_outputs(input_payload: dict[str, Any], output_dir: Path) -> None:
    file_results = [normalize_file_result(item) for item in input_payload.get("file_results", [])]
    repo_path = input_payload.get("repo_path", "")
    references_used = input_payload.get("references_used", {})
    timestamp = input_payload.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    project_name = input_payload.get("project_name") or Path(repo_path).name or "unknown"
    languages = input_payload.get("languages", [])
    line_count = str(input_payload.get("line_count", "未统计"))

    severity_counter, type_counter, issue_count, _ = count_issues(file_results)
    flattened = flatten_issues(file_results)
    repo_summary = render_repo_summary(file_results, severity_counter, type_counter, issue_count)
    repo_result = build_repo_result(repo_path, repo_summary.strip(), file_results)

    review_output_dir = output_dir / "review_output"
    for file_result in file_results:
        report_path = review_output_dir / f"{file_result['file_path']}_review.json"
        write_json(report_path, file_result)

    summary_path = output_dir / "repo_summary.txt"
    write_text(summary_path, repo_summary)
    write_json(output_dir / "repo_result.json", repo_result)

    full_report_template = (ASSETS_DIR / "full-report-template.md").read_text(encoding="utf-8")
    conclusion, merge_readiness = repo_conclusion(issue_count, severity_counter)
    report_content = fill_template(
        full_report_template,
        {
            "project_name": project_name,
            "timestamp": timestamp,
            "output_dir": output_dir.as_posix(),
            "languages": make_references_line(languages),
            "file_count": str(len(file_results)),
            "line_count": line_count,
            "language_references": make_references_line(references_used.get("language", [])),
            "security_references": make_references_line(references_used.get("security", [])),
            "performance_references": make_references_line(references_used.get("performance", [])),
            "workflow_references": make_references_line(references_used.get("workflow", [])),
            "conclusion": conclusion,
            "merge_readiness": merge_readiness,
            "executive_summary": input_payload.get("executive_summary", repo_summary.splitlines()[0]),
            "total_issues_count": str(issue_count),
            "high_count": str(severity_counter["高危"]),
            "medium_count": str(severity_counter["中危"]),
            "low_count": str(severity_counter["低危"]),
            "files_with_issues_count": str(sum(1 for item in file_results if item["status_code"] != 0)),
            "files_without_issues_count": str(sum(1 for item in file_results if item["status_code"] == 0)),
            "top_risk_types": top_risk_types(type_counter),
            "priority_files": priority_files(file_results),
            "priority_summary_table": make_priority_summary_table(severity_counter),
            "risk_type_summary_table": make_risk_type_table(type_counter),
            "file_issue_summary_table": make_file_issue_summary_table(file_results),
            "global_key_findings": make_global_key_findings(flattened),
            "issues_table": make_issues_table(flattened),
            "file_report_index": make_repo_file_report_index(file_results),
            "context_scope": input_payload.get("context_scope", "静态代码审查，必要时补充直接相关上下文"),
            "language_coverage": make_references_line(languages),
            "full_context": input_payload.get("full_context", "否，仅按必要上下文扩展"),
            "review_notes": input_payload.get("review_notes", "结果由文件级中间结果聚合生成；未额外验证运行时行为。"),
        },
    )
    write_text(output_dir / "review_report.md", report_content)


def build_diff_review_result(commit_info: dict[str, Any], file_results: list[dict[str, Any]]) -> dict[str, Any]:
    template = clone_json_template("review-result-template.json")
    severity_counter, type_counter, issue_count, failed_count = count_issues(file_results)
    template["revision"] = commit_info.get("revision", "")
    template["message"] = commit_info.get("message", "")
    template["author"] = commit_info.get("author", "")
    template["file_count"] = len(file_results)
    template["issue_count"] = issue_count
    template["review_failed_count"] = failed_count
    template["severity_count_dict"] = dict(severity_counter)
    template["type_count_dict"] = dict(type_counter)
    template["file_review_result"] = file_results
    return template


def build_diff_repo_result(repo_path: str, commit_info: dict[str, Any], review_result: dict[str, Any]) -> dict[str, Any]:
    template = clone_json_template("repo-result-template.json")
    severity_counter = review_result["severity_count_dict"]
    type_counter = review_result["type_count_dict"]
    template["repo_path"] = repo_path
    template["repo_summary"] = f"提交 {commit_info.get('revision', '')} 共审查 {review_result['file_count']} 个文件，发现 {review_result['issue_count']} 个值得正式留档的问题。"
    template["file_count"] = review_result["file_count"]
    template["issue_count"] = review_result["issue_count"]
    template["severity_count_dict"] = dict(severity_counter)
    template["type_count_dict"] = dict(type_counter)
    template["llm_usage"] = dict(LLM_USAGE_NOT_COLLECTED)
    return template


def write_diff_review_outputs(input_payload: dict[str, Any], output_dir: Path) -> None:
    commit_info = input_payload.get("commit_info", {})
    file_results = [normalize_file_result(item) for item in input_payload.get("file_results", [])]
    diff_payload = input_payload.get("diff_payload") or clone_json_template("diff-json-template.json")
    references_used = input_payload.get("references_used", {})
    timestamp = input_payload.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    repo_path = input_payload.get("repo_path", "")

    review_result = build_diff_review_result(commit_info, file_results)
    repo_result = build_diff_repo_result(repo_path, commit_info, review_result)

    revision = commit_info.get("revision", "unknown")
    author = commit_info.get("author", "unknown")
    commit_dir = output_dir / "commits_result" / f"{revision}_reviewer_{author}"
    write_json(output_dir / "repo_result.json", repo_result)
    write_json(commit_dir / "diff.json", diff_payload)
    review_result_path = commit_dir / "review_result.json"
    write_json(review_result_path, review_result)
    validate_diff_review_result(review_result_path)

    diff_report_template = (ASSETS_DIR / "diff-report-template.md").read_text(encoding="utf-8")
    severity_counter = review_result["severity_count_dict"]
    type_counter = review_result["type_count_dict"]
    flattened = flatten_issues(file_results)
    conclusion, merge_readiness = repo_conclusion(review_result["issue_count"], Counter(severity_counter))
    report_content = fill_template(
        diff_report_template,
        {
            "review_scope": input_payload.get("review_scope", repo_path or "本次差异范围"),
            "revision_range": revision,
            "author": author,
            "timestamp": timestamp,
            "commit_message": commit_info.get("message", ""),
            "changed_files_count": str(len(file_results)),
            "language_references": make_references_line(references_used.get("language", [])),
            "security_references": make_references_line(references_used.get("security", [])),
            "performance_references": make_references_line(references_used.get("performance", [])),
            "workflow_references": make_references_line(references_used.get("workflow", [])),
            "conclusion": conclusion,
            "merge_readiness": merge_readiness,
            "executive_summary": input_payload.get("executive_summary", repo_result["repo_summary"]),
            "total_issues_count": str(review_result["issue_count"]),
            "high_count": str(severity_counter["高危"]),
            "medium_count": str(severity_counter["中危"]),
            "low_count": str(severity_counter["低危"]),
            "files_with_issues_count": str(sum(1 for item in file_results if item["status_code"] != 0)),
            "files_without_issues_count": str(sum(1 for item in file_results if item["status_code"] == 0)),
            "top_risk_types": top_risk_types(Counter(type_counter)),
            "priority_files": priority_files(file_results),
            "priority_summary_table": make_priority_summary_table(Counter(severity_counter)),
            "risk_type_summary_table": make_risk_type_table(Counter(type_counter)),
            "file_issue_summary_table": make_file_issue_summary_table(file_results),
            "global_key_findings": make_global_key_findings(flattened),
            "issues_table": make_issues_table(flattened),
            "file_report_index": make_diff_file_report_index(file_results, commit_dir, output_dir),
            "review_mode": input_payload.get("review_mode", "正式差异审查"),
            "context_scope": input_payload.get("context_scope", "以变更文件及直接相关上下文为主"),
            "diff_only": input_payload.get("diff_only", "是，必要时补充直接相关上下文"),
            "review_notes": input_payload.get("review_notes", "结果由文件级中间结果聚合生成；未额外验证运行时行为。"),
        },
    )
    write_text(commit_dir / "report.md", report_content)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="组装正式代码审核输出")
    parser.add_argument("--mode", required=True, choices=["repo", "diff"], help="输出模式：repo 或 diff")
    parser.add_argument("--input", required=True, help="中间结果 JSON 输入文件")
    parser.add_argument("--output-dir", required=True, help="正式产物输出目录")
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    input_payload = load_json(Path(args.input))
    output_dir = Path(args.output_dir)

    if args.mode == "repo":
        write_repo_review_outputs(input_payload, output_dir)
    else:
        write_diff_review_outputs(input_payload, output_dir)


if __name__ == "__main__":
    main()
