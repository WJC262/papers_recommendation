# rename_by_title.py
"""根据每个 txt 内的论文标题行重命名文件

目录结构假设：
    ./formatted_txt/xxx.txt

txt 格式示例：
    论文标题\n
    理想诱导环境下的网联车与网联自动驾驶车混合交通流建模研究\n
    摘要\n
脚本行为：
1. 遍历指定文件夹下所有 .txt。
2. 找到第一处出现 "论文标题" 的行；其下一行即论文标题。
3. 用标题内容生成新文件名：
      <标题>.txt
   - 先去除非法字符 \\/:*?"<>| 及首尾空格。
   - 若长度超 80 字符则截断。
   - 如目标文件已存在，用 (1)、(2)… 递增避免覆盖。
4. 执行 os.rename() 完成重命名。

使用::
    python rename_by_title.py ./formatted_txt

安全性：
- 只改文件名，不改文件内容。
- 如遇解析失败或找到重复标题，将打印警告并跳过。
"""

import os
import sys
import pathlib
import re

ILLEGAL_CHARS = r"\\/:*?\"<>|"
TRANS_TABLE = str.maketrans({c: "_" for c in ILLEGAL_CHARS})

MAX_LEN = 80


def extract_title(text: str) -> str | None:
    """返回标题（在出现"论文标题"行之后的第一行非空白文本）"""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "论文标题":
            # 找下一条非空行
            for j in range(i + 1, len(lines)):
                cand = lines[j].strip()
                if cand:
                    return cand
            break
    return None


def safe_filename(title: str, existing: set[str]) -> str:
    name = title.translate(TRANS_TABLE).strip()
    name = re.sub(r"\s+", " ", name)  # 合并连续空白
    if len(name) > MAX_LEN:
        name = name[:MAX_LEN].rstrip()
    base = name or "untitled"
    candidate = base + ".txt"
    idx = 1
    while candidate in existing:
        candidate = f"{base}({idx}).txt"
        idx += 1
    existing.add(candidate)
    return candidate


def main(folder: str):
    folder_path = pathlib.Path(folder).resolve()
    if not folder_path.is_dir():
        print(f"❌ 目录不存在: {folder_path}")
        sys.exit(1)

    existing_names: set[str] = set(os.listdir(folder_path))
    processed = 0
    skipped = 0

    for txt_path in folder_path.glob("*.txt"):
        content = txt_path.read_text(encoding="utf-8", errors="ignore")
        title = extract_title(content)
        if not title:
            print(f"[跳过] {txt_path.name} 未找到论文标题")
            skipped += 1
            continue
        new_name = safe_filename(title, existing_names)
        new_path = txt_path.with_name(new_name)
        txt_path.rename(new_path)
        print(f"✔ {txt_path.name} -> {new_name}")
        processed += 1

    print(f"\n完成：重命名 {processed} 个文件，跳过 {skipped} 个。")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python rename_by_title.py <folder>")
        sys.exit(1)
    main(sys.argv[1])
