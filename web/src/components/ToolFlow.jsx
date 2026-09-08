import React, { useEffect, useState } from 'react';
import { Card, Space, Steps, Tag, Typography } from 'antd';
import { TOOL_LABEL, tryParse, lokiRows, promRows, traceRows } from './DetailPanels';

const { Text } = Typography;

// P2-FE-05: 诊断流程图 —— Tool 调用串成步骤条，失败环节红叉突出、点击展开错误详情

/** 结果 JSON → 一句话结论（与证据 Tab 同源的人话化） */
function resultSentence(item) {
  const parsed = tryParse(item.resultSummary);
  if (!parsed || typeof parsed !== 'object') return item.resultSummary || '';
  if (parsed.error) return `错误：${parsed.error}`;
  if (parsed.data?.resultType === 'streams') {
    const rows = lokiRows(parsed);
    const bad = rows.filter((r) => r.level === 'error' || r.level === 'warn').length;
    return rows.length === 0 ? '该时间窗内无日志' : `${rows.length} 条日志${bad ? `（${bad} 条 warn/error）` : ''}`;
  }
  if (parsed.data?.resultType) {
    const rows = promRows(parsed);
    return rows.length === 0 ? '✓ 查询窗口内无数据点（正常）' : `${rows.length} 个数据点`;
  }
  if (Array.isArray(parsed.data)) {
    const rows = traceRows(parsed);
    const errs = rows.filter((r) => r.error).length;
    return rows.length === 0 ? '无匹配链路' : `${rows.length} 个 span${errs ? `（${errs} 个错误）` : ''}`;
  }
  return null;
}

/** 展开的环节详情 */
function StepDetail({ item }) {
  const args = tryParse(item.argumentsJson) || {};
  const failed = item.status !== 'SUCCESS';
  return (
    <Card
      size="small"
      style={{ marginTop: 8, marginBottom: 12, borderColor: failed ? '#FFCCC7' : undefined, background: failed ? '#FFF1F0' : '#FAFAFA' }}
      title={<span style={{ fontSize: 13 }}>{TOOL_LABEL[item.toolName] || item.toolName}{item.durationMs != null ? ` · ${item.durationMs}ms` : ''}</span>}
    >
      {Object.keys(args).length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>参数：</Text>
          {Object.entries(args).map(([k, v]) => <Tag key={k} style={{ marginRight: 4 }}>{k}={String(v)}</Tag>)}
        </div>
      )}
      {failed ? (
        <div>
          <Tag color="red">执行失败</Tag>
          <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: '8px 0 0', color: '#CF1322' }}>
            {item.error || item.resultSummary || '无错误详情'}
          </pre>
        </div>
      ) : (
        <div style={{ fontSize: 13 }}>
          <Text type="secondary">结果：</Text>
          <Text>{resultSentence(item) || '成功'}</Text>
        </div>
      )}
      <details style={{ fontSize: 12, color: '#98A2B3', marginTop: 8 }}>
        <summary style={{ cursor: 'pointer' }}>原始返回</summary>
        <pre style={{ fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: '4px 0 0', maxHeight: 260, overflow: 'auto' }}>
          {item.resultSummary || ''}
        </pre>
      </details>
    </Card>
  );
}

export default function ToolFlow({ toolCalls }) {
  const [active, setActive] = useState(null);

  useEffect(() => {
    // 默认展开第一个失败环节；全成功则展开第一个
    const fail = toolCalls.findIndex((t) => t.status !== 'SUCCESS');
    setActive(toolCalls.length ? (fail >= 0 ? fail : 0) : null);
  }, [toolCalls]);

  if (!toolCalls.length) return <Text type="secondary">暂无 Tool 调用</Text>;

  const items = toolCalls.map((t, i) => {
    const failed = t.status !== 'SUCCESS';
    const sentence = failed ? (t.error ? String(t.error).slice(0, 60) : '执行失败') : resultSentence(t);
    return {
      title: <span style={{ fontWeight: i === active ? 600 : 400 }}>{TOOL_LABEL[t.toolName] || t.toolName}</span>,
      description: (
        <span style={{ fontSize: 12, color: failed ? '#CF1322' : '#98A2B3' }}>
          {sentence}{t.durationMs != null ? ` · ${t.durationMs}ms` : ''}
        </span>
      ),
      status: failed ? 'error' : 'finish',
    };
  });

  return (
    <div>
      <Steps
        direction="vertical"
        size="small"
        current={active}
        items={items}
        onChange={(i) => setActive(i)}
      />
      {active != null && toolCalls[active] && <StepDetail item={toolCalls[active]} />}
    </div>
  );
}
