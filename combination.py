# """
# paper_retrieval_fusion.py
# ------------------------------------------------
# • 读取 ./papers_txt 里的所有 .txt 论文
# • 分别建立 ①BM25 ②向量（FAISS + m3e-large）两套索引
# • 查询时：
#     1. 计算每篇文档的 BM25 分数 → Min-Max 归一化 → bm25_norm[i]
#     2. 计算每篇文档的 向量余弦相似度 → Min-Max 归一化 → vec_norm[i]
#     3. 融合分数 f_coarse[i] = w1*bm25_norm[i] + w2*vec_norm[i]
#     4. 动态阈值  thr = μ + n·σ  (默认 n=2)
#        仅保留 f_coarse ≥ thr 的文档
#     5. 输出按 f_coarse 降序的最终候选
# ------------------------------------------------
# """
# import os, torch, numpy as np, jieba
# from langchain.schema import Document
# from langchain.vectorstores import FAISS
# from langchain.embeddings.huggingface import HuggingFaceEmbeddings
# from rank_bm25 import BM25Okapi
# from typing import List

# TXT_DIR   = "./papers_txt"                # 论文 txt 文件夹
# EMB_MODEL = "./pre_train_model/m3e-large"  # HuggingFace 路径
# W1, W2    = 0, 1                      # 融合权重，可调
# N_SIGMA   = 1.5                           # μ + n·σ 里的 n


# # ---------- 1. 读文件 ----------
# docs: List[Document] = []
# fnames: List[str]   = []
# for fn in os.listdir(TXT_DIR):
#     if fn.lower().endswith(".txt"):
#         path = os.path.join(TXT_DIR, fn)
#         with open(path, encoding="utf-8") as f:
#             txt = f.read().strip()
#         if txt:
#             docs.append(Document(page_content=txt, metadata={"fname": fn}))
#             fnames.append(fn)
# assert docs, "文件夹为空？"


# # ---------- 2. 向量索引 ----------
# emb = HuggingFaceEmbeddings(
#     model_name=EMB_MODEL,
#     model_kwargs={"device": "cuda"},
#     encode_kwargs={"normalize_embeddings": True},
# )
# vect_db = FAISS.from_documents(docs, emb, distance_strategy="COSINE")
# torch.cuda.empty_cache()            # embedding 做完即可释放显存


# # ---------- 3. BM25 索引 ----------
# def jieba_tok(text: str):                # 搜索模式分词
#     return [w for w in jieba.cut_for_search(text) if w.strip()]

# tokenized = [jieba_tok(d.page_content) for d in docs]
# bm25 = BM25Okapi(tokenized)


# # ---------- 4. 查询函数 ----------
# def query_papers(query: str, top_k_print: int = 20):
#     # 4-1  BM25 原始分数
#     q_tok = jieba_tok(query)
#     bm25_raw = np.array(bm25.get_scores(q_tok), dtype=float)

#     # 4-2  向量余弦相似度  (dist = ||u-v||² , cos = 1 - dist/2)
#     dists = np.array(
#         [dist for _, dist in vect_db.similarity_search_with_score(query, k=len(docs))],
#         dtype=float,
#     )
#     vec_raw = 1.0 - dists / 2.0

#     # 4-3  两套分数各自 Min-Max 归一化 → [0,1]
#     def minmax(x):
#         return np.zeros_like(x) if x.max() - x.min() < 1e-9 else (x - x.min()) / (x.max() - x.min())

#     bm25_norm = minmax(bm25_raw)
#     vec_norm  = minmax(vec_raw)

#     # 4-4  融合分数
#     f_coarse = W1 * bm25_norm + W2 * vec_norm

#     # 4-5  动态阈值 μ + nσ
#     mu, sigma = f_coarse.mean(), f_coarse.std()
#     thr = mu + N_SIGMA * sigma
#     keep_mask = f_coarse >= thr

#     # 4-6  汇总并排序
#     results = [
#         (fnames[i], float(f_coarse[i]), float(bm25_norm[i]), float(vec_norm[i]))
#         for i in range(len(docs)) if keep_mask[i]
#     ]
#     results.sort(key=lambda x: x[1], reverse=True)

#     # 4-7  打印
#     print(f"\n🟢 查询: {query!r}")
#     print(f"候选总数: {len(docs)}  →  通过阈值(μ+{N_SIGMA}σ)  = {thr:.4f}  保留 {len(results)} 篇\n")
#     print(f"{'Rank':<4} {'Score':>7}   {'BM25':>5}  {'Vec':>5}   Filename")
#     for rank, (fname, s, b, v) in enumerate(results[:top_k_print], 1):
#         print(f"{rank:<4} {s:7.4f}   {b:5.2f}  {v:5.2f}   {fname}")

#     return results


# # ---------- 5. DEMO ----------
# if __name__ == "__main__":
#     query_papers("路口")           # 随意替换查询


"""
paper_retrieval_fusion.py
------------------------------------------------
• 读取 ./papers_txt 里的所有 .txt 论文
• 分别建立 ①BM25 ②向量（FAISS + m3e-large）两套索引
• 查询时：
    1. 计算每篇文档的 BM25 分数 → Min-Max 归一化 → bm25_norm[i]
    2. 计算每篇文档的 向量余弦相似度 → Min-Max 归一化 → vec_norm[i]
    3. 融合分数 f_coarse[i] = w1*bm25_norm[i] + w2*vec_norm[i]
    4. 动态阈值  thr = μ + n·σ  (默认 n=2)
       仅保留 f_coarse ≥ thr 的文档
    5. 输出按 f_coarse 降序的最终候选
------------------------------------------------
"""
import os
import torch
import numpy as np
import jieba
from langchain.schema import Document
from langchain.vectorstores import FAISS
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi
from typing import List

# 论文 txt 文件夹
TXT_DIR   = "./papers_txt"
# HuggingFace m3e-large 模型路径
EMB_MODEL = "./pre_train_model/m3e-large"
# 融合权重
W1, W2    = 0.2, 0.8
# μ + nσ 里的 n（阈值系数）
N_SIGMA   = 1.5


# ---------- 1. 读文件 ----------
docs: List[Document] = []
fnames: List[str]   = []
for fn in os.listdir(TXT_DIR):
    if fn.lower().endswith(".txt"):
        path = os.path.join(TXT_DIR, fn)
        with open(path, encoding="utf-8") as f:
            txt = f.read().strip()
        if txt:
            docs.append(Document(page_content=txt, metadata={"fname": fn}))
            fnames.append(fn)
assert docs, "文件夹为空？"


# ---------- 2. 向量索引 ----------
emb = HuggingFaceEmbeddings(
    model_name=EMB_MODEL,
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True},
)
vect_db = FAISS.from_documents(docs, emb, distance_strategy="COSINE")
torch.cuda.empty_cache()  # embedding 做完即可释放显存


# ---------- 3. BM25 索引 ----------
def jieba_tok(text: str):
    # 搜索模式分词
    return [w for w in jieba.cut_for_search(text) if w.strip()]

tokenized = [jieba_tok(d.page_content) for d in docs]
bm25 = BM25Okapi(tokenized)


# ---------- 4. 查询函数 ----------
def query_papers(query: str, top_k_print: int = 20):
    # 4-1  BM25 原始分数
    q_tok = jieba_tok(query)
    bm25_raw = np.array(bm25.get_scores(q_tok), dtype=float)

    # 4-2  向量余弦相似度  (dist = ||u-v||² , cos = 1 - dist/2)
    # 注意：FAISS 返回的结果是按相似度排序的列表，我们要把它映射回原始 docs 顺序
    docs_dists = vect_db.similarity_search_with_score(query, k=len(docs))
    # 构建 fname -> dist 映射
    dist_map = {doc.metadata["fname"]: dist for doc, dist in docs_dists}
    # 保证顺序与 docs 一致
    dists = np.array([dist_map[d.metadata["fname"]] for d in docs], dtype=float)
    vec_raw = 1.0 - dists / 2.0

    # 4-3  两套分数各自 Min-Max 归一化 → [0,1]
    def minmax(x):
        return np.zeros_like(x) if x.max() - x.min() < 1e-9 else (x - x.min()) / (x.max() - x.min())

    bm25_norm = minmax(bm25_raw)
    vec_norm  = minmax(vec_raw)

    # 4-4  融合分数
    f_coarse = W1 * bm25_norm + W2 * vec_norm

    # 4-5  动态阈值 μ + nσ
    mu, sigma = f_coarse.mean(), f_coarse.std()
    thr = mu + N_SIGMA * sigma
    keep_mask = f_coarse >= thr

    # 4-6  汇总并排序
    results = [
        (fnames[i], float(f_coarse[i]), float(bm25_norm[i]), float(vec_norm[i]))
        for i in range(len(docs)) if keep_mask[i]
    ]
    results.sort(key=lambda x: x[1], reverse=True)

    # 4-7  打印
    print(f"\n🟢 查询: {query!r}")
    print(f"候选总数: {len(docs)}  →  通过阈值(μ+{N_SIGMA}σ)  = {thr:.4f}  保留 {len(results)} 篇\n")
    print(f"{'Rank':<4} {'Score':>7}   {'BM25':>5}  {'Vec':>5}   Filename")
    for rank, (fname, s, b, v) in enumerate(results[:top_k_print], 1):
        print(f"{rank:<4} {s:7.4f}   {b:5.2f}  {v:5.2f}   {fname}")

    return results


# ---------- 5. DEMO ----------
if __name__ == "__main__":
    query_papers("关于交叉口的研究")  # 随意替换查询

