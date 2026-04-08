#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ALLOWED_TYPES = {"业务逻辑", "代码质量", "安全", "性能"}
ALLOWED_SEVERITIES = {"低级", "中级", "高级"}
REQUIRED_ISSUE_FIELDS = {
    "title",
    "type",
    "severity",
    "description",
    "location",
    "start_line",
    "end_line",
    "evidence",
    "suggestion",
}
REQUIRED_FILE_RESULT_FIELDS = {
    "file_path",
    "status_code",
    "issues",
    "report",
}
REQUIRED_TOP_LEVEL_FIELDS = {
    "revision",
    "message",
    "author",
    "file_count",
    "issue_count",
    "review_failed_count",
    "severity_count_dict",
    "type_count_dict",
    "file_review_result",
}
SEVERITY_KEYS = {"高危", "中危", "低危"}
TYPE_KEYS = {"业务逻辑", "安全", "代码质量", "性能"}
SEVERITY_TO_COUNT_KEY = {
    "高级": "高危",
    "中级": "中危",
    "低级": "低危",
}
NON_EMPTY_ISSUE_FIELDS = {
    "title",
    "description",
    "location",
    "evidence",
    "suggestion",
}


def add_error(errors: list[dict[str, Any]], path: str, message: str, actual: Any = None) -> None:
    error = {"path": path, "message": message}
    if actual is not None:
        error["actual"] = actual
    errors.append(error)


def validate_string(value: Any, path: str, field_name: str, errors: list[dict[str, Any]], *, allow_empty: bool) -> None:
    if not isinstance(value, str):
        add_error(errors, path, f"{field_name} 必须是字符串", value)
        return
    if not allow_empty and not value.strip():
        add_error(errors, path, f"{field_name} 不能为空字符串", value)


def validate_issue(issue: Any, file_index: int, issue_index: int, errors: list[dict[str, Any]]) -> str | None:
    issue_path = f"file_review_result[{file_index}].issues[{issue_index}]"
    if not isinstance(issue, dict):
        add_error(errors, issue_path, "issue 必须是对象", issue)
        return None

    missing_fields = sorted(REQUIRED_ISSUE_FIELDS - set(issue.keys()))
    if missing_fields:
        add_error(errors, issue_path, "issue 缺少必填字段", missing_fields)

    for field_name in REQUIRED_ISSUE_FIELDS & set(issue.keys()):
        value = issue[field_name]
        field_path = f"{issue_path}.{field_name}"
        if field_name in {"start_line", "end_line"}:
            if not isinstance(value, int):
                add_error(errors, field_path, f"{field_name} 必须是整数", value)
        elif field_name == "type":
            validate_string(value, field_path, field_name, errors, allow_empty=False)
            if isinstance(value, str) and value not in ALLOWED_TYPES:
                add_error(errors, field_path, "type 枚举不合法", value)
        elif field_name == "severity":
            validate_string(value, field_path, field_name, errors, allow_empty=False)
            if isinstance(value, str) and value not in ALLOWED_SEVERITIES:
                add_error(errors, field_path, "severity 枚举不合法", value)
        else:
            validate_string(
                value,
                field_path,
                field_name,
                errors,
                allow_empty=field_name not in NON_EMPTY_ISSUE_FIELDS,
            )

    if isinstance(issue.get("severity"), str) and issue["severity"] in ALLOWED_SEVERITIES:
        return issue["severity"]
    return None


def validate_count_dict(value: Any, path: str, expected_keys: set[str], errors: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        add_error(errors, path, "必须是对象", value)
        return
    missing = sorted(expected_keys - set(value.keys()))
    if missing:
        add_error(errors, path, "缺少必填键", missing)
    for key in expected_keys & set(value.keys()):
        if not isinstance(value[key], int):
            add_error(errors, f"{path}.{key}", "值必须是整数", value[key])


def validate_file_result(file_item: Any, file_index: int, errors: list[dict[str, Any]]) -> tuple[int, Counter, Counter, int]:
    file_path = f"file_review_result[{file_index}]"
    if not isinstance(file_item, dict):
        add_error(errors, file_path, "file_review_result 元素必须是对象", file_item)
        return 0, Counter(), Counter(), 0

    missing_fields = sorted(REQUIRED_FILE_RESULT_FIELDS - set(file_item.keys()))
    if missing_fields:
        add_error(errors, file_path, "file_review_result 缺少必填字段", missing_fields)

    if "file_path" in file_item:
        validate_string(file_item["file_path"], f"{file_path}.file_path", "file_path", errors, allow_empty=False)

    status_code = file_item.get("status_code")
    if not isinstance(status_code, int):
        add_error(errors, f"{file_path}.status_code", "status_code 必须是整数", status_code)

    if "report" in file_item:
        validate_string(file_item["report"], f"{file_path}.report", "report", errors, allow_empty=False)

    issues = file_item.get("issues")
    severity_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    issue_count = 0
    if issues is None:
        issues = []
    elif not isinstance(issues, list):
        add_error(errors, f"{file_path}.issues", "issues 必须是数组", issues)
        issues = []
    else:
        for issue_index, issue in enumerate(issues):
            severity = validate_issue(issue, file_index, issue_index, errors)
            if severity is not None:
                severity_counts[severity] += 1
            if isinstance(issue, dict) and isinstance(issue.get("type"), str) and issue["type"] in ALLOWED_TYPES:
                type_counts[issue["type"]] += 1
            issue_count += 1

    failed = 1 if isinstance(status_code, int) and status_code != 0 else 0
    return issue_count, severity_counts, type_counts, failed


def validate_payload(payload: Any) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        add_error(errors, "$", "顶层必须是对象", payload)
        return errors

    missing_fields = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(payload.keys()))
    if missing_fields:
        add_error(errors, "$", "顶层缺少必填字段", missing_fields)

    for field_name in {"revision", "message", "author"} & set(payload.keys()):
        validate_string(payload[field_name], f"$.{field_name}", field_name, errors, allow_empty=field_name == "message")

    for field_name in {"file_count", "issue_count", "review_failed_count"} & set(payload.keys()):
        if not isinstance(payload[field_name], int):
            add_error(errors, f"$.{field_name}", f"{field_name} 必须是整数", payload[field_name])

    if "severity_count_dict" in payload:
        validate_count_dict(payload["severity_count_dict"], "$.severity_count_dict", SEVERITY_KEYS, errors)
    if "type_count_dict" in payload:
        validate_count_dict(payload["type_count_dict"], "$.type_count_dict", TYPE_KEYS, errors)

    file_review_result = payload.get("file_review_result")
    if file_review_result is None:
        add_error(errors, "$.file_review_result", "缺少 file_review_result")
        return errors
    if not isinstance(file_review_result, list):
        add_error(errors, "$.file_review_result", "file_review_result 必须是数组", file_review_result)
        return errors

    actual_issue_count = 0
    actual_failed_count = 0
    severity_counts = Counter({key: 0 for key in SEVERITY_KEYS})
    type_counts = Counter({key: 0 for key in TYPE_KEYS})

    for file_index, file_item in enumerate(file_review_result):
        item_issue_count, item_severity_counts, item_type_counts, item_failed = validate_file_result(file_item, file_index, errors)
        actual_issue_count += item_issue_count
        actual_failed_count += item_failed
        for severity, count in item_severity_counts.items():
            severity_counts[SEVERITY_TO_COUNT_KEY[severity]] += count
        for issue_type, count in item_type_counts.items():
            type_counts[issue_type] += count

    expected_counts = {
        "file_count": len(file_review_result),
        "issue_count": actual_issue_count,
        "review_failed_count": actual_failed_count,
    }
    for field_name, expected_value in expected_counts.items():
        actual_value = payload.get(field_name)
        if isinstance(actual_value, int) and actual_value != expected_value:
            add_error(
                errors,
                f"$.{field_name}",
                f"{field_name} 与实际数量不一致",
                {"expected": expected_value, "actual": actual_value},
            )

    severity_dict = payload.get("severity_count_dict")
    if isinstance(severity_dict, dict):
        for key in SEVERITY_KEYS:
            actual_value = severity_dict.get(key)
            expected_value = severity_counts[key]
            if isinstance(actual_value, int) and actual_value != expected_value:
                add_error(
                    errors,
                    f"$.severity_count_dict.{key}",
                    "severity_count_dict 与 issues 实际数量不一致",
                    {"expected": expected_value, "actual": actual_value},
                )

    type_dict = payload.get("type_count_dict")
    if isinstance(type_dict, dict):
        for key in TYPE_KEYS:
            actual_value = type_dict.get(key)
            expected_value = type_counts[key]
            if isinstance(actual_value, int) and actual_value != expected_value:
                add_error(
                    errors,
                    f"$.type_count_dict.{key}",
                    "type_count_dict 与 issues 实际数量不一致",
                    {"expected": expected_value, "actual": actual_value},
                )

    return errors


def validate_file(file_path: Path) -> dict[str, Any]:
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "error_type": "json_decode_error",
            "errors": [
                {
                    "path": "$",
                    "message": "JSON 语法错误",
                    "actual": {
                        "line": exc.lineno,
                        "column": exc.colno,
                        "message": exc.msg,
                    },
                }
            ],
        }

    errors = validate_payload(payload)
    return {
        "ok": not errors,
        "error_type": None if not errors else "schema_validation_error",
        "errors": errors,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": "usage_error",
                    "errors": [{"path": "$", "message": "Usage: validate-review-json.py <json_file>"}],
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_type": "file_not_found",
                    "errors": [{"path": "$", "message": "文件不存在", "actual": str(file_path)}],
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    result = validate_file(file_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
