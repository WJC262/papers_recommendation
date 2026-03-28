import os
import json
import numpy as np
import jieba
from langchain.schema import Document
from langchain.vectorstores import FAISS
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

# ─── 配置区 ───────────────────────────────────────────────────────────────────
TXT_DIR    = "./papers_txt"                    # 文本文件夹
EMB_MODEL  = "./pre_train_model/m3e-large"     # HuggingFace 模型路径
INDEX_DIR  = "faiss_index"                     # FAISS 索引保存目录
W1, W2     = 0.2, 0.8                            # 融合权重
N_SIGMA    = 1.5                                 # 阈值倍数

# ─── 1. 读取所有文档 ───────────────────────────────────────────────────────────
docs: list[Document] = []
fnames: list[str]   = []

for fn in os.listdir(TXT_DIR):
    if fn.lower().endswith(".txt"):
        path = os.path.join(TXT_DIR, fn)
        text = open(path, encoding="utf-8").read().strip()
        if text:
            docs.append(Document(page_content=text, metadata={"fname": fn}))
            fnames.append(fn)

if not docs:
    raise RuntimeError(f"目录 {TXT_DIR} 下没有 .txt 文档！")

# ─── 2. 加载／构建并持久化 FAISS 向量索引 ─────────────────────────────────────
print(">>> 初始化 Embeddings 模型 ...")
emb = HuggingFaceEmbeddings(
    model_name=EMB_MODEL,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

if os.path.exists(INDEX_DIR):
    print(f">>> 从磁盘加载 FAISS 索引（{INDEX_DIR}）...请确保索引由信任源生成")
    # 允许反序列化 pickle 文件，仅在信任来源时使用
    vect_db = FAISS.load_local(INDEX_DIR, emb, allow_dangerous_deserialization=True)
else:
    print(">>> 构建 FAISS 索引（首次运行会比较慢，请耐心等候）...")
    vect_db = FAISS.from_documents(docs, emb, distance_strategy="COSINE")
    vect_db.save_local(INDEX_DIR)
    print(f">>> FAISS 索引已保存到 {INDEX_DIR}/")

# ─── 3. 构建 BM25 索引 ───────────────────────────────────────────────────────
def jieba_tok(text: str) -> list[str]:
    return [w for w in jieba.cut_for_search(text) if w.strip()]

tokenized = [jieba_tok(d.page_content) for d in docs]
bm25 = BM25Okapi(tokenized)

# ─── 4. 查询函数 ─────────────────────────────────────────────────────────────
def query_papers(query: str, top_k_print: int = 20):
    # BM25 原始分
    q_tok     = jieba_tok(query)
    bm25_raw  = np.array(bm25.get_scores(q_tok), dtype=float)

    # 向量相似度
    docs_dists = vect_db.similarity_search_with_score(query, k=len(docs))
    dist_map   = {doc.metadata["fname"]: dist for doc, dist in docs_dists}
    dists      = np.array([dist_map[d.metadata["fname"]] for d in docs], dtype=float)
    vec_raw    = 1.0 - dists / 2.0

    # Min-Max 归一化
    def minmax(x):
        return np.zeros_like(x) if x.max() - x.min() < 1e-9 else (x - x.min()) / (x.max() - x.min())

    bm25_norm = minmax(bm25_raw)
    vec_norm  = minmax(vec_raw)
    f_coarse  = W1 * bm25_norm + W2 * vec_norm

    # 阈值筛选
    mu, sigma = f_coarse.mean(), f_coarse.std()
    thr       = mu + N_SIGMA * sigma
    keep_mask = f_coarse >= thr

    # 汇总结果
    results = [
        (fnames[i], float(f_coarse[i]), float(bm25_norm[i]), float(vec_norm[i]))
        for i in range(len(docs)) if keep_mask[i]
    ]
    results.sort(key=lambda x: x[1], reverse=True)

    # 打印
    print(f"\n🟢 查询：{query!r}")
    print(f"候选总数：{len(docs)}  →  阈值 = {thr:.4f}  保留 {len(results)} 篇\n")
    print(f"{'Rank':<4} {'Score':>7}   {'BM25':>5}  {'Vec':>5}   Filename")
    for rank, (fname, s, b, v) in enumerate(results[:top_k_print], 1):
        print(f"{rank:<4} {s:7.4f}   {b:5.2f}  {v:5.2f}   {fname}")

    return results

# ─── 5. 主程序调用（在此处定义你的查询，无需 interactive input） ─────────────────
QUERIES = [
    "关于交叉口的研究",  # 示例：可以添加更多查询条件
]

if __name__ == "__main__":
    for q in QUERIES:
        query_papers(q)


