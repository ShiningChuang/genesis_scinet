#!/usr/bin/env python3
"""把 markdown 里 IDE 复制粘贴带出来的 `vscode-webview://<host>/<repo-path>` 链接
重写成**仓库内相对路径**(按该文件相对仓库根的目录深度补 `../`)。

背景:在 VSCode webview 里复制含相对链接的文本,链接会被改写成
`vscode-webview://<hash>/src/...`,别人 clone 后打不开。本脚本把这层壳剥掉,
还原成 `../src/...`(docs/findings.md)或 `../../src/...`(docs/archive/x.md)等。

用法:`fix_webview_links.py <file.md> [<file2.md> ...]`(路径相对仓库根)。
被改动的文件名打到 stdout(供 pre-commit hook 决定 re-add 哪些);其余静默。
非文本/读不到的文件跳过,绝不报错中断(给 hook 当"尽力而为"用)。
"""

import os
import re
import sys

# 匹配 webview 主机壳:`vscode-webview://<host>/` 与 `vscode-resource` 变体,
# 捕获到的整段(到第一个 `/` 后)被替成相对前缀。
PAT = re.compile(r'(?:vscode-webview|vscode-resource)://[^/]+/')


def rel_prefix(path):
    """文件相对仓库根的目录深度 → `../` × 深度('docs/x.md'→'../';根文件→'')。"""
    d = os.path.dirname(path)
    depth = len([p for p in d.split(os.sep) if p]) if d else 0
    return "../" * depth


def fix_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeError):
        return False
    new = PAT.sub(rel_prefix(path), text)
    if new == text:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return True


def main(argv):
    for path in argv:
        if fix_file(path):
            print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
