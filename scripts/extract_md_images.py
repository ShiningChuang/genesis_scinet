#!/usr/bin/env python3
"""把 markdown 里内嵌的 base64 图片(`data:image/<type>;base64,<巨长字符串>`)抽成
`resources/imgs/` 下的独立图片文件,并把原处改写成**相对路径引用**。

背景:从 Google Docs / 剪贴板等导出的 md 常把截图内嵌成 base64,单张就几百 KB,
撑大仓库、diff 不可读、agent 读文件时塞满上下文。本脚本在 pre-commit 时把它们拆出去。

覆盖三种写法(只替换 data URI 本身,外层语法原样保留):
    ![alt](data:image/png;base64,...)
    [image1]: <data:image/png;base64,...>      # Google Docs 导出的引用式
    <img src="data:image/png;base64,...">

命名:`resources/imgs/{YYYYMMDD}_{tag}.{ext}`,同名已占用则 `_2`、`_3` …;
内容完全相同的已有文件直接复用(重复运行幂等)。日期与 tag 取自 md 文件名:
    20260926_agent.md          → 20260926_agent.png
    meetings/20260727.md       → 20260727_meetings.png   (无 tag 时用所在目录名)
    README.md                  → {今天}_readme.png        (无日期时用今天)

用法:
    extract_md_images.py <file.md> [<file2.md> ...]   # 路径相对仓库根
    extract_md_images.py --all                        # 扫仓库内全部 md(tracked + untracked,不含 external/)
改动过的 md 与新写出的图片路径打到 stdout(供 pre-commit hook re-add);其余静默。
读不到 / 非 UTF-8 的文件跳过;写图失败则非零退出(hook 据此阻断提交)。
"""

import base64
import binascii
import os
import re
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "resources", "imgs")

# 至少 100 个 base64 字符才算"内嵌图片",避免误伤正文里举例写的短 data URI。
PAT = re.compile(r"data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]{100,})")
EXT = {"jpeg": "jpg", "svg+xml": "svg", "x-icon": "ico"}


def date_and_tag(md_path):
    """md 文件名 → (YYYYMMDD, tag)。规则见模块 docstring。"""
    stem = os.path.splitext(os.path.basename(md_path))[0]
    m = re.match(r"^(\d{8})(?:_(.+))?$", stem)
    if m:
        d, tag = m.group(1), m.group(2) or os.path.basename(os.path.dirname(os.path.abspath(md_path)))
    else:
        d, tag = date.today().strftime("%Y%m%d"), stem
    tag = re.sub(r"[^a-z0-9_]+", "_", tag.lower()).strip("_") or "img"
    return d, tag


def place_image(data, base, ext):
    """把图片字节落到 resources/imgs/,返回文件绝对路径与是否新写出。

    依次尝试 base.ext、base_2.ext …:空位则写入;已有文件内容相同则复用。
    """
    os.makedirs(IMG_DIR, exist_ok=True)
    n = 1
    while True:
        name = f"{base}.{ext}" if n == 1 else f"{base}_{n}.{ext}"
        path = os.path.join(IMG_DIR, name)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(data)
            return path, True
        with open(path, "rb") as f:
            if f.read() == data:
                return path, False
        n += 1


def fix_file(md_path):
    """处理单个 md;返回 (是否改动, 新写出的图片绝对路径列表)。"""
    try:
        with open(md_path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeError):
        return False, []
    if not PAT.search(text):
        return False, []

    d, tag = date_and_tag(md_path)
    md_dir = os.path.dirname(os.path.abspath(md_path))
    written = []

    def repl(m):
        try:
            data = base64.b64decode(m.group(2), validate=True)
        except (binascii.Error, ValueError):
            return m.group(0)  # 不是合法 base64,原样保留
        ext = EXT.get(m.group(1).lower(), m.group(1).lower())
        path, new = place_image(data, f"{d}_{tag}", ext)
        if new:
            written.append(path)
        return os.path.relpath(path, md_dir).replace(os.sep, "/")

    new_text = PAT.sub(repl, text)
    if new_text == text:
        return False, written
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    return True, written


def all_md():
    out = subprocess.check_output(
        ["git", "ls-files", "-co", "--exclude-standard", "--", "*.md"], cwd=ROOT
    ).decode()
    return [os.path.join(ROOT, p) for p in out.splitlines() if not p.startswith("external/")]


def main(argv):
    paths = all_md() if argv == ["--all"] else argv
    for path in paths:
        changed, written = fix_file(path)
        if changed:
            print(os.path.relpath(path, os.getcwd()))
        for img in written:
            print(os.path.relpath(img, os.getcwd()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
