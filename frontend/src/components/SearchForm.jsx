import React, { useState, useEffect } from "react";
import { Input, Checkbox, Dropdown, message } from "antd";
import { DownOutlined, ArrowUpOutlined } from "@ant-design/icons";
import YearIssueSelector from "./YearIssueSelector";

const HOT_QUERIES = [];

export default function SearchForm({ onSearch, onError, onYearIssueSelect }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState([]);
  const [journals, setJournals] = useState([]);
  const [loading, setLoading] = useState(true);

  // 获取期刊列表
  useEffect(() => {
    fetchJournals();
  }, []);

  const fetchJournals = async () => {
    try {
      const response = await fetch('/api/journals');
      const data = await response.json();
      if (data.journals && data.journals.length > 0) {
        setJournals(data.journals);
        // 默认只选择交通运输工程与信息学报
        const defaultJournal = data.journals.find(j => j.code === 'jtysgcyxxxb');
        setSelected(defaultJournal ? [defaultJournal.code] : []);
      }
    } catch (error) {
      console.error('获取期刊列表失败:', error);
      message.error('获取期刊列表失败');
    } finally {
      setLoading(false);
    }
  };

  const dropdownItems = (
    <div style={{ padding: 12, width: 220 }}>
      <Checkbox.Group
        options={journals.map(j => ({ label: j.name, value: j.code }))}
        value={selected}
        onChange={setSelected}
      />
    </div>
  );

  const triggerSearch = (q = query) => {
    if (!selected.length) {
      message.warning("请至少选择一个期刊");
      onError("请至少选择一个期刊");
      return;
    }
    
    // 移除对交通运输研究期刊的限制，现在已支持该期刊
    
    // 传递选中的期刊代码列表
    onSearch(q.trim(), selected);
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center" }}>
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
        <div>加载中...</div>
      </div>
    );
  }

  return (
    <div style={{ textAlign: "center", position: "relative" }}>
      {/* 年份期数选择器 - 移到左上角 */}
      <div style={{ 
        position: "absolute", 
        top: 20, 
        left: 20, 
        zIndex: 100 
      }}>
        <YearIssueSelector onSelect={onYearIssueSelect} />
      </div>

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
                options={journals.map(j => ({ label: j.name, value: j.code }))}
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
