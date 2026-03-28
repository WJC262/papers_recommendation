// import axios from "axios";

// // const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
// const API_URL = "https://findpaper.cn";
// //fetch(`/api/search?q=${kw}`);

// export const searchPapers = async (query, journal) => {
//   const resp = await axios.get(`${API_URL}/api/search`, {
//     params: { q: query, journal },
//     timeout: 8000000,
//   });
//   return resp.data;
// };


import axios from "axios";

// 不再声明 API_URL，让浏览器自己取当前域名
export const searchPapers = async (query, journal) => {
  const resp = await axios.get("/api/search", {
    params: { q: query, journal },
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

