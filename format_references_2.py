# format_references_with_title.py
"""批量格式化【引文格式】引用，并按论文题目重命名文件

升级点（v5）：
1. **DeepSeek 一次提取**：输出三行——第一行为论文中文题目，第二行为中文引用，第三行为英文引用。
2. **本地兜底**：当 DeepSeek 不可用或解析失败时，使用原有两行输出 + 本地 regex 提取标题。
3. 保持 `--apply` / `--out` / 备份 / 去重重命名等既有流程。

用法示例
────────
```bash
# 仅预览
python format_references_with_title.py ./txt_folder
# 覆盖原文件并重命名
python format_references_with_title.py ./txt_folder --apply
# 输出到新目录
python format_references_with_title.py ./txt_folder --out ./out
```"""

from __future__ import annotations
import os, re, sys, pathlib, argparse, requests, textwrap, shutil
from typing import Tuple

API_KEY = os.getenv("DEEPSEEK_API_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

SYSTEM_PROMPT = textwrap.dedent("""
你是学术排版助手。输入可能缺少空格或换行的参考文献信息。
请严格输出三行：
第一行：论文中文题目（不含句号、[J]、年份卷页）；
第二行：完整的中文引用；
第三行：完整的英文引用。
确保行末无多余空格，整体不要额外换行。""")

# ───────────────── API 调用 ──────────────────

def call_deepseek(raw: str) -> str:
    if not API_KEY:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": raw.strip()},
        ],
        "temperature": 0.2,
        "max_tokens": 512,
    }
    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

# ───────────────── 本地兜底 ──────────────────

def local_fix(raw: str) -> str:
    txt = raw.replace("\n", " ")
    txt = re.sub(r"([。.,，；;:])(?=\S)", r"\1 ", txt)
    m = re.search(r"[A-Za-z]", txt)
    if not m:
        return txt
    idx = m.start()
    return f"{txt[:idx].strip()}\n{txt[idx:].strip()}"

# 提取本地标题

def extract_title_regex(cn_line: str) -> str | None:
    m = re.search(r"\.\s*([^\.\[\]]+?)\s*\[J\]", cn_line)
    if m:
        return m.group(1).strip()
    m = re.search(r"\.\s*([^\.]+?)\.", cn_line)
    if m:
        return m.group(1).strip()
    return None

# ───────────────── 辅助函数 ──────────────────

def extract_block(text: str) -> Tuple[int, int, str] | None:
    m = re.search(r"引文格式[\s\S]*?(?:\r?\n)(.+)$", text, re.MULTILINE)
    if not m:
        return None
    start = m.start(1)
    tail = text[start:]
    m2 = re.search(r"\n\s*\n", tail)
    end = start + (m2.start() if m2 else len(tail))
    return start, end, text[start:end]


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\u4e00-\u9fff\-() ]", "", name)
    return re.sub(r"\s+", " ", name).strip()[:128]


def get_unique_path(p: pathlib.Path) -> pathlib.Path:
    if not p.exists(): return p
    stem, suf = p.stem, p.suffix
    i = 1
    while True:
        candidate = p.with_name(f"{stem}_{i}{suf}")
        if not candidate.exists(): return candidate
        i += 1

# ───────────────── 核心流程 ──────────────────

def process(path: pathlib.Path, apply: bool, offline: bool, out_dir: pathlib.Path | None):
    txt = path.read_text(encoding="utf-8", errors="ignore")
    blk = extract_block(txt)
    if not blk:
        print(f"[跳过] {path.name} 无引文格式")
        return
    s, e, raw = blk

    if offline:
        fixed = local_fix(raw)
        lines = fixed.split("\n")
        title = extract_title_regex(lines[0]) or path.stem
        cn_line = lines[0]
        en_line = lines[1] if len(lines) > 1 else ""
    else:
        try:
            out = call_deepseek(raw)
            lines = out.split("\n")
            title, cn_line, en_line = lines[0], lines[1], lines[2] if len(lines)>2 else ""
            fixed = f"{cn_line}\n{en_line}"
        except Exception as err:
            print(f"[DeepSeek 失败] {path.name}: {err} → 本地处理")
            fixed = local_fix(raw)
            lines = fixed.split("\n")
            title = extract_title_regex(lines[0]) or path.stem
            cn_line = lines[0]
            en_line = lines[1] if len(lines)>1 else ""

    print(f"\n✔ {path.name}\n{cn_line}\n{en_line}\n{'-'*40}")
    fname = sanitize_filename(title) + ".txt"
    target = out_dir or path.parent
    target.mkdir(parents=True, exist_ok=True)
    out_path = get_unique_path(target / fname)
    out_path.write_text(txt[:s] + cn_line + "\n" + en_line + txt[e:], encoding="utf-8")

    if apply and out_dir is None and out_path != path:
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.move(str(path), str(bak))
        print(f"[重命名] {path.name} -> {out_path.name}")

# ───────────────── CLI ──────────────────

def main():
    ap = argparse.ArgumentParser(description="修复 txt 引文并按题目重命名（DeepSeek 三行提取 v5）")
    ap.add_argument("folder", help="目标文件夹")
    ap.add_argument("--apply", action="store_true", help="覆盖并重命名")
    ap.add_argument("--offline", action="store_true", help="仅本地处理，不调用 DeepSeek")
    ap.add_argument("--out", help="输出到此目录，原文件保留")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out).resolve() if args.out else None
    for p in pathlib.Path(args.folder).rglob("*.txt"):
        process(p, args.apply, args.offline, out_dir)

if __name__ == "__main__":
    main()
