import React from "react";
import { Card, Button, Progress, Modal, message, Tag, Rate, Spin } from "antd";
import { logUserAction, generateSummary, generateSummaryStream } from "../api";

function scoreToStars(score) {
  if (score > 0.9) return 5;
  if (score > 0.75) return 4;
  if (score > 0.5) return 3;
  if (score > 0.25) return 2;
  if (score > 0) return 1;
  return 0; // 0 或缺省
}

export default function ResultList({ results, total, isYearIssueSearch }) {
  const [citeVisible, setCiteVisible] = React.useState(false);
  const [currentCitation, setCurrentCitation] = React.useState("");
  const [summaryVisible, setSummaryVisible] = React.useState(false);
  const [currentSummary, setCurrentSummary] = React.useState("");
  const [loadingPapers, setLoadingPapers] = React.useState(new Set());
  const [streamingSummary, setStreamingSummary] = React.useState("");
  const [isStreaming, setIsStreaming] = React.useState(false);

  const handleShowCitation = (citation) => {
    if (!citation) {
      message.warning("抱歉，该论文暂无引文信息");
      return;
    }
    setCurrentCitation(citation);
    setCiteVisible(true);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(currentCitation);
      message.success("已复制到剪贴板！");
    } catch {
      message.error("复制失败");
    }
  };

  const handleGenerateSummary = async (paperTitle) => {
    // 设置当前论文为加载状态
    setLoadingPapers(prev => new Set([...prev, paperTitle]));
    
    try {
      const summary = await generateSummary(paperTitle);
      setCurrentSummary(summary);
      setSummaryVisible(true);
      logUserAction("generate_summary", paperTitle);
    } catch (error) {
      message.error("生成概述失败，请稍后重试");
      console.error("生成概述错误:", error);
    } finally {
      // 移除当前论文的加载状态
      setLoadingPapers(prev => {
        const newSet = new Set(prev);
        newSet.delete(paperTitle);
        return newSet;
      });
    }
  };

  const handleGenerateSummaryStream = (paperTitle) => {
    // 设置当前论文为加载状态
    setLoadingPapers(prev => new Set([...prev, paperTitle]));
    setIsStreaming(true);
    setStreamingSummary("");
    setSummaryVisible(true);
    
    // 记录用户行为
    logUserAction("generate_summary_stream", paperTitle);
    
    let finalText = "";
    
    generateSummaryStream(
      paperTitle,
      // onChunk - 接收到新的文本块
      (chunk) => {
        finalText += chunk;
        setStreamingSummary(finalText);
      },
      // onComplete - 生成完成
      () => {
        setCurrentSummary(finalText);
        setIsStreaming(false);
        setLoadingPapers(prev => {
          const newSet = new Set(prev);
          newSet.delete(paperTitle);
          return newSet;
        });
      },
      // onError - 发生错误
      (error) => {
        message.error("生成概述失败，请稍后重试");
        console.error("生成概述错误:", error);
        setIsStreaming(false);
        setSummaryVisible(false);
        setLoadingPapers(prev => {
          const newSet = new Set(prev);
          newSet.delete(paperTitle);
          return newSet;
        });
      }
    );
  };

  const handleCopySummary = async () => {
    try {
      const textToCopy = isStreaming ? streamingSummary : currentSummary;
      await navigator.clipboard.writeText(textToCopy);
      message.success("已复制到剪贴板！");
    } catch {
      message.error("复制失败");
    }
  };

  if (!results) return null;
  if (results.length === 0)
    return (
      <div style={{ textAlign: "center", margin: "40px 0" }}>
        <img
          src="https://cdn-icons-png.flaticon.com/512/2748/2748558.png"
          width="100"
          alt=""
        />
        <div style={{ fontSize: 16, color: "#999" }}>
          没有找到相关结果，建议尝试其他关键词。
        </div>
      </div>
    );

  return (
    <div>
      <h3>
        {isYearIssueSearch ? (
          <>按期检索到 <b>{total}</b> 篇文档</>
        ) : (
          <>共检索到 <b>{total}</b> 篇文档</>
        )}
      </h3>
      {results.map((r, idx) => {
        const fileBase = r.filename.replace(/\.[^/.]+$/, "");
        const paperId = fileBase.replace(/-[^-]{2,3}$/, "");
        // 去掉开头的"11"前缀
        const displayTitle = paperId.replace(/^11/, "");
        const stars    = scoreToStars(r.rank_score);   // ③ 计算星数
        const isThisPaperLoading = loadingPapers.has(paperId);
        return (
          <Card
            key={paperId}
            style={{ marginBottom: 20 }}
            title={
              <div style={{ display: "flex", alignItems: "center" }}>
                <b>{displayTitle}</b>
                {!isYearIssueSearch && (
                  <Rate
                    disabled
                    value={stars}
                    style={{ marginLeft: 8, fontSize: 16 }}
                  />
                )}
                {isYearIssueSearch && r.journal_name && (
                  <Tag color="blue" style={{ marginLeft: 8 }}>
                    {r.journal_name}
                  </Tag>
                )}
              </div>
            }
          >
            <div>
              <span style={{ fontWeight: "bold" }}>摘要：</span>
              {r.abstract}
            </div>
            {r.year && (
              <div style={{ margin: "5px 0" }}>
                <span style={{ fontWeight: "bold" }}>论文年份：</span>
                {r.year}
              </div>
            )}
            {r.author && (
              <div style={{ margin: "5px 0" }}>
                <span style={{ fontWeight: "bold" }}>作者：</span>
                {r.author}
              </div>
            )}
            {!isYearIssueSearch && (
              <div style={{ margin: "10px 0" }}>
                <div style={{ display: "inline-block", width: 200, marginRight: 24 }}>
                  <span>字面匹配度：</span>
                  <Progress percent={Math.round(r.bm25 * 100)} size="small" />
                </div>
                <div style={{ display: "inline-block", width: 200 }}>
                  <span>语义相似度:</span>
                  <Progress percent={Math.round(r.vec * 100)} size="small" />
                </div>
              </div>
            )}
            <div style={{ marginTop: 10 }}>
              {r.pdf_path ? (
                <Button
                  type="primary"
                  href={r.pdf_path}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ marginRight: 8 }}
                  onClick={() => logUserAction("download", paperId)}
                >
                  下载PDF
                </Button>
              ) : (
                <span style={{ color: "#aaa" }}>暂无 PDF</span>
              )}
              <Button
                type="dashed"
                onClick={() => {
                  logUserAction("cite", paperId);
                  handleShowCitation(r.citation);
                }}
                style={{ marginRight: 8 }}
              >
                引用本文
              </Button>
              <Button
                type="dashed"
                loading={isThisPaperLoading}
                onClick={() => handleGenerateSummaryStream(paperId)}
              >
                一句话概述
              </Button>
            </div>
          </Card>
        );
      })}
    <Modal
      title="引用格式"
      open={citeVisible}
      onCancel={() => setCiteVisible(false)}
      footer={[
        <Button key="copy" type="primary" onClick={handleCopy}>
          复制
        </Button>,
      ]}
    >
      <pre
        style={{
          /* 保留换行同时允许自动折行 */
          whiteSpace: "pre-wrap",
          /* 英文单词／长串无空格时也强制折行 */
          wordBreak: "break-all",
          margin: 0,
          lineHeight: 1.6,
        }}
      >
        {currentCitation}
      </pre>
    </Modal>
    <Modal
      title={
        <span>
          <span role="img" aria-label="summary" style={{ marginRight: 8 }}>🧠</span>
          一句话概述
        </span>
      }
      open={summaryVisible}
      onCancel={() => {
        setSummaryVisible(false);
        setIsStreaming(false);
        setStreamingSummary("");
      }}
      footer={[
        <Button key="copy" type="primary" onClick={handleCopySummary}>
          复制
        </Button>,
      ]}
    >
      <div
        style={{
          margin: 0,
          lineHeight: 1.6,
          fontSize: "14px",
          minHeight: "60px",
          textAlign: "left",
        }}
      >
        {isStreaming ? (
          streamingSummary ? (
            <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {streamingSummary}
              <span 
                style={{ 
                  animation: "blink 1s infinite",
                  marginLeft: "2px"
                }}
              >
                |
              </span>
            </div>
          ) : (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60px" }}>
              <Spin size="large" tip="正在生成概述..." />
            </div>
          )
        ) : (
          <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {currentSummary}
          </div>
        )}
      </div>
      <style>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </Modal>
    </div>
  );
}
