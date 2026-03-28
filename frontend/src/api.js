import axios from "axios";

// 不再声明 API_URL，让浏览器自己取当前域名
export const searchPapers = async (query, journals) => {
  const resp = await axios.get("/api/search", {
    params: { q: query, journals },
    timeout: 15000,
  });
  return resp.data;
};

// 获取指定年份期数的论文
export const getPapersByYearIssue = async (year, issue, journal = null) => {
  const params = { year, issue };
  if (journal) {
    params.journal = journal;
  }
  const resp = await axios.get("/api/papers-by-year-issue", {
    params,
    timeout: 15000,
  });
  return resp.data;
};

// 记录用户行为日志
// 记录用户行为日志
export function logUserAction(action, paperTitle, sid = null) {
  const data = new URLSearchParams({
    action,
    paper_title: paperTitle,
    ...(sid ? { sid } : {}),
  });

  // sendBeacon 对于 FormData / URLSearchParams 会使用 text/plain，
  // 后端 FastAPI 的 Form() 需要 application/x-www-form-urlencoded。
  // 因此用 Blob 包装一下，手动指定 Content-Type。
  const blob = new Blob([data.toString()], {
    type: "application/x-www-form-urlencoded",
  });
  
  navigator.sendBeacon("/api/log-action", blob);
}

// 生成论文概述
export async function generateSummary(paperTitle) {
  const formData = new FormData();
  formData.append("paper_title", paperTitle);
  
  const response = await fetch("/api/generate-summary", {
    method: "POST",
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error(`生成概述失败: ${response.status}`);
  }
  
  const data = await response.json();
  return data.summary;
}

// 流式生成论文概述
export function generateSummaryStream(paperTitle, onChunk, onComplete, onError) {
  const formData = new FormData();
  formData.append("paper_title", paperTitle);
  
  // 使用fetch发送POST请求，然后手动处理SSE流
  fetch("/api/generate-summary-stream", {
    method: "POST",
    body: formData,
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`生成概述失败: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    function readStream() {
      reader.read().then(({ done, value }) => {
        if (done) {
          onComplete();
          return;
        }
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') {
              onComplete();
              return;
            }
            
            try {
              const data = JSON.parse(dataStr);
              if (data.content) {
                onChunk(data.content);
              } else if (data.error) {
                onError(data.error);
                return;
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
        
        readStream();
      }).catch(error => {
        onError(error.message);
      });
    }
    
    readStream();
  })
  .catch(error => {
    onError(error.message);
  });
}
