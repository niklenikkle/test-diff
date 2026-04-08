#!/usr/bin/env python3
"""
收集项目文件

用法：
    python collect-files.py <project_root> [options]

选项：
    --type <ext>      指定文件扩展名（可多次使用）
    --exclude <dir>   排除目录（可多次使用）
    --max-size <mb>   最大文件大小（MB）
    --max-files <n>   最大文件数量

输出：
    JSON 格式的文件列表
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Set, Optional


DEFAULT_EXCLUDE_DIRS = {
    'node_modules', 'venv', '.venv', 'env', '.env',
    '__pycache__', '.git', '.svn', '.hg',
    'build', 'dist', 'target', 'out', 'bin',
    'vendor', 'third_party', 'thirdparty',
    '.idea', '.vscode', '.vs',
    'coverage', '.pytest_cache', '.mypy_cache',
    'site-packages', '.tox', '.nox',
}

DEFAULT_INCLUDE_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx',
    '.java', '.kt', '.kts',
    '.go', '.rs',
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp',
    '.php', '.rb', '.swift', '.dart',
    '.scala', '.cs', '.fs',
    '.sql', '.sh', '.bash',
    '.json', '.yaml', '.yml', '.xml', '.toml',
    '.md', '.rst', '.txt',
}

BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.mp3', '.mp4', '.wav', '.avi', '.mov',
    '.exe', '.dll', '.so', '.dylib',
    '.pyc', '.pyo', '.class', '.jar', '.war',
    '.min.js', '.min.css',
}


def is_binary_file(file_path: Path) -> bool:
    """检查是否为二进制文件"""
    ext = file_path.suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return True
    
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
            if b'\x00' in chunk:
                return True
    except Exception:
        return True
    
    return False


def collect_files(
    project_root: str,
    include_extensions: Optional[Set[str]] = None,
    exclude_dirs: Optional[Set[str]] = None,
    max_size_mb: float = 1.0,
    max_files: int = 1000,
) -> List[dict]:
    """
    收集项目文件
    
    Args:
        project_root: 项目根目录
        include_extensions: 包含的文件扩展名
        exclude_dirs: 排除的目录
        max_size_mb: 最大文件大小（MB）
        max_files: 最大文件数量
        
    Returns:
        文件信息列表
    """
    project_root = Path(project_root)
    
    if not project_root.exists():
        return []
    
    if include_extensions is None:
        include_extensions = DEFAULT_INCLUDE_EXTENSIONS
    
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS
    
    max_size_bytes = int(max_size_mb * 1024 * 1024)
    files = []
    
    for file_path in project_root.rglob('*'):
        if len(files) >= max_files:
            break
        
        if not file_path.is_file():
            continue
        
        if any(part in exclude_dirs for part in file_path.parts):
            continue
        
        ext = file_path.suffix.lower()
        if ext not in include_extensions:
            continue
        
        try:
            stat = file_path.stat()
            if stat.st_size > max_size_bytes:
                continue
        except Exception:
            continue
        
        if is_binary_file(file_path):
            continue
        
        relative_path = file_path.relative_to(project_root)
        
        files.append({
            'path': str(relative_path),
            'absolute_path': str(file_path),
            'extension': ext,
            'size': stat.st_size,
            'lines': None,
        })
    
    return files


def count_lines(file_path: str) -> Optional[int]:
    """计算文件行数"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return sum(1 for _ in f)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='收集项目文件')
    parser.add_argument('project_root', help='项目根目录')
    parser.add_argument('--type', action='append', dest='types', 
                       help='文件扩展名（可多次使用）')
    parser.add_argument('--exclude', action='append', dest='excludes',
                       help='排除目录（可多次使用）')
    parser.add_argument('--max-size', type=float, default=1.0,
                       help='最大文件大小（MB）')
    parser.add_argument('--max-files', type=int, default=1000,
                       help='最大文件数量')
    parser.add_argument('--count-lines', action='store_true',
                       help='计算文件行数')
    
    args = parser.parse_args()
    
    include_extensions = set(args.types) if args.types else None
    exclude_dirs = set(args.excludes) if args.excludes else None
    
    files = collect_files(
        args.project_root,
        include_extensions=include_extensions,
        exclude_dirs=exclude_dirs,
        max_size_mb=args.max_size,
        max_files=args.max_files,
    )
    
    if args.count_lines:
        for file_info in files:
            file_info['lines'] = count_lines(file_info['absolute_path'])
    
    result = {
        'project_root': args.project_root,
        'total_files': len(files),
        'total_size': sum(f['size'] for f in files),
        'total_lines': sum(f['lines'] or 0 for f in files) if args.count_lines else None,
        'files': files,
    }
    
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
