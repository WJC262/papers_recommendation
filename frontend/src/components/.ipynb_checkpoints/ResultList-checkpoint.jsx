import React from "react";
import { Card, Button, Progress, Modal, message, Tag, Rate} from "antd";
import { logUserAction } from "../api";

function scoreToStars(score) {
  if (score > 1) return 5;
  if (score > 0.75) return 4;
  if (score > 0.5) return 3;
  if (score > 0.25) return 2;
  if (score > 0) return 1;
  return 0; // 0 或缺省
}

export default function ResultList({ results, total }) {
  const [citeVisible, setCiteVisible] = React.useState(false);
  const [currentCitation, setCurrentCitation] = React.useState("");

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
        共检索到 <b>{total}</b> 篇文档
      </h3>
      {results.map((r, idx) => {
        const fileBase = r.filename.replace(/\.[^/.]+$/, "");
        const paperId = fileBase.replace(/-[^-]{2,3}$/, "");
        const stars    = scoreToStars(r.rank_score);   // ③ 计算星数
        return (
          <Card
            key={paperId}
            style={{ marginBottom: 20 }}
            title={
              <div style={{ display: "flex", alignItems: "center" }}>
                <b>{paperId}</b>
                <Rate
                  disabled
                  value={stars}
                  style={{ marginLeft: 8, fontSize: 16 }}
                />

              </div>
            }
          >
            <div>
              <span style={{ fontWeight: "bold" }}>摘要：</span>
              {r.abstract}
            </div>
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
              >
                引用本文
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
    </div>
  );
}


