import React, { useState } from "react";
import { Layout, Spin, message } from "antd";
import SearchForm from "./components/SearchForm";
import ResultList from "./components/ResultList";
import { searchPapers } from "./api";

const { Footer } = Layout;

export default function App() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState(null);

  const handleSearch = async (query, journal) => {
    setLoading(true);
    setError(null);
    try {
      const data = await searchPapers(query, journal);
      setResults(data.results || []);
      setTotal(data.total || 0);
    } catch (e) {
      // 区分网络错误和空结果
      setError("网络连接失败，请检查网络后重试");
      setResults(null);
      setTotal(0);
    }
    setLoading(false);
  };

  const handleError = (errorMessage) => {
    setError(errorMessage);
    setResults(null);
    setTotal(0);
  };

  // 计算容器 class：有结果则加上 has-result
  const shellClass = `app-shell${results && results.length > 0 ? " has-result" : ""}`;

  return (
    <Layout className={shellClass} style={{ minHeight: results && results.length > 0 ? "auto" : "100vh" }}>
      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 800,
          padding: "0 16px",
          ...(results && results.length > 0 ? {} : {
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center"
          })
        }}
      >
        {/* 转圈覆盖层 */}
        {loading && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: "transparent",
              display: "flex",
              justifyContent: "center",   // 水平方向居中
              alignItems: "flex-start",    // 垂直方向贴顶部
              paddingTop: results && results.length > 0 ? 185 : 570,  // 结果页偏移100px，首页偏移225px
              zIndex: 10,
            }}
          >
            <Spin tip="检索中 …" size="large" />
          </div>
        )}

        {/* 搜索框始终可见 */}
        <SearchForm onSearch={handleSearch} onError={handleError} loading={loading} />

        {/* 结果列表（加载中时依旧在 DOM，只是被蒙层遮住） */}
        {error && (
          <div style={{ marginTop: 40 }}>
            <div style={{ textAlign: "center", margin: "40px 0" }}>
              <img
                src={error.includes("网络连接失败") 
                  ? "https://cdn-icons-png.flaticon.com/512/2748/2748558.png" 
                  : "https://cdn-icons-png.flaticon.com/512/2748/2748558.png"}
                width="100"
                alt=""
              />
              <div style={{ fontSize: 16, color: "#999" }}>
                {error}
              </div>
            </div>
          </div>
        )}
        {results && !error && (
          <div style={{ marginTop: 40 }}>
            <ResultList results={results} total={total} />
          </div>
        )}
      </div>
      
      {/* 备案号 - 只在真正的首页显示（从未搜索过） */}
      {!results && !loading && !error && (
        <Footer style={{ 
          textAlign: "center", 
          padding: "20px 0",
          background: "transparent",
          borderTop: "none",
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 1000
        }}>
          <a 
            href="https://beian.miit.gov.cn/" 
            target="_blank" 
            rel="noopener noreferrer"
            style={{ 
              color: "#999", 
              textDecoration: "none",
              fontSize: "12px"
            }}
          >
            京ICP备2025132697号
          </a>
        </Footer>
      )}
    </Layout>
  );
}
