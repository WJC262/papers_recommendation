python3 - <<'EOF'
import os, urllib.parse
PDF_DIR = "papers_pdf_new"    # 根据你实际的 PDF 存放目录改路径
for fn in os.listdir(PDF_DIR):
    if "跨境电商" in fn:
        print("原始文件名:", fn)
        print("编码后 URL 片段:", urllib.parse.quote(fn))
        print()
EOF
