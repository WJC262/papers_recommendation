import React, { useState } from "react";
import { Button } from "antd";

/** 数据结构：使用实际可用的年份期数 */
const DATA_JTYSGCYXXXB = {
  2026: ["01"],
  2025: ["01", "02", "03", "04"],
  2024: ["01", "02", "03", "04"],
  2023: ["01", "02", "03", "04"],
  2022: ["01", "02", "03", "04"],
  2021: ["01", "02", "03", "04"],
  2020: ["01", "02", "03", "04"],
  2019: ["01", "02", "03", "04"],
  2018: ["01", "02", "03", "04"],
};

const DATA_GLJTKJ = {
  2025: ["01", "02", "03", "04", "05", "06"],
};

const DATA_JTYSYJ = {
  2025: ["01", "02", "03"],
};

const JOURNALS = [
  { code: "jtysgcyxxxb", name: "交通运输工程与信息学报" },
  { code: "gljtkj", name: "公路交通科技" },
  { code: "jtysyj", name: "交通运输研究" },
];

export default function YearIssueSelector({ onSelect }) {
  const [isHovered, setIsHovered] = useState(false);
  const [hoveredYear, setHoveredYear] = useState(null);
  const [selectedJournal, setSelectedJournal] = useState(null);

  const chooseIssue = (journalCode, year, issue) => {
    onSelect(year, issue, journalCode);
    setIsHovered(false);
    setHoveredYear(null);
    setSelectedJournal(null);
  };

  if (isHovered) {
    return (
      <div style={{ position: "fixed", top: 20, left: 20, zIndex: 1000 }}>
        {/* 主按钮 */}
        <Button
          size="middle"
          style={{
            backgroundColor: "#ffffff",
            borderColor: "#d9d9d9",
            color: "#333",
            fontSize: 14,
            padding: "6px 12px",
            height: "auto",
            lineHeight: 1.4,
          }}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          全部论文
        </Button>

        {/* 弹出的菜单 */}
        <div
          style={{
            position: "absolute",
            left: "100%",
            top: 0,
            zIndex: 1000,
            backgroundColor: "#fff",
            border: "1px solid #d9d9d9",
            borderRadius: 4,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            padding: "4px 0",
            width: "fit-content",
          }}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >


          {/* 期刊列表 */}
          {JOURNALS.map((journal) => (
            <div
              key={journal.code}
              style={{ position: "relative", display: "block" }}
              onMouseEnter={() => setSelectedJournal(journal.code)}
              onMouseLeave={() => setSelectedJournal(null)}
            >
              <div
                style={{
                  padding: "6px 6px",
                  fontSize: 13,
                  cursor: "pointer",
                  backgroundColor:
                    selectedJournal === journal.code ? "#f5f5f5" : "transparent",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  whiteSpace: "nowrap",
                  minWidth: 140,
                }}
              >
                <span>{journal.name}</span>
                <span style={{ fontSize: 11, color: "#999", marginLeft: 4 }}>▶</span>
              </div>

              {/* 年份列（去箭头 + 更窄） */}
              {selectedJournal === journal.code && (
                <div
                  style={{
                    position: "absolute",
                    left: "100%",
                    top: 0,
                    zIndex: 1000,
                    backgroundColor: "#fff",
                    border: "1px solid #d9d9d9",
                    borderRadius: 4,
                    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                    minWidth: 45, // 更窄
                  }}
                  onMouseEnter={() => setSelectedJournal(journal.code)}
                  onMouseLeave={() => setSelectedJournal(null)}
                >
                  {Object.keys(
                    selectedJournal === "gljtkj" ? DATA_GLJTKJ : 
                    selectedJournal === "jtysgcyxxxb" ? DATA_JTYSGCYXXXB : DATA_JTYSYJ
                  )
                    .sort((a, b) => b - a)
                    .map((yearValue) => (
                      <div
                        key={yearValue}
                        style={{ position: "relative", display: "block" }}
                        onMouseEnter={() => setHoveredYear(yearValue)}
                        onMouseLeave={() => setHoveredYear(null)}
                      >
                        <div
                          style={{
                            padding: "6px 8px",
                            fontSize: 13,
                            cursor: "pointer",
                            backgroundColor:
                              hoveredYear === yearValue ? "#f5f5f5" : "transparent",
                            textAlign: "center",
                            whiteSpace: "nowrap",
                            minWidth: 45, // 更窄
                          }}
                        >
                          {yearValue}
                        </div>

                        {/* 期数列（同样窄、可点击） */}
                        {hoveredYear === yearValue && (
                          <div
                            style={{
                              position: "absolute",
                              left: "100%",
                              top: 0,
                              zIndex: 1000,
                              backgroundColor: "#fff",
                              border: "1px solid #d9d9d9",
                              borderRadius: 4,
                              boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                              minWidth: 45,
                            }}
                            onMouseEnter={() => setHoveredYear(yearValue)}
                            onMouseLeave={() => setHoveredYear(null)}
                          >
                            {(
                              selectedJournal === "gljtkj"
                                ? DATA_GLJTKJ
                                : selectedJournal === "jtysgcyxxxb"
                                ? DATA_JTYSGCYXXXB
                                : DATA_JTYSYJ
                            )[yearValue]?.map((issueValue) => (
                              <div
                                key={issueValue}
                                style={{
                                  padding: "6px 8px",
                                  fontSize: 13,
                                  cursor: "pointer",
                                  borderBottom: "1px solid #f0f0f0",
                                  textAlign: "center",
                                }}
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.backgroundColor = "#f5f5f5";
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.backgroundColor = "transparent";
                                }}
                                onClick={() =>
                                  chooseIssue(journal.code, yearValue, issueValue)
                                }
                              >
                                {issueValue}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 初始状态：仅按钮
  return (
    <div style={{ position: "fixed", top: 20, left: 20, zIndex: 1000 }}>
      <Button
        size="middle"
        style={{
          backgroundColor: "#ffffff",
          borderColor: "#d9d9d9",
          color: "#333",
          fontSize: 14,
          padding: "6px 12px",
          height: "auto",
          lineHeight: 1.4,
        }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        全部论文
      </Button>
    </div>
  );
} 
