from __future__ import annotations
import os, re, sys, json, pathlib, argparse, requests, textwrap, shutil
from typing import Tuple

API_KEY = os.getenv("DEEPSEEK_API_KEY")
HEADERS  = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
API_URL  = "https://api.deepseek.com/v1/chat/completions"
MODEL    = "deepseek-chat"

SYSTEM_PROMPT = textwrap.dedent("""
    你是学术排版助手。输入可能缺空格/换行，请输出**严格两行**：第一行中文引用，第二行英文引用。
    行末不可有多余空格，整体返回不要额外换行或缩进。
""")

# ───────────────── API & fallback ──────────────────

def call_deepseek(raw:str)->str:
    if not API_KEY:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": raw.strip()},
        ],
        "temperature": 0.2,
        "max_tokens" : 512,
    }
    r = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"].strip()
    if content.count("\n") < 1:
        content = local_fix(content)
    return content

def local_fix(raw:str)->str:
    txt = raw.replace("\n", " ")
    txt = re.sub(r"([。.,，；;:])(?=\S)", r"\1 ", txt)
    m = re.search(r"[A-Za-z]", txt)
    if not m:
        return txt
    idx = m.start()
    return f"{txt[:idx].strip()}\n{txt[idx:].strip()}"

# ───────────────── helper ──────────────────

def extract_block(text:str)->Tuple[int,int,str]|None:
    m = re.search(r"引文格式[\s\S]*?(?:\r?\n)(.+)$", text, re.MULTILINE)
    if not m:
        return None
    start = m.start(1)
    tail  = text[start:]
    m2    = re.search(r"\n\s*\n", tail)
    end   = start + (m2.start() if m2 else len(tail))
    return start, end, text[start:end]

# ───────────────── core ──────────────────

def process(path:pathlib.Path, apply:bool, offline:bool, out_dir:pathlib.Path|None):
    txt = path.read_text(encoding="utf-8", errors="ignore")
    res = extract_block(txt)
    if not res:
        print(f"[跳过] {path.name} 无引文格式")
        return
    s,e,raw = res
    fixed = local_fix(raw) if offline else call_deepseek(raw)

    # 打印预览
    print(f"\n✔ {path.name}\n{fixed}\n{'-'*40}")

    if apply and out_dir is None:
        # 直接覆盖原文件（先备份）
        backup = path.with_suffix(path.suffix+".bak")
        shutil.copy2(path, backup)
        path.write_text(txt[:s]+fixed+txt[e:], encoding="utf-8")
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / path.name
        out_path.write_text(txt[:s]+fixed+txt[e:], encoding="utf-8")

# ───────────────── CLI ──────────────────

def main():
    ap = argparse.ArgumentParser(description="修复所有 txt 的引文格式")
    ap.add_argument("folder", help="目标文件夹")
    ap.add_argument("--apply", action="store_true", help="覆盖原文件")
    ap.add_argument("--offline", action="store_true", help="不用 API，正则修补")
    ap.add_argument("--out", help="把修正版写到此目录，原文件不动")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out).resolve() if args.out else None

    for p in pathlib.Path(args.folder).rglob("*.txt"):
        process(p, args.apply, args.offline, out_dir)

if __name__ == "__main__":
    main()
