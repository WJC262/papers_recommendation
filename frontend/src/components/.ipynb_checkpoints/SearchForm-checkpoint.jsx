import React, { useState } from "react";
import { Input, Checkbox, Dropdown, message } from "antd";
import { DownOutlined, ArrowUpOutlined } from "@ant-design/icons";

const ALL_JOURNALS = [
  "交通运输工程与信息学报",
  "交通运输研究",
  "公路交通科技",
];
const SUPPORTED_JOURNALS = ["交通运输工程与信息学报"];
const HOT_QUERIES = [];

export default function SearchForm({ onSearch, onError }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(["交通运输工程与信息学报"]);

  const dropdownItems = (
    <div style={{ padding: 12, width: 220 }}>
      <Checkbox.Group
        options={ALL_JOURNALS}
        value={selected}
        onChange={setSelected}
      />
    </div>
  );

  const triggerSearch = (q = query) => {
    if (!selected.length) {
      message.warning("请至少选择一个期刊");
      return;
    }
    
    // 检查是否包含"交通运输工程与信息学报"
    const hasSupportedJournal = selected.includes("交通运输工程与信息学报");
    if (!hasSupportedJournal) {
      onError("暂无该期刊数据，请选择包含'交通运输工程与信息学报'的期刊");
      return;
    }
    
    onSearch(q.trim(), selected[0]);
  };

  return (
    <div style={{ textAlign: "center" }}>
      {/* 标题 */}
      <h1
        style={{
          fontFamily: '"Source Han Sans SC", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", "sans-serif"',
          fontSize: 40,
          fontWeight: 700,
          color: '#333',
          marginBottom: 16,
          letterSpacing: 1,
        }}
      >
        AI 智慧检索
      </h1>

      {/* 搜索框 + 按钮 */}
      <div className="input-box" style={{ marginBottom: 8 }}>
        <Input
          bordered={false}
          placeholder="搜索关键词或完整句子"
          size="large"
          style={{ flex: 1, paddingTop: 0, paddingBottom: 30 }}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onPressEnter={() => triggerSearch()}
        />

        <Dropdown
          trigger={['click']}
          placement="bottomCenter"
          dropdownRender={() => (
            <div className="journal-dropdown">
              <Checkbox.Group
                options={ALL_JOURNALS}
                value={selected}
                onChange={setSelected}
                style={{ display: 'flex', flexDirection: 'column', rowGap: 8 }}
              />
            </div>
          )}
          arrow={{ pointAtCenter: true }}
        >
          <div className="selector-btn">
            期刊 <DownOutlined />
          </div>
        </Dropdown>

        <div className="square-btn" title="检索" onClick={() => triggerSearch()}>
          <ArrowUpOutlined />
        </div>
      </div>


    </div>
  );
}


