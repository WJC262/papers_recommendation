# AI 智慧检索 - 多期刊学术论文搜索与推荐系统

一个面向交通领域的学术论文智能检索平台，结合关键词匹配（BM25）与语义向量检索（FAISS + M3E），支持多期刊论文搜索、按年卷浏览、AI 摘要生成和引文管理。

## 功能特性

- **混合检索引擎** - BM25 关键词匹配 + FAISS 语义向量检索，加权融合排序（20% BM25 + 80% 向量），动态阈值过滤
- **多期刊支持** - 覆盖《交通运输工程与信息学报》《公路交通科技》《交通运输研究》三本期刊
- **按年卷浏览** - 按年份和期号浏览各期刊论文列表
- **AI 一句话摘要** - 基于 DeepSeek API 生成论文一句话总结，支持缓存
- **引文格式提取** - 自动提取并展示引文格式，一键复制
- **PDF 下载** - 直接获取论文 PDF 全文
- **数据分析看板** - 基于 Streamlit 的搜索趋势、热词统计、用户行为分析

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI, Uvicorn, LangChain, FAISS (CPU), rank-bm25, jieba, HuggingFace Embeddings (M3E-Large) |
| 前端 | React 19, Ant Design, Vite 6, Axios |
| AI 摘要 | DeepSeek Chat API |
| 数据看板 | Streamlit, Pandas |

## 项目结构

```
├── api.py                    # FastAPI 主服务（API 路由、摘要生成、日志记录）
├── retrieval_cpu.py          # 检索引擎（BM25 + FAISS 混合排序）
├── service.py                # 业务逻辑层
├── dashboard.py / app.py     # Streamlit 数据分析看板
├── requirements.txt          # Python 依赖
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── App.jsx           # 主组件
│   │   ├── api.js            # API 请求封装
│   │   └── components/
│   │       ├── SearchForm.jsx        # 搜索表单 + 期刊选择
│   │       ├── ResultList.jsx        # 搜索结果列表
│   │       └── YearIssueSelector.jsx # 年卷浏览选择器
│   ├── package.json
│   └── vite.config.js
├── faiss_index_9_6/          # 预构建 FAISS 向量索引
├── pre_train_model/          # M3E-Large 嵌入模型（本地）
├── all_txt_*/                # 各期刊论文文本文件
└── papers_pdf_new/           # 论文 PDF 文件
```

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- 预构建的 FAISS 索引（`faiss_index_9_6/`）
- M3E-Large 模型（`pre_train_model/m3e-large`）

### 后端启动

```bash
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000
```

### 前端构建

```bash
cd frontend
npm install
npm run build
```

构建产物位于 `frontend/dist/`，由 FastAPI 静态文件服务提供。

### 数据分析看板（可选）

```bash
streamlit run dashboard.py
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/search` | 按关键词 + 期刊筛选搜索论文 |
| GET | `/api/journals` | 获取可用期刊列表 |
| GET | `/api/papers-by-year-issue` | 按年卷浏览论文 |
| POST | `/api/generate-summary` | 生成论文一句话摘要 |
| POST | `/api/log-action` | 记录用户行为（引用/下载） |
| GET | `/pdfs/*` | 论文 PDF 静态文件 |

## 检索算法

1. 使用 jieba 对查询进行中文分词
2. BM25 计算关键词相关性分数
3. FAISS 计算语义向量相似度分数
4. Min-Max 归一化后加权融合（W1=0.2, W2=0.8）
5. 基于标准差（1.5 sigma）的动态阈值过滤
6. 标题命中关键词额外加分
7. 按融合分数降序返回结果

## 环境变量

在项目根目录创建 `.env` 文件：

```
DEEPSEEK_API_KEY=your_api_key_here
```
