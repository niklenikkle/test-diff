#!/usr/bin/env python3
"""
解析 SVN 差异输出

用法：
    python svn-diff-parser.py [revision_range]
    python svn-diff-parser.py -c REV
    python svn-diff-parser.py --url SVN_URL
    python svn-diff-parser.py --url SVN_URL -c REV
    python svn-diff-parser.py --url SVN_URL START:END

示例：
    python svn-diff-parser.py                    # 工作副本差异
    python svn-diff-parser.py 1234:1235         # 版本范围差异
    python svn-diff-parser.py -c 1235           # 特定版本变更
    python svn-diff-parser.py --url SVN_URL     # URL 最近一次提交差异
    python svn-diff-parser.py --url SVN_URL -c 1235

输出：
    JSON 格式的差异信息
"""

import sys
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple


USAGE = """用法：
    python svn-diff-parser.py [revision_range]
    python svn-diff-parser.py -c REV
    python svn-diff-parser.py --url SVN_URL
    python svn-diff-parser.py --url SVN_URL -c REV
    python svn-diff-parser.py --url SVN_URL START:END
"""


@dataclass
class Hunk:
    """差异块"""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str]


@dataclass
class FileDiff:
    """文件差异"""
    path: str
    change_type: str  # 'added', 'modified', 'deleted'
    old_path: Optional[str]
    new_path: Optional[str]
    hunks: List[Hunk]
    additions: int
    deletions: int


def print_usage(exit_code: int = 0) -> None:
    """打印用法并退出。"""
    output = sys.stdout if exit_code == 0 else sys.stderr
    print(USAGE, file=output)
    sys.exit(exit_code)


def run_svn_command(args: List[str]) -> str:
    """执行 svn 命令并返回 stdout。"""
    cmd = ['svn'] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
    except FileNotFoundError:
        print("Error: svn command not found", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        stderr = result.stderr.strip() or 'unknown svn error'
        print(f"Error: {' '.join(cmd)} failed: {stderr}", file=sys.stderr)
        sys.exit(result.returncode)

    return result.stdout


def run_svn_diff(args: List[str]) -> str:
    """执行 svn diff 命令"""
    return run_svn_command(['diff'] + args)


def run_svn_log(args: List[str]) -> str:
    """执行 svn log 命令"""
    return run_svn_command(['log'] + args)


def parse_diff_output(diff_text: str) -> List[FileDiff]:
    """解析差异输出"""
    diffs = []
    current_diff = None
    current_hunk = None

    lines = diff_text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith('Index: '):
            if current_diff:
                if current_hunk:
                    current_diff.hunks.append(current_hunk)
                diffs.append(current_diff)

            path = line[7:].strip()
            current_diff = FileDiff(
                path=path,
                change_type='modified',
                old_path=None,
                new_path=None,
                hunks=[],
                additions=0,
                deletions=0
            )
            current_hunk = None

        elif line.startswith('--- '):
            if current_diff:
                match = re.match(r'--- (.+?)\s+\(revision (\d+)\)', line)
                if match:
                    current_diff.old_path = match.group(1)
                    if match.group(2) == '0':
                        current_diff.change_type = 'added'

        elif line.startswith('+++ '):
            if current_diff:
                match = re.match(r'\+\+\+ (.+?)\s+\((?:working copy|revision \d+)\)', line)
                if match:
                    current_diff.new_path = match.group(1)

        elif line.startswith('@@ '):
            if current_diff:
                if current_hunk:
                    current_diff.hunks.append(current_hunk)

                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    current_hunk = Hunk(
                        old_start=int(match.group(1)),
                        old_count=int(match.group(2) or 1),
                        new_start=int(match.group(3)),
                        new_count=int(match.group(4) or 1),
                        lines=[]
                    )

        elif current_hunk is not None:
            if line.startswith('+') and not line.startswith('+++'):
                current_diff.additions += 1
                current_hunk.lines.append(line)
            elif line.startswith('-') and not line.startswith('---'):
                current_diff.deletions += 1
                current_hunk.lines.append(line)
            elif line.startswith(' '):
                current_hunk.lines.append(line)

        i += 1

    if current_diff:
        if current_hunk:
            current_diff.hunks.append(current_hunk)
        diffs.append(current_diff)

    return diffs


def get_svn_info(revision: str = None, target: str = None) -> dict:
    """获取 SVN 仓库信息"""
    cmd = ['info']
    if revision:
        cmd.extend(['-r', revision])
    if target:
        cmd.append(target)

    try:
        result = run_svn_command(cmd)
        info = {}
        for line in result.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip()] = value.strip()
        return info
    except SystemExit:
        return {}


def get_latest_revision(target: str) -> Optional[str]:
    """获取 URL 目标最近一次可见提交 revision。"""
    log_output = run_svn_log(['-l', '1', '-v', target])
    match = re.search(r'^r(\d+)\s+\|', log_output, re.MULTILINE)
    return match.group(1) if match else None


def parse_cli_args(args: List[str]) -> Tuple[Optional[str], List[str]]:
    """解析命令行参数，提取 --url。"""
    if any(arg in ('-h', '--help') for arg in args):
        print_usage(0)

    target_url = None
    diff_args = []
    i = 0

    while i < len(args):
        arg = args[i]
        if arg == '--url':
            if i + 1 >= len(args):
                print('Error: --url requires a value', file=sys.stderr)
                print_usage(1)
            target_url = args[i + 1]
            i += 2
            continue
        diff_args.append(arg)
        i += 1

    if diff_args and diff_args[0].startswith('-') and diff_args[0] != '-c':
        print(f"Error: unsupported argument {diff_args[0]}", file=sys.stderr)
        print_usage(1)

    if diff_args[:1] == ['-c'] and len(diff_args) == 1:
        print('Error: -c requires a revision', file=sys.stderr)
        print_usage(1)

    return target_url, diff_args


def build_diff_args(target_url: Optional[str], diff_args: List[str]) -> Tuple[List[str], Optional[str]]:
    """构建 svn diff 参数，并返回用于 svn info 的 revision。"""
    info_revision = None

    if not diff_args:
        if target_url:
            latest_revision = get_latest_revision(target_url)
            if not latest_revision:
                print(f'Error: cannot determine latest revision for {target_url}', file=sys.stderr)
                sys.exit(1)
            info_revision = latest_revision
            return ['-c', latest_revision, target_url], info_revision
        return [], None

    if len(diff_args) == 1 and ':' in diff_args[0]:
        start, end = diff_args[0].split(':', 1)
        info_revision = end
        built_args = ['-r', f'{start}:{end}']
        if target_url:
            built_args.append(target_url)
        return built_args, info_revision

    if diff_args[0] == '-c' and len(diff_args) > 1:
        info_revision = diff_args[1]
        built_args = ['-c', diff_args[1]]
        if target_url:
            built_args.append(target_url)
        return built_args, info_revision

    built_args = list(diff_args)
    if target_url and target_url not in built_args:
        built_args.append(target_url)
    return built_args, info_revision


def main():
    raw_args = sys.argv[1:]
    target_url, diff_args = parse_cli_args(raw_args)
    svn_diff_args, info_revision = build_diff_args(target_url, diff_args)

    diff_text = run_svn_diff(svn_diff_args)
    diffs = parse_diff_output(diff_text)
    svn_info = get_svn_info(revision=info_revision, target=target_url)
    if not svn_info:
        print('Error: failed to read svn info for current target', file=sys.stderr)
        sys.exit(1)

    result = {
        'repository': svn_info.get('Repository Root', ''),
        'working_copy_path': svn_info.get('Working Copy Root Path', ''),
        'target_url': target_url or '',
        'target_path': svn_info.get('Path', ''),
        'revision': svn_info.get('Revision', info_revision or ''),
        'files': [asdict(d) for d in diffs],
        'summary': {
            'total_files': len(diffs),
            'total_additions': sum(d.additions for d in diffs),
            'total_deletions': sum(d.deletions for d in diffs),
            'added_files': sum(1 for d in diffs if d.change_type == 'added'),
            'modified_files': sum(1 for d in diffs if d.change_type == 'modified'),
            'deleted_files': sum(1 for d in diffs if d.change_type == 'deleted'),
        }
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
