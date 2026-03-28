import os
import json
import logging
import aiohttp
import asyncio
import re
import pickle
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse

import service  # 你的检索逻辑模块

# ───────────────────────────────────────────────
# 0. 概述缓存系统
# ───────────────────────────────────────────────
SUMMARY_CACHE_FILE = "summary_cache.pkl"
SUMMARY_CACHE_JSON = "summary_cache.json"
summary_cache = {}

def load_summary_cache():
    """加载概述缓存"""
    global summary_cache
    # 优先尝试加载pkl文件
    if os.path.exists(SUMMARY_CACHE_FILE):
        try:
            with open(SUMMARY_CACHE_FILE, 'rb') as f:
                summary_cache = pickle.load(f)
            print(f"已加载概述缓存（pkl），包含 {len(summary_cache)} 条记录")
        except Exception as e:
            print(f"加载pkl缓存失败: {e}")
            # 如果pkl失败，尝试加载JSON
            if os.path.exists(SUMMARY_CACHE_JSON):
                try:
                    with open(SUMMARY_CACHE_JSON, 'r', encoding='utf-8') as f:
                        summary_cache = json.load(f)
                    print(f"已加载概述缓存（JSON），包含 {len(summary_cache)} 条记录")
                except Exception as e2:
                    print(f"加载JSON缓存也失败: {e2}")
                    summary_cache = {}
            else:
                summary_cache = {}
    # 如果pkl不存在，尝试加载JSON
    elif os.path.exists(SUMMARY_CACHE_JSON):
        try:
            with open(SUMMARY_CACHE_JSON, 'r', encoding='utf-8') as f:
                summary_cache = json.load(f)
            print(f"已加载概述缓存（JSON），包含 {len(summary_cache)} 条记录")
        except Exception as e:
            print(f"加载JSON缓存失败: {e}")
            summary_cache = {}
    else:
        print("未找到缓存文件，使用空缓存")
        summary_cache = {}

def save_summary_cache():
    """保存概述缓存（同时保存pkl和JSON格式）"""
    try:
        # 保存pkl格式（高性能）
        with open(SUMMARY_CACHE_FILE, 'wb') as f:
            pickle.dump(summary_cache, f)
        
        # 保存JSON格式（人类可读）
        with open(SUMMARY_CACHE_JSON, 'w', encoding='utf-8') as f:
            json.dump(summary_cache, f, ensure_ascii=False, indent=2)
        
        print(f"概述缓存已保存（pkl+JSON），包含 {len(summary_cache)} 条记录")
    except Exception as e:
        print(f"保存概述缓存失败: {e}")

def get_cached_summary(paper_title: str) -> str | None:
    """获取缓存的概述"""
    return summary_cache.get(paper_title)

def set_cached_summary(paper_title: str, summary: str):
    """设置概述缓存"""
    summary_cache[paper_title] = summary
    save_summary_cache()

# 启动时加载缓存
load_summary_cache()

# ───────────────────────────────────────────────
# 0.1. 工具函数
# ───────────────────────────────────────────────
def clean_html_tags(text: str) -> str:
    """
    将HTML标签转换为更友好的显示格式
    """
    # 替换常见的HTML标签为更友好的格式
    replacements = [
        (r'<sub>(\d+)</sub>', r'_\1'),  # <sub>1</sub> -> _1
        (r'<sup>(\d+)</sup>', r'^\1'),  # <sup>2</sup> -> ^2
        (r'<sub>([^<]+)</sub>', r'_\1'),  # <sub>text</sub> -> _text
        (r'<sup>([^<]+)</sup>', r'^\1'),  # <sup>text</sup> -> ^text
        (r'<[^>]+>', ''),  # 移除其他所有HTML标签
    ]
    
    cleaned_text = text
    for pattern, replacement in replacements:
        cleaned_text = re.sub(pattern, replacement, cleaned_text)
    
    return cleaned_text

# ───────────────────────────────────────────────
# 0.2. 生成概述函数
# ───────────────────────────────────────────────
async def generate_paper_summary(paper_title: str) -> str:
    """
    使用DeepSeek API生成论文的一句话概述
    """
    # 在多个期刊文件夹中查找论文文件
    paper_file = None
    journal_dirs = {
        "jtysgcyxxxb": "./all_txt_jtysgcyxxxb",
        "gljtkj": "./all_txt_gljtkj",
        "jtysyj": "./all_txt_jtysyj"
    }
    
    for journal_code, txt_dir in journal_dirs.items():
        potential_file = Path(txt_dir) / f"{paper_title}.txt"
        if potential_file.exists():
            paper_file = potential_file
            break
    
    if not paper_file or not paper_file.exists():
        raise FileNotFoundError(f"找不到论文文件: {paper_title}.txt")
    
    with open(paper_file, 'r', encoding='utf-8') as f:
        paper_content = f.read()
    
    # 构建提示词
    prompt = f"""请根据以下论文内容，生成一句话概述，帮助用户快速了解论文内容，字数不超过100字。

注意：
1. 请只返回一句话概述，不要包含其他内容
2. 如果涉及数学符号，请使用可读的格式，例如：
   - 使用 C_1, C_2 而不是 C<sub>1</sub>, C<sub>2</sub>
   - 使用 PH(n) 而不是 PH(n)
   - 避免使用HTML标签

论文内容：
{paper_content}

请只返回一句话概述，不要包含其他内容："""
    
    # 调用DeepSeek API
    deepseek_api_key = "sk-409a1e63759a40c89ea285e587e30cc0"
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {deepseek_api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    summary = result["choices"][0]["message"]["content"].strip()
                    # 清理HTML标签
                    cleaned_summary = clean_html_tags(summary)
                    return cleaned_summary
                else:
                    error_text = await response.text()
                    raise Exception(f"DeepSeek API调用失败: {response.status} - {error_text}")
    except Exception as e:
        raise Exception(f"生成概述失败: {str(e)}")

# ───────────────────────────────────────────────
# 0.3. 获取概述函数（优先使用缓存）
# ───────────────────────────────────────────────
async def get_paper_summary(paper_title: str) -> str:
    """
    获取论文概述，优先使用缓存，如果没有则生成并缓存
    """
    # 先检查缓存
    cached_summary = get_cached_summary(paper_title)
    if cached_summary:
        print(f"使用缓存的概述: {paper_title}")
        return cached_summary
    
    # 缓存中没有，生成新的概述
    print(f"生成新的概述: {paper_title}")
    summary = await generate_paper_summary(paper_title)
    
    # 保存到缓存
    set_cached_summary(paper_title, summary)
    
    return summary

# ───────────────────────────────────────────────
# 0.4. 批量预生成概述函数
# ───────────────────────────────────────────────
async def pregenerate_all_summaries():
    """
    批量预生成所有论文的概述
    """
    print("开始批量预生成概述...")
    
    # 获取所有期刊目录
    journal_dirs = {
        "jtysgcyxxxb": "./all_txt_jtysgcyxxxb",
        "gljtkj": "./all_txt_gljtkj",
        "jtysyj": "./all_txt_jtysyj"
    }
    
    all_papers = set()
    for journal_code, txt_dir in journal_dirs.items():
        txt_path = Path(txt_dir)
        if txt_path.exists():
            for txt_file in txt_path.glob("*.txt"):
                paper_title = txt_file.stem  # 去掉.txt后缀
                all_papers.add(paper_title)
    
    print(f"找到 {len(all_papers)} 篇论文")
    
    # 过滤掉已经有缓存的论文
    papers_to_generate = [paper for paper in all_papers if not get_cached_summary(paper)]
    print(f"需要生成概述的论文数量: {len(papers_to_generate)}")
    
    if not papers_to_generate:
        print("所有论文的概述都已生成完成！")
        return
    
    # 批量生成概述
    for i, paper_title in enumerate(papers_to_generate, 1):
        try:
            print(f"正在生成第 {i}/{len(papers_to_generate)} 篇论文概述: {paper_title}")
            summary = await generate_paper_summary(paper_title)
            set_cached_summary(paper_title, summary)
            
            # 每生成10篇保存一次缓存
            if i % 10 == 0:
                save_summary_cache()
                print(f"已保存缓存，进度: {i}/{len(papers_to_generate)}")
                
        except Exception as e:
            print(f"生成概述失败 {paper_title}: {e}")
            continue
    
    # 最终保存缓存
    save_summary_cache()
    print("批量预生成概述完成！")

# ───────────────────────────────────────────────
# 0.5. 流式生成概述函数（保留但不再使用）
# ───────────────────────────────────────────────
async def generate_paper_summary_stream(paper_title: str):
    """
    使用DeepSeek API流式生成论文的一句话概述（已废弃，保留兼容性）
    """
    # 直接返回已缓存的概述
    summary = await get_paper_summary(paper_title)
    yield f"data: {json.dumps({'content': summary}, ensure_ascii=False)}\n\n"
    yield f"data: [DONE]\n\n"

# ───────────────────────────────────────────────
# 1. 结构化日志
# ───────────────────────────────────────────────
logger = logging.getLogger("search_logger")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("search.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)

# ───────────────────────────────────────────────
# 2. FastAPI 应用
# ───────────────────────────────────────────────
app = FastAPI(title="Paper Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 上线后可收紧为 ["https://findpaper.cn"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ───────────────────────────────────────────────
# 3. 自定义静态文件服务: 支持 Brotli/Gzip
# ───────────────────────────────────────────────
class BrStatic(StaticFiles):
    async def get_response(self, path, scope):
        accept = dict(scope['headers']).get(b'accept-encoding', b'').decode()
        full_path = Path(self.directory) / path
        # Brotli 优先
        if 'br' in accept and full_path.with_suffix(full_path.suffix + '.br').is_file():
            return FileResponse(
                full_path.with_suffix(full_path.suffix + '.br'),
                headers={'Content-Encoding': 'br'}
            )
        # 然后 Gzip
        if 'gzip' in accept and full_path.with_suffix(full_path.suffix + '.gz').is_file():
            return FileResponse(
                full_path.with_suffix(full_path.suffix + '.gz'),
                headers={'Content-Encoding': 'gzip'}
            )
        return await super().get_response(path, scope)

# ───────────────────────────────────────────────
# 4. 缓存控制中间件
# ───────────────────────────────────────────────
@app.middleware('http')
async def cache_control(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get('content-type', '')
    if content_type.startswith(('text/javascript', 'text/css')):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response

# ───────────────────────────────────────────────
# 5. PDF 静态目录  →  /pdfs/<file>.pdf
# ───────────────────────────────────────────────
PDF_DIR = Path(os.getenv("PDF_DIR", "papers_pdf_new")).resolve()
PDF_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/pdfs", StaticFiles(directory=str(PDF_DIR)), name="pdfs")

# ───────────────────────────────────────────────
# 6. API 路由（必须在 mount('/') 之前）
# ───────────────────────────────────────────────
@app.get("/api/search")
async def search_api(
    request: Request,
    q: str = Query(..., min_length=1),
    journals: str | None = Query(None, description="期刊代码，多个用逗号分隔，如：jtysgcyxxxb,gljtkj"),
    sid: str | None = Query(None),
):
    """
    GET /api/search?q=xxx&journals=xxx&sid=xxx
    """
    # 解析期刊参数
    selected_journals = None
    if journals:
        selected_journals = [j.strip() for j in journals.split(",") if j.strip()]
    
    # 记录查询日志
    logger.info(
        json.dumps({
            "ts":      datetime.utcnow().isoformat(),
            "sid":     sid,
            "query":   q,
            "journals": selected_journals,
            "ip":      request.client.host,
        }, ensure_ascii=False)
    )
    try:
        results, total, thr = await run_in_threadpool(service.search, q, selected_journals)
        for r in results:
            if raw := r.get("pdf_path"):
                fname = Path(raw).name
                r["pdf_path"] = str(request.url_for("pdfs", path=fname))
        return {"total": total, "threshold": thr, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/journals")
async def get_journals_api():
    """
    GET /api/journals
    获取所有可用的期刊列表
    """
    try:
        journals = await run_in_threadpool(service.get_journals)
        return {"journals": journals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/papers-by-year-issue")
async def papers_by_year_issue_api(
    request: Request,
    year: str = Query(..., description="年份"),
    issue: str = Query(..., description="期数"),
    journal: str | None = Query(None, description="期刊代码"),
    sid: str | None = Query(None),
):
    """
    GET /api/papers-by-year-issue?year=2021&issue=01&journal=jtysgcyxxxb&sid=xxx
    根据年份和期数获取论文列表
    """
    # 记录查询日志
    logger.info(
        json.dumps({
            "ts":      datetime.utcnow().isoformat(),
            "sid":     sid,
            "year":    year,
            "issue":   issue,
            "journal": journal,
            "ip":      request.client.host,
        }, ensure_ascii=False)
    )
    try:
        results = await run_in_threadpool(service.get_papers_by_year_issue, year, issue, journal)
        for r in results:
            if raw := r.get("pdf_path"):
                fname = Path(raw).name
                r["pdf_path"] = str(request.url_for("pdfs", path=fname))
        return {"total": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/log-action")
async def log_action_api(
    request: Request,
    action: str = Form(..., description="动作类型: cite 或 download"),
    paper_title: str = Form(..., description="论文标题"),
    sid: str | None = Form(None),
):
    """
    POST /api/log-action
    记录用户点击行为
    """
    # 记录用户行为日志
    logger.info(
        json.dumps({
            "ts":          datetime.utcnow().isoformat(),
            "sid":         sid,
            "action":      action,
            "paper_title": paper_title,
            "ip":          request.client.host,
        }, ensure_ascii=False)
    )
    return {"status": "success"}

@app.post("/api/generate-summary")
async def generate_summary_api(
    request: Request,
    paper_title: str = Form(..., description="论文标题"),
    sid: str | None = Form(None),
):
    """
    POST /api/generate-summary
    获取论文的一句话概述（优先使用缓存）
    """
    try:
        # 记录用户行为日志
        logger.info(
            json.dumps({
                "ts":          datetime.utcnow().isoformat(),
                "sid":         sid,
                "action":      "get_summary",
                "paper_title": paper_title,
                "ip":          request.client.host,
            }, ensure_ascii=False)
        )
        
        # 调用获取概述的函数（优先使用缓存）
        summary = await get_paper_summary(paper_title)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pregenerate-summaries")
async def pregenerate_summaries_api(
    request: Request,
    sid: str | None = Form(None),
):
    """
    POST /api/pregenerate-summaries
    批量预生成所有论文的概述
    """
    try:
        # 记录用户行为日志
        logger.info(
            json.dumps({
                "ts":      datetime.utcnow().isoformat(),
                "sid":     sid,
                "action":  "pregenerate_summaries",
                "ip":      request.client.host,
            }, ensure_ascii=False)
        )
        
        # 在后台任务中执行批量预生成
        asyncio.create_task(pregenerate_all_summaries())
        
        return {"status": "success", "message": "批量预生成概述任务已启动，请查看控制台输出"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary-cache-status")
async def get_summary_cache_status_api():
    """
    GET /api/summary-cache-status
    获取概述缓存状态
    """
    try:
        total_papers = 0
        journal_dirs = {
            "jtysgcyxxxb": "./all_txt_jtysgcyxxxb",
            "gljtkj": "./all_txt_gljtkj"
        }
        
        for journal_code, txt_dir in journal_dirs.items():
            txt_path = Path(txt_dir)
            if txt_path.exists():
                total_papers += len(list(txt_path.glob("*.txt")))
        
        cached_count = len(summary_cache)
        progress = (cached_count / total_papers * 100) if total_papers > 0 else 0
        
        # 检查缓存文件状态
        pkl_exists = os.path.exists(SUMMARY_CACHE_FILE)
        json_exists = os.path.exists(SUMMARY_CACHE_JSON)
        
        pkl_size = os.path.getsize(SUMMARY_CACHE_FILE) if pkl_exists else 0
        json_size = os.path.getsize(SUMMARY_CACHE_JSON) if json_exists else 0
        
        return {
            "total_papers": total_papers,
            "cached_summaries": cached_count,
            "progress_percentage": round(progress, 2),
            "cache_files": {
                "pkl": {
                    "exists": pkl_exists,
                    "size_kb": round(pkl_size / 1024, 2),
                    "path": SUMMARY_CACHE_FILE
                },
                "json": {
                    "exists": json_exists,
                    "size_kb": round(json_size / 1024, 2),
                    "path": SUMMARY_CACHE_JSON
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary-cache-json")
async def download_summary_cache_json():
    """
    GET /api/summary-cache-json
    下载概述缓存的JSON格式文件
    """
    try:
        if not os.path.exists(SUMMARY_CACHE_JSON):
            raise HTTPException(status_code=404, detail="JSON缓存文件不存在")
        
        # 读取JSON文件内容
        with open(SUMMARY_CACHE_JSON, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 返回JSON文件下载
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={SUMMARY_CACHE_JSON}",
                "Content-Type": "application/json; charset=utf-8"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-summary-stream")
async def generate_summary_stream_api(
    request: Request,
    paper_title: str = Form(..., description="论文标题"),
    sid: str | None = Form(None),
):
    """
    POST /api/generate-summary-stream
    获取论文的一句话概述（兼容流式API，但实际使用缓存）
    """
    try:
        # 记录用户行为日志
        logger.info(
            json.dumps({
                "ts":          datetime.utcnow().isoformat(),
                "sid":         sid,
                "action":      "get_summary_stream",
                "paper_title": paper_title,
                "ip":          request.client.host,
            }, ensure_ascii=False)
        )
        
        # 调用流式生成概述的函数（实际使用缓存）
        return StreamingResponse(content=generate_paper_summary_stream(paper_title), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ───────────────────────────────────────────────
# 7. 前端静态文件  → 根 路径 '/'
#    必须放在所有 API 路由之后！
# ───────────────────────────────────────────────
FRONTEND_DIST = (
    Path(__file__).resolve().parent /
    "frontend" / "dist"
).resolve()

if not FRONTEND_DIST.is_dir():
    raise RuntimeError(
        f"找不到前端构建目录：{FRONTEND_DIST}\n"
        "请在 frontend 目录执行 `npm run build` 后再启动后端。"
    )

app.mount("/", BrStatic(directory=str(FRONTEND_DIST), html=True), name="static_root")
