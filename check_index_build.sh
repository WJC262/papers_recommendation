#!/bin/bash
echo "=== 索引构建进度检查 ==="
echo ""

# 1. 检查索引目录是否存在
if [ -d "faiss_index_9_6" ]; then
    echo "✅ 索引目录已生成"
    ls -lh faiss_index_9_6/ | tail -3
    echo ""
    echo "索引文件大小:"
    du -sh faiss_index_9_6/
else
    echo "⏳ 索引目录尚未生成，正在构建中..."
fi

echo ""

# 2. 检查进程状态
PID=$(ps aux | grep "[u]vicorn api:app" | awk '{print $2}' | head -1)
if [ -n "$PID" ]; then
    echo "✅ 服务进程运行中 (PID: $PID)"
    ps -p $PID -o %cpu,%mem,etime 2>/dev/null | tail -1
else
    echo "❌ 服务进程未运行"
fi

echo ""

# 3. 检查日志文件
if [ -f "api.log" ]; then
    echo "📄 日志文件大小: $(wc -l < api.log) 行"
    echo "最后的关键信息:"
    tail -20 api.log | grep -E ">>>|加载了|构建|索引|FAISS|论文" || echo "   (暂无构建信息输出)"
fi

echo ""

# 4. 测试API
echo "🔍 测试API响应:"
curl -s http://localhost:8000/api/journals > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ API已就绪，可以接受请求"
else
    echo "⏳ API尚未就绪，可能仍在构建索引"
fi
