import os
import re
import jieba
import numpy as np
from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

# 配置区
TXT_DIRS = {
    "jtysgcyxxxb": "./all_txt_jtysgcyxxxb",  # 交通运输工程与信息学报
    "gljtkj": "./all_txt_gljtkj",            # 公路交通科技
    "jtysyj": "./all_txt_jtysyj"             # 交通运输研究
}
PDF_DIR = "./papers_pdf_new"
EMB_MODEL = "./pre_train_model/m3e-large"
INDEX_DIR = "faiss_index_9_6"  # 使用现有的索引目录
W1, W2 = 0.2, 0.8
N_SIGMA = 1.5

# 期刊名称映射
JOURNAL_NAMES = {
    "jtysgcyxxxb": "交通运输工程与信息学报",
    "gljtkj": "公路交通科技",
    "jtysyj": "交通运输研究"
}

# 预加载所有文本
docs: List[Document] = []
fnames, citations, abstracts, journals, years, authors = [], [], [], [], [], []

def extract_citation(txt: str) -> str:
    m = re.search(r"引文格式\s*\n(.*)", txt, re.S)
    return m.group(1).strip() if m else ""

def extract_year(txt: str) -> str:
    """从引文中提取年份"""
    citation = extract_citation(txt)
    if not citation:
        return ""
    
    # 匹配引文中的发表年：2016–2019、2020–2029、2030–2039（可按需再扩）
    year_pattern = r'(201[6-9]|202[0-9]|203[0-9])'
    match = re.search(year_pattern, citation)
    return match.group(1) if match else ""

def extract_author(txt: str) -> str:
    """从引文中提取作者信息"""
    citation = extract_citation(txt)
    if not citation:
        return ""
    
    # 从引文开头到第一个句号之间的部分就是作者
    # 去掉开头的空白字符
    citation = citation.strip()
    # 找到第一个句号的位置
    dot_pos = citation.find('.')
    if dot_pos != -1:
        return citation[:dot_pos].strip()
    else:
        # 如果没有句号，返回整个引文
        return citation

def extract_abstract(txt: str) -> str:
    # 使用多层级匹配策略，按优先级尝试不同的边界模式
    patterns = [
        # 模式1：摘要到关键词（作为章节标题，前后都有换行）
        r"摘要\s*(.*?)(?=\n\s*关键词\s*\n)",
        # 模式2：摘要到关键字（作为章节标题，前后都有换行）
        r"摘要\s*(.*?)(?=\n\s*关键字\s*\n)",
        # 模式3：摘要到引言（如果关键词部分缺失）
        r"摘要\s*(.*?)(?=\n\s*引言\s*\n)",
        # 模式4：备用方案 - 摘要到双换行
        r"摘要\s*(.*?)(?=\n\s*\n)",
        # 模式5：最后备用 - 摘要到文档结束
        r"摘要\s*(.*?)(?=\Z)"
    ]
    
    for pattern in patterns:
        m = re.search(pattern, txt, re.S)
        if m:
            return m.group(1).strip()
    
    return ""

def get_available_journals() -> List[dict]:
    """获取所有可用的期刊列表"""
    return [
        {"code": code, "name": name} 
        for code, name in JOURNAL_NAMES.items()
    ]

# 遍历所有期刊目录，加载所有论文
for journal_code, txt_dir in TXT_DIRS.items():
    if not os.path.exists(txt_dir):
        print(f"警告：目录 {txt_dir} 不存在，跳过")
        continue
    
    for fn in os.listdir(txt_dir):
        if not fn.lower().endswith(".txt"):
            continue
        path = os.path.join(txt_dir, fn)
        with open(path, encoding="utf-8") as f:
            txt = f.read().strip()
        if not txt:
            continue
        
        docs.append(Document(page_content=txt, metadata={"fname": fn, "journal": journal_code}))
        fnames.append(fn)
        citations.append(extract_citation(txt))
        abstracts.append(extract_abstract(txt))
        journals.append(journal_code)
        years.append(extract_year(txt))
        authors.append(extract_author(txt))

if not docs:
    raise RuntimeError(f"没有找到任何论文文件！")

print(f">>> 加载了 {len(docs)} 篇论文，来自 {len(set(journals))} 个期刊")

# 加载/构建FAISS索引
print(">>> 初始化 Embeddings 模型（CPU）...")
emb = HuggingFaceEmbeddings(
    model_name=EMB_MODEL,
    model_kwargs={"device": "cpu", "local_files_only": True},
    encode_kwargs={"normalize_embeddings": True},
)

if os.path.exists(INDEX_DIR):
    print(f">>> 从磁盘加载 FAISS 索引（{INDEX_DIR}）...")
    vect_db = FAISS.load_local(INDEX_DIR, emb, allow_dangerous_deserialization=True)
else:
    print(">>> 构建 FAISS 索引（首次运行会比较慢，请耐心等候）...")
    vect_db = FAISS.from_documents(docs, emb, distance_strategy="COSINE")
    vect_db.save_local(INDEX_DIR)
    print(f">>> FAISS 索引已保存到 {INDEX_DIR}/")

# 构建BM25索引
def jieba_tok(text: str):
    return [w for w in jieba.cut_for_search(text) if w.strip()]

bm25 = BM25Okapi([jieba_tok(d.page_content) for d in docs])

# 查询接口
def search(query: str, selected_journals: List[str] = None, w1=W1, w2=W2, n_sigma=N_SIGMA, top_k=20):
    """
    搜索论文
    :param query: 查询词
    :param selected_journals: 选择的期刊代码列表，如 ["jtysgcyxxxb", "gljtkj"]，None表示搜索所有期刊
    :param w1, w2: 融合权重
    :param n_sigma: 阈值倍数
    :param top_k: 返回结果数量
    """
    # 1. BM25 原始分数
    bm25_raw = np.array(bm25.get_scores(jieba_tok(query)), dtype=float)

    # 2. 向量相似度计算
    vec_raw = np.zeros(len(docs))
    
    # 从FAISS索引中获取已索引的文档列表
    indexed_docs = set()
    for doc_id in vect_db.docstore._dict:
        doc = vect_db.docstore._dict[doc_id]
        if hasattr(doc, 'metadata') and doc.metadata and 'fname' in doc.metadata:
            indexed_docs.add(doc.metadata['fname'])
    
    # 只为索引中的文档计算向量相似度
    if indexed_docs:
        k = min(len(indexed_docs), len(vect_db.docstore._dict))
        doc_dists = vect_db.similarity_search_with_score(query, k=k)
        dist_map = {d.metadata["fname"]: dist for d, dist in doc_dists}
        
        # 将向量分数映射回原始文档索引
        for i, fn in enumerate(fnames):
            if fn in indexed_docs:
                vec_raw[i] = 1.0 - dist_map[fn] / 2.0 if fn in dist_map else 0.0
            else:
                # 新文档的向量分数设为0
                vec_raw[i] = 0.0

    # 3. Min-Max 归一化
    def minmax(x: np.ndarray) -> np.ndarray:
        return np.zeros_like(x) if x.ptp() < 1e-9 else (x - x.min()) / x.ptp()
    bm25_n = minmax(bm25_raw)
    vec_n = minmax(vec_raw)

    # 4. 融合分数计算
    f_score = np.zeros(len(docs))
    for i in range(len(docs)):
        # 检查文档是否在FAISS索引中
        doc_in_index = False
        for doc_id in vect_db.docstore._dict:
            doc = vect_db.docstore._dict[doc_id]
            if hasattr(doc, 'metadata') and doc.metadata and 'fname' in doc.metadata:
                if doc.metadata['fname'] == fnames[i]:
                    doc_in_index = True
                    break
        
        if doc_in_index:
            # 原有文档：使用混合分数 w1 * bm25_n + w2 * vec_n
            f_score[i] = w1 * bm25_n[i] + w2 * vec_n[i]
        else:
            # 新文档：BM25权重100%，向量权重0%
            f_score[i] = 1.0 * bm25_n[i] + 0.0 * vec_n[i]  # 即 f_score[i] = bm25_n[i]

    # 5. 动态阈值筛选
    thr = f_score.mean() + n_sigma * f_score.std()
    keep_idx = np.where(f_score >= thr)[0]

    # 6. 期刊过滤
    if selected_journals:
        # 只保留选中期刊的论文
        filtered_idx = []
        for i in keep_idx:
            if journals[i] in selected_journals:
                filtered_idx.append(i)
        keep_idx = np.array(filtered_idx)

    # 7. 收集并排序结果
    results = []
    seen_titles = set()  # 用于去重的标题集合
    
    for i in keep_idx:
        pdf_name = os.path.splitext(fnames[i])[0] + ".pdf"
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        
        # 获取论文标题（去掉"11"前缀）
        title = fnames[i].replace('.txt', '')
        clean_title = title.replace('11', '', 1) if title.startswith('11') else title  # 去掉开头的"11"
        
        # 如果已经见过这个标题，跳过
        if clean_title in seen_titles:
            continue
        
        seen_titles.add(clean_title)
        
        results.append({
            "rank_score": float(f_score[i]),
            "bm25": float(bm25_n[i]),
            "vec": float(vec_n[i]),
            "filename": fnames[i],
            "abstract": abstracts[i],
            "pdf_path": pdf_path if os.path.exists(pdf_path) else None,
            "citation": citations[i],
            "journal": journals[i],
            "journal_name": JOURNAL_NAMES.get(journals[i], journals[i]),
            "year": years[i],
            "author": authors[i]
        })
        
    # 8. 标题匹配加分
    key = query.lower().strip()
    for r in results:
        title = os.path.splitext(r["filename"])[0].lower()
        if key in title:  # 命中标题
            r["rank_score"] += 1  # 直接 +1，保证 > 未命中最高分
    
    results.sort(key=lambda x: x["rank_score"], reverse=True)
    return results[:top_k], len(keep_idx), thr

def get_papers_by_year_issue(year: str, issue: str, journal_code: str = None):
    """
    根据年份和期数获取论文列表
    支持两个期刊：jtysgcyxxxb (交通运输工程与信息学报) 和 gljtkj (公路交通科技)
    :param year: 年份
    :param issue: 期数
    :param journal_code: 期刊代码，如果指定则只返回该期刊的论文
    """
    import os
    import re
    from pathlib import Path
    
    results = []
    seen_titles = set()  # 用于去重的标题集合
    
    print(f"开始查找年份: {year}, 期数: {issue}")
    
    # 定义期刊目录映射
    journal_dirs = {
        "jtysgcyxxxb": Path("all_txt_jtysgcyxxxb"),
        "gljtkj": Path("all_txt_gljtkj"),
        "jtysyj": Path("all_txt_jtysyj")
    }
    
    # 使用与配置一致的PDF目录
    pdf_dir = Path(PDF_DIR)
    
    # 根据期刊选择不同的文件清单
    if journal_code == "gljtkj":
        mapping_file = Path("文件夹和文件清单_2.txt")
        print(f"使用公路交通科技文件清单: {mapping_file}")
    elif journal_code == "jtysyj":
        mapping_file = Path("文件夹和文件清单_3.txt")
        print(f"使用交通运输研究文件清单: {mapping_file}")
    else:
        mapping_file = Path("文件夹和文件清单.txt")
        print(f"使用交通运输工程与信息学报文件清单: {mapping_file}")
    
    if not mapping_file.exists():
        print(f"映射文件不存在: {mapping_file}")
        # 如果没有映射文件，返回所有论文
        for journal_code, txt_dir in journal_dirs.items():
            if not txt_dir.exists():
                print(f"期刊目录不存在: {txt_dir}")
                continue
                
            print(f"搜索期刊: {JOURNAL_NAMES.get(journal_code, journal_code)}")
            
            # 遍历该期刊下的所有文件
            for txt_file in txt_dir.glob("*.txt"):
                filename = txt_file.stem
                
                try:
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    abstract = extract_abstract(content)
                    citation = extract_citation(content)
                    year_extracted = extract_year(content)
                    author_extracted = extract_author(content)
                    
                    # 获取论文标题（去掉"11"前缀）用于去重
                    clean_title = filename.replace('11', '', 1) if filename.startswith('11') else filename
                    
                    # 如果已经见过这个标题，跳过
                    if clean_title in seen_titles:
                        continue
                    
                    seen_titles.add(clean_title)
                    
                    pdf_file = pdf_dir / f"{filename}.pdf"
                    pdf_path = str(pdf_file) if pdf_file.exists() else None
                    
                    result = {
                        "filename": f"{filename}.txt",
                        "abstract": abstract,
                        "citation": citation,
                        "pdf_path": pdf_path,
                        "rank_score": 1.0,
                        "bm25": 1.0,
                        "vec": 1.0,
                        "year": year_extracted if year_extracted else year,
                        "issue": issue,
                        "journal": journal_code,
                        "journal_name": JOURNAL_NAMES.get(journal_code, journal_code),
                        "author": author_extracted
                    }
                    results.append(result)
                    
                except Exception as e:
                    print(f"读取文件失败 {txt_file}: {e}")
                    continue
        
        print(f"总共找到 {len(results)} 个论文")
        return results
    
    print(f"映射文件存在: {mapping_file}")
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"映射文件内容长度: {len(content)}")
    
    # 查找对应年份期数的论文列表
    if journal_code == "jtysyj":
        # 交通运输研究使用不同的格式：交通运输研究_2025_1
        section_pattern = rf"文件夹: 交通运输研究_{year}_{int(issue)} \({year}年第{issue.zfill(2)}期\)\n文件数量: (\d+)个\n文件列表:\n(.*?)(?=\n\n|$)"
    else:
        # 其他期刊使用标准格式：2025_01
        section_pattern = rf"文件夹: {year}_{issue.zfill(2)} \({year}年第{issue.zfill(2)}期\)\n文件数量: (\d+)个\n文件列表:\n(.*?)(?=\n\n|$)"
    
    print(f"搜索模式: {section_pattern}")
    match = re.search(section_pattern, content, re.DOTALL)
    
    if not match:
        print(f"未找到年份期数匹配: {year}_{issue.zfill(2)}")
        # 尝试查找所有年份期数
        all_matches = re.findall(r"文件夹: (\d{4}_\d{2})", content)
        print(f"找到的所有年份期数: {all_matches}")
        return results
    
    print(f"找到匹配的年份期数: {year}_{issue.zfill(2)}")
    
    file_list_text = match.group(2)
    lines = file_list_text.strip().split('\n')
    print(f"找到 {len(lines)} 行文件列表")
    
    # 创建文件名集合，用于快速查找
    target_files = set()
    for line in lines:
        if line.strip() and '.txt' in line:
            # 提取文件名（去掉序号和.txt后缀）
            parts = line.strip().split('. ')
            if len(parts) >= 2:
                title = parts[1].replace('.txt', '')
                target_files.add(title)
                print(f"目标文件: {title}")
    
    # 遍历所有期刊目录，查找匹配的文件
    for journal_code, txt_dir in journal_dirs.items():
        if not txt_dir.exists():
            print(f"期刊目录不存在: {txt_dir}")
            continue
            
        print(f"搜索期刊: {JOURNAL_NAMES.get(journal_code, journal_code)}")
        
        # 遍历该期刊下的所有文件
        for txt_file in txt_dir.glob("*.txt"):
            filename = txt_file.stem  # 去掉.txt后缀
            
            # 检查是否在目标文件列表中
            if filename in target_files:
                print(f"找到匹配文件: {filename}")
                
                try:
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    abstract = extract_abstract(content)
                    citation = extract_citation(content)
                    year_extracted = extract_year(content)
                    author_extracted = extract_author(content)
                    
                    # 获取论文标题（去掉"11"前缀）用于去重
                    clean_title = filename.replace('11', '', 1) if filename.startswith('11') else filename
                    
                    # 如果已经见过这个标题，跳过
                    if clean_title in seen_titles:
                        continue
                    
                    seen_titles.add(clean_title)
                    
                    pdf_file = pdf_dir / f"{filename}.pdf"
                    pdf_path = str(pdf_file) if pdf_file.exists() else None
                    
                    result = {
                        "filename": f"{filename}.txt",
                        "abstract": abstract,
                        "citation": citation,
                        "pdf_path": pdf_path,
                        "rank_score": 1.0,
                        "bm25": 1.0,
                        "vec": 1.0,
                        "year": year_extracted if year_extracted else year,
                        "issue": issue,
                        "journal": journal_code,
                        "journal_name": JOURNAL_NAMES.get(journal_code, journal_code),
                        "author": author_extracted
                    }
                    results.append(result)
                    
                except Exception as e:
                    print(f"读取文件失败 {txt_file}: {e}")
                    continue
    
    print(f"总共找到 {len(results)} 个论文")
    return results
