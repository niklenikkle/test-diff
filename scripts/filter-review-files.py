#!/usr/bin/env python3
"""
过滤代码审查目标文件：仅剔除明确低价值文件，其余文件保留并打标。

支持两类输入：
1. 文件清单 manifest（包含 files 数组）
2. 单条 SVN 提交记录 JSON（如 commit_info/file_info/change_content/change_location）

用法：
    python filter-review-files.py <input_json>
    python filter-review-files.py --project-root <project_root> [--count-lines]

输出：
    JSON，包含：
    - included_files: 保留送审文件（附 tags）
    - excluded_files: 被剔除文件及原因
    - stats: 过滤统计
    - input_kind: manifest 或 svn_commit_record
"""

import sys
import json
import argparse
import importlib.util
from pathlib import Path
from typing import Any, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECT_FILES_PATH = SCRIPT_DIR / 'collect-files.py'
COLLECT_FILES_SPEC = importlib.util.spec_from_file_location('collect_files_module', COLLECT_FILES_PATH)
if COLLECT_FILES_SPEC is None or COLLECT_FILES_SPEC.loader is None:
    raise RuntimeError(f'无法加载 collect-files.py: {COLLECT_FILES_PATH}')
COLLECT_FILES_MODULE = importlib.util.module_from_spec(COLLECT_FILES_SPEC)
COLLECT_FILES_SPEC.loader.exec_module(COLLECT_FILES_MODULE)
collect_files = COLLECT_FILES_MODULE.collect_files
count_lines = COLLECT_FILES_MODULE.count_lines


LOW_VALUE_SUFFIXES = (
    '.min.js',
    '.min.css',
    '.bundle.js',
    '.bundle.css',
    '.snap',
)

LOW_VALUE_NAMES = {
    'package-lock.json',
    'yarn.lock',
    'pnpm-lock.yaml',
    'poetry.lock',
    'Cargo.lock',
    'go.sum',
    'composer.lock',
}

DOC_EXTENSIONS = {'.md', '.rst', '.txt'}
CONFIG_EXTENSIONS = {'.json', '.yaml', '.yml', '.toml', '.xml'}
REVIEW_INPUT_KEYWORDS = (
    'svn',
    'commit',
    'diff',
    'review',
    'revision',
)
TEST_KEYWORDS = (
    'test/',
    'tests/',
    '__tests__/',
    'spec/',
    '_test.',
    '.test.',
    '.spec.',
)

LARGE_FILE_LINE_THRESHOLD = 800
LARGE_FILE_SIZE_THRESHOLD = 512 * 1024


def normalize_path(path: str) -> str:
    return path.replace('\\', '/').lower()


def load_manifest(manifest_path: str) -> dict[str, Any]:
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_manifest_from_project(project_root: str, count_lines_enabled: bool) -> dict[str, Any]:
    files = collect_files(project_root)

    if count_lines_enabled:
        for file_info in files:
            absolute_path = file_info.get('absolute_path')
            if absolute_path:
                file_info['lines'] = count_lines(absolute_path)

    return {
        'project_root': project_root,
        'total_files': len(files),
        'files': files,
        'input_kind': 'manifest',
    }


def is_svn_commit_record(payload: dict[str, Any]) -> bool:
    return isinstance(payload, dict) and 'file_info' in payload and 'change_content' in payload


def adapt_svn_commit_record(payload: dict[str, Any], source_path: Optional[str]) -> dict[str, Any]:
    file_info = payload.get('file_info') or {}
    change_content = payload.get('change_content') or {}
    file_path = file_info.get('file_path') or file_info.get('file_name') or source_path or 'unknown'
    extension = Path(file_path).suffix.lower()
    content_for_size = change_content.get('new_content') or change_content.get('old_content') or ''
    line_count = None
    if isinstance(content_for_size, str):
        line_count = len(content_for_size.splitlines())

    file_entry = {
        'path': file_path,
        'absolute_path': source_path,
        'extension': extension,
        'size': len(content_for_size.encode('utf-8')) if isinstance(content_for_size, str) else 0,
        'lines': line_count,
        'source_kind': 'svn_commit_record',
        'commit_info': payload.get('commit_info'),
        'change_location': payload.get('change_location'),
        'change_type': payload.get('change_type'),
    }

    return {
        'project_root': None,
        'total_files': 1,
        'files': [file_entry],
        'input_kind': 'svn_commit_record',
        'raw_input_path': source_path,
    }


def to_manifest(payload: dict[str, Any], source_path: Optional[str]) -> dict[str, Any]:
    if is_svn_commit_record(payload):
        return adapt_svn_commit_record(payload, source_path)

    manifest = dict(payload)
    manifest.setdefault('input_kind', 'manifest')
    return manifest


def get_excluded_reason(path: str) -> Optional[str]:
    normalized = normalize_path(path)
    file_name = Path(path).name

    if file_name in LOW_VALUE_NAMES:
        return 'lockfile'

    if any(normalized.endswith(suffix) for suffix in LOW_VALUE_SUFFIXES):
        return 'generated_or_snapshot_artifact'

    if '.generated.' in normalized:
        return 'generated_or_snapshot_artifact'

    return None


def is_review_input_file(path: str) -> bool:
    normalized = normalize_path(path)
    file_name = Path(path).name.lower()

    if not file_name.endswith('.json'):
        return False

    return any(keyword in normalized for keyword in REVIEW_INPUT_KEYWORDS)


def build_tags(path: str, extension: str, size: int, lines: Optional[int], source_kind: Optional[str]) -> list[str]:
    normalized = normalize_path(path)
    tags: list[str] = []

    if source_kind == 'svn_commit_record' or is_review_input_file(path):
        tags.append('review_input')
    elif extension in CONFIG_EXTENSIONS:
        tags.append('config_file')

    if any(keyword in normalized for keyword in TEST_KEYWORDS):
        tags.append('test_file')

    if extension in DOC_EXTENSIONS:
        tags.append('doc_file')

    if size > LARGE_FILE_SIZE_THRESHOLD:
        tags.append('large_file')

    if lines is not None and lines > LARGE_FILE_LINE_THRESHOLD:
        tags.append('large_file')

    return sorted(set(tags))


def filter_files(manifest: dict[str, Any]) -> dict[str, Any]:
    files = manifest.get('files', [])
    included_files: list[dict[str, Any]] = []
    excluded_files: list[dict[str, Any]] = []

    for file_info in files:
        path = file_info.get('path') or file_info.get('absolute_path') or ''
        extension = (file_info.get('extension') or Path(path).suffix or '').lower()
        size = int(file_info.get('size') or 0)
        lines = file_info.get('lines')
        source_kind = file_info.get('source_kind')

        excluded_reason = get_excluded_reason(path)
        if excluded_reason is not None and source_kind != 'svn_commit_record':
            excluded_item = dict(file_info)
            excluded_item['excluded_reason'] = excluded_reason
            excluded_files.append(excluded_item)
            continue

        included_item = dict(file_info)
        included_item['tags'] = build_tags(path, extension, size, lines, source_kind)
        included_files.append(included_item)

    return {
        'project_root': manifest.get('project_root'),
        'input_kind': manifest.get('input_kind', 'manifest'),
        'input_total_files': len(files),
        'included_total_files': len(included_files),
        'excluded_total_files': len(excluded_files),
        'included_files': included_files,
        'excluded_files': excluded_files,
        'stats': {
            'input_total_size': sum(int(item.get('size') or 0) for item in files),
            'included_total_size': sum(int(item.get('size') or 0) for item in included_files),
            'excluded_total_size': sum(int(item.get('size') or 0) for item in excluded_files),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='过滤代码审查目标文件')
    parser.add_argument('input_json', nargs='?', help='文件清单 JSON 或 SVN 提交记录 JSON')
    parser.add_argument('--project-root', help='直接从项目目录构造文件清单')
    parser.add_argument('--count-lines', action='store_true', help='扫描项目时统计文件行数')
    args = parser.parse_args()

    if not args.input_json and not args.project_root:
        print('必须提供 input_json 或 --project-root', file=sys.stderr)
        sys.exit(1)

    if args.input_json:
        payload = load_manifest(args.input_json)
        manifest = to_manifest(payload, args.input_json)
    else:
        manifest = build_manifest_from_project(args.project_root, args.count_lines)

    result = filter_files(manifest)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
