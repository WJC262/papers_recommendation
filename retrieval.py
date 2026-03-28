# retrieval.py
import os
import re
import torch
import jieba
import numpy as np
from typing import List
from langchain.schema import Document
from langchain.vectorstores import FAISS
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

TXT_DIR   = "./papers_txt_2"
PDF_DIR   = "./papers_pdf"
EMB_MODEL = "./pre_train_model/m3e-large"

# ---------- 预加载所有文本 ----------
docs: List[Document] = []
fnames, citations, abstracts = [], [], []

def extract_citation(txt: str) -> str:
    """从全文中抓取【引文格式】段落（若不存在返回空串）"""
    m = re.search(r"引文格式\s*\n(.*)", txt, re.S)
    return m.group(1).strip() if m else ""

def extract_abstract(txt: str) -> str:
    """
    从全文中提取摘要段落（“摘要：”到“关键词：”之间的内容）
    若没有关键词标签，则提取“摘要：”后面的第一段内容
    """
    m = re.search(r"摘要\s*(.*?)(?=(关键词|关键字))", txt, re.S)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"摘要[:：]\s*(.*?)(?:\n\n|\Z)", txt, re.S)
    return m2.group(1).strip() if m2 else ""

for fn in os.listdir(TXT_DIR):
    if not fn.lower().endswith(".txt"):
        continue
    path = os.path.join(TXT_DIR, fn)
    with open(path, encoding="utf-8") as f:
        txt = f.read().strip()
    if not txt:
        continue
    docs.append(Document(page_content=txt, metadata={"fname": fn}))
    fnames.append(fn)
    citations.append(extract_citation(txt))
    abstracts.append(extract_abstract(txt))

# ---------- 向量 & BM25 索引 ----------
emb = HuggingFaceEmbeddings(
    model_name=EMB_MODEL,
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True},
)
vect_db = FAISS.from_documents(docs, emb, distance_strategy="COSINE")
torch.cuda.empty_cache()

def jieba_tok(text: str):
    return [w for w in jieba.cut_for_search(text) if w.strip()]

bm25 = BM25Okapi([jieba_tok(d.page_content) for d in docs])

# ---------- 查询接口 ----------
def search(query: str, w1=0.2, w2=0.8, n_sigma=1.5, top_k=20):
    # 1. BM25 原始分数
    bm25_raw = np.array(bm25.get_scores(jieba_tok(query)), dtype=float)

    # 2. 向量相似度
    doc_dists = vect_db.similarity_search_with_score(query, k=len(docs))
    dist_map  = {d.metadata["fname"]: dist for d, dist in doc_dists}
    dists     = np.array([dist_map[d.metadata["fname"]] for d in docs])
    vec_raw   = 1.0 - dists / 2.0

    # 3. 归一化
    mm = lambda x: np.zeros_like(x) if x.ptp() < 1e-9 else (x - x.min()) / x.ptp()
    bm25_n, vec_n = mm(bm25_raw), mm(vec_raw)

    # 4. 融合
    f = w1 * bm25_n + w2 * vec_n

    # 5. 动态阈值
    thr = f.mean() + n_sigma * f.std()
    keep = np.where(f >= thr)[0]

    # 6. 收集结果
    results = []
    for i in keep:
        pdf_name = os.path.splitext(fnames[i])[0] + ".pdf"
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        results.append({
            "rank_score": float(f[i]),
            "bm25":       float(bm25_n[i]),
            "vec":        float(vec_n[i]),
            "filename":   fnames[i],
            "abstract":   abstracts[i],
            "pdf_path":   pdf_path if os.path.exists(pdf_path) else None,
            "citation":   citations[i],
        })

    # 按综合得分排序并返回
    results.sort(key=lambda x: x["rank_score"], reverse=True)
    return results[:top_k], len(keep), thr




