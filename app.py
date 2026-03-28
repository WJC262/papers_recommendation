import os
import requests
import streamlit as st
import streamlit.components.v1 as components
import uuid

# -------- 0. 后端地址 --------
API_URL = os.getenv("API_URL", "http://localhost:8000")

if "sid" not in st.session_state:
    st.session_state["sid"] = str(uuid.uuid4())

# -------- 1. 页面基础 & 主题配色 --------
st.set_page_config(page_title="论文检索", page_icon="📄", layout="wide")
os.environ.update({
    "STREAMLIT_THEME_BASE": "light",
    "STREAMLIT_THEME_PRIMARYCOLOR": "#306ce6",
    "STREAMLIT_THEME_BACKGROUNDCOLOR": "#F9FAFC",
    "STREAMLIT_THEME_SECONDARYBACKGROUNDCOLOR": "#FFFFFF",
    "STREAMLIT_THEME_TEXTCOLOR": "#2C3E50",
})

# -------- 2. 全局 CSS --------
st.markdown(
    """
<style>
html[data-theme="light"] .stApp,
html[data-theme="dark"]  .stApp {
  background: linear-gradient(135deg,#e6ebf4 0%,#f9fafc 100%) !important;
}
html[data-theme="light"] .stApp::before,
html[data-theme="dark"]  .stApp::before {
  content:"";position:fixed;inset:0;pointer-events:none;
  background-image:radial-gradient(#d8dde9 1px,transparent 1px);
  background-size:4px 4px;opacity:.35;
}
html[data-theme="light"] .main .block-container,
html[data-theme="dark"]  .main .block-container {
  background:rgba(255,255,255,.82)!important;
  backdrop-filter:blur(10px);border-radius:24px;padding:32px 24px 24px;
  box-shadow:0 8px 24px rgba(0,0,0,.06);
}
.center-box .stTextInput>div{width:600px;max-width:90vw;}
.hot-keywords{font-size:16px;color:#888;margin-bottom:20px;text-align:center;}
.hot-keywords a{color:#306ce6 !important;margin:0 8px;text-decoration:none;}
.hot-keywords a:hover{text-decoration:underline;}
header [data-testid="themeToggle"]{display:none !important;}
</style>
""",
    unsafe_allow_html=True,
)

# -------- 3. URL 参数 & 页面头部 --------
params = st.query_params
default_q = params.get("query", "")
if "query" not in st.session_state:
    st.session_state["query"] = default_q

st.markdown("<div class='center-box'>", unsafe_allow_html=True)
st.markdown(
    "<h1>📄 AI 智慧检索</h1>"
    "<p style='font-size:18px;color:#7f8c8d;margin-top:-10px;'>专为学术研究设计，助力高效检索文献</p>",
    unsafe_allow_html=True,
)

# -------- 4. 检索输入框 --------
query = st.text_input(
    "🔍 请输入查询词或一句话",
    placeholder="例如：无人驾驶 交叉口 老年人",
    key="query",
)
if query != st.session_state["query"]:
    st.session_state["query"] = query
    st.query_params.update({"query": query})

# -------- 5. 期刊多选（放在输入框下面） --------
st.markdown("**请选择期刊（可多选）：**")
ALL_JOURNALS = [
    "交通运输工程与信息学报",
    "交通运输研究",
    "交通信息系统工程与信息",
    "公路交通科技",
]
SUPPORTED_JOURNALS = {"交通运输工程与信息学报", "公路交通科技", "交通运输研究"}  # 支持的期刊

selected = []
for journal in ALL_JOURNALS:
    if st.checkbox(journal, value=(journal in SUPPORTED_JOURNALS), key=f"chk_{journal}"):
        selected.append(journal)

if not selected:
    st.info("⚠️ 请至少选择一个期刊后再检索。")
    st.stop()

st.markdown("</div>", unsafe_allow_html=True)

# -------- 6. 热门搜索 --------
st.markdown(
    """
<div class='hot-keywords'>
🔥 热门搜索：
<a href='?query=城市交通碳排放'>城市交通碳排放</a>｜
<a href='?query=车路协同'>车路协同</a>｜
<a href='?query=深度学习'>深度学习</a>｜
<a href='?query=公交优先'>公交优先</a>
</div>
""",
    unsafe_allow_html=True,
)

# -------- 7. 检索逻辑 --------
if query.strip():
    # 判断所选期刊中是否包含支持期刊
    effective_journal = next((j for j in selected if j in SUPPORTED_JOURNALS), None)
    if effective_journal is None:
        st.info("当前所选期刊暂无数据，请选择“交通运输工程与信息学报”。")
        st.stop()

    with st.spinner("检索中 ..."):
        try:
            resp = requests.get(
                f"{API_URL}/api/search",
                params={"q": query, "journal": effective_journal},
                timeout=60,
            )
            data = resp.json()
            results = data.get("results", [])
            total_count = data.get("total", 0)
        except Exception as e:
            st.error(f"后端接口调用失败：{e}")
            st.stop()

    st.markdown(f"**共检索到 {total_count} 篇文档**")

    if not results:
        st.markdown(
            """
        <div style="text-align:center;margin-top:40px;">
            <img src="https://cdn-icons-png.flaticon.com/512/2748/2748558.png" width="100">
            <p style="font-size:16px;color:#999;">没有找到相关结果，建议尝试其他关键词。</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        for idx, r in enumerate(results, 1):
            paper_id = os.path.splitext(r["filename"])[0]
            st.markdown(f"### {idx}. {paper_id}")
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(
                    f"<span style='font-family:SimHei;font-weight:bold;'>摘要：</span>{r['abstract']}",
                    unsafe_allow_html=True,
                )
                b1, b2 = st.columns(2)
                with b1:
                    if r.get("pdf_path"):
                        dl_key = f"dl-btn-{paper_id}"
                        if st.button("📥 准备下载 PDF", key=dl_key):
                            with open(r["pdf_path"], "rb") as f:
                                pdf_bytes = f.read()
                            st.download_button(
                                "👉 点此保存",
                                pdf_bytes,
                                file_name=os.path.basename(r["pdf_path"]),
                                mime="application/pdf",
                                key=f"pdf-{paper_id}",
                            )
                    else:
                        st.write("暂无 PDF")
                with b2:
                    btn_key = f"cite-btn-{paper_id}"
                    flag_key = f"show_cite_{paper_id}"
                    if st.button("📋 引用本文", key=btn_key):
                        st.session_state[flag_key] = not st.session_state.get(flag_key, False)
            with col2:
                st.metric("综合得分", f"{r['rank_score']:.3f}")
                st.progress(r["bm25"], text="BM25")
                st.progress(r["vec"], text="向量")
            if st.session_state.get(f"show_cite_{paper_id}", False):
                with st.expander("引用格式（点击一键复制）", expanded=True):
                    st.code(r["citation"], language="text")
                    escaped = r["citation"].replace("\\", "\\\\").replace("'", "\\'")
                    components.html(
                        f"""
                        <button onclick="navigator.clipboard.writeText('{escaped}')"
                                style="padding:6px 12px;border:none;background:#4caf50;color:white;border-radius:4px;cursor:pointer;">
                            复制到剪贴板
                        </button>
                        """,
                        height=40,
                    )
            st.divider()

# -------- 8. 页脚 --------
st.markdown(
    """
<hr style="border:none;border-top:1px solid #eee;" />
<div style="text-align:center;color:#aaa;font-size:14px;">
    © 论文推荐系统 · 2025 | <a href='mailto:jiachenwang_bjut@163.com'>联系我们</a>
</div>
""",
    unsafe_allow_html=True,
)

