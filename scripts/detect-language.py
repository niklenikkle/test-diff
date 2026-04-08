#!/usr/bin/env python3
"""
检测项目使用的编程语言

用法：
    python detect-language.py <project_root>

输出：
    JSON 格式的语言列表及置信度
"""

import os
import sys
import json
from pathlib import Path
from collections import Counter

LANGUAGE_CONFIG_FILES = {
    'package.json': ['javascript', 'typescript'],
    'tsconfig.json': ['typescript'],
    'requirements.txt': ['python'],
    'setup.py': ['python'],
    'pyproject.toml': ['python'],
    'Pipfile': ['python'],
    'pom.xml': ['java'],
    'build.gradle': ['java'],
    'build.gradle.kts': ['java'],
    'go.mod': ['go'],
    'Cargo.toml': ['rust'],
    'CMakeLists.txt': ['cpp', 'c'],
    'Makefile': ['c', 'cpp'],
    'composer.json': ['php'],
    'Gemfile': ['ruby'],
    'pubspec.yaml': ['dart'],
    'mix.exs': ['elixir'],
}

LANGUAGE_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.mjs': 'javascript',
    '.cjs': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.mts': 'typescript',
    '.java': 'java',
    '.kt': 'kotlin',
    '.kts': 'kotlin',
    '.go': 'go',
    '.rs': 'rust',
    '.c': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.hxx': 'cpp',
    '.php': 'php',
    '.rb': 'ruby',
    '.swift': 'swift',
    '.dart': 'dart',
    '.ex': 'elixir',
    '.exs': 'elixir',
    '.scala': 'scala',
    '.cs': 'csharp',
    '.fs': 'fsharp',
    '.vb': 'vb',
    '.lua': 'lua',
    '.r': 'r',
    '.sql': 'sql',
    '.sh': 'shell',
    '.bash': 'shell',
    '.ps1': 'powershell',
}

EXCLUDE_DIRS = {
    'node_modules', 'venv', '.venv', 'env', '.env',
    '__pycache__', '.git', '.svn', '.hg',
    'build', 'dist', 'target', 'out', 'bin',
    'vendor', 'third_party', 'thirdparty',
    '.idea', '.vscode', '.vs',
    'coverage', '.pytest_cache', '.mypy_cache',
}


def detect_languages(project_root: str) -> list:
    """
    检测项目使用的编程语言
    
    Args:
        project_root: 项目根目录路径
        
    Returns:
        语言列表，包含语言名称、置信度和文件数量
    """
    project_root = Path(project_root)
    
    if not project_root.exists():
        return []
    
    languages = Counter()
    
    for config_file, langs in LANGUAGE_CONFIG_FILES.items():
        if (project_root / config_file).exists():
            for lang in langs:
                languages[lang] += 10
    
    for file_path in project_root.rglob('*'):
        if file_path.is_file():
            if any(part in EXCLUDE_DIRS for part in file_path.parts):
                continue
            
            ext = file_path.suffix.lower()
            if ext in LANGUAGE_EXTENSIONS:
                languages[LANGUAGE_EXTENSIONS[ext]] += 1
    
    total = sum(languages.values())
    if total == 0:
        return []
    
    result = []
    for lang, count in languages.most_common(10):
        confidence = round(count / total, 2)
        result.append({
            'language': lang,
            'confidence': confidence,
            'file_count': count
        })
    
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python detect-language.py <project_root>", file=sys.stderr)
        sys.exit(1)
    
    project_root = sys.argv[1]
    result = detect_languages(project_root)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
