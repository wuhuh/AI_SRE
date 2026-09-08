import React from 'react';
import { Card, List, Space, Tag, Typography } from 'antd';

// P2-FE-05: 证据/Tool/修复的结构化可视化 —— 把 JSON 翻译成「结论句 + 明细行」，
// 原始 JSON 一律折叠兜底。数据形状见 CP 的 AgentEvidence/ToolCall/RemediationAction。

const { Text, Paragraph } = Typography;

function tryParse(str) {
  if (typeof str !== 'string') return str ?? null;
  try { return JSON.parse(str); } catch { return null; }
}

/** Loki streams 结果 → [{level, container, line}] */
function lokiRows(parsed) {
  const streams = parsed?.data?.result || [];
  const rows = [];
  for (const st of streams) {
    const labels = st.stream || {};
    for (const [ts, line] of st.values || []) {
      rows.push({ level: labels.level || 'info', container: labels.container || labels.job || '', ts, line });
    }
  }
  return rows;
}

/** Prometheus vector/matrix → [{labels, value}] */
function promRows(parsed) {
  const result = parsed?.data?.result || [];
  return result.map((r) => {
    const labels = r.metric || {};
    const v = r.value?.[1] ?? r.values?.slice(-1)[0]?.[1] ?? '';
    return { labels, value: v };
  });
}

/** Jaeger traces → [{service, operation, durationMs, error}] */
function traceRows(parsed) {
  const out = [];
  for (const tr of parsed?.data || []) {
    for (const sp of tr.spans || []) {
      const svc = (sp.process?.serviceName) || '';
      out.push({
        service: svc,
        operation: sp.operationName,
        durationMs: sp.duration ? Math.round(sp.duration / 1000) : null, // jaeger duration 是微秒
        error: (sp.tags || []).some((t) => t.key === 'error' && t.value),
      });
    }
  }
  return out;
}

const LEVEL_COLOR = { error: 'red', warn: 'orange', info: 'blue', debug: 'default' };

/** 人话结论句 */
function EvidenceSummary({ source, parsed }) {
  if (source === 'query_prometheus') {
    const rows = promRows(parsed);
    return rows.length === 0
      ? <Text type="success">✓ 查询窗口内无数据点（错误率/延迟类查询 = 该窗口正常）</Text>
      : <Text>共 {rows.length} 个数据点</Text>;
  }
  if (source === 'query_logs') {
    const rows = lokiRows(parsed);
    const bad = rows.filter((r) => r.level === 'error' || r.level === 'warn').length;
    return rows.length === 0
      ? <Text type="secondary">该时间窗内无日志</Text>
      : <Text>共 {rows.length} 条日志{bad > 0 ? <Tag color="orange" style={{ marginLeft: 8 }}>{bad} 条 warn/error</Tag> : null}</Text>;
  }
  if (source === 'query_trace') {
    const rows = traceRows(parsed);
    const errs = rows.filter((r) => r.error).length;
    return rows.length === 0
      ? <Text type="secondary">无匹配链路</Text>
      : <Text>{rows.length} 个 span{errs > 0 ? <Tag color="red" style={{ marginLeft: 8 }}>{errs} 个错误 span</Tag> : null}</Text>;
  }
  return null;
}

function EvidenceBody({ source, parsed }) {
  if (source === 'query_prometheus') {
    const rows = promRows(parsed);
    if (rows.length === 0) return null;
    return (
      <div style={{ marginTop: 4 }}>
        {rows.slice(0, 8).map((r, i) => (
          <div key={i} style={{ fontSize: 12, fontFamily: 'monospace' }}>
            {Object.entries(r.labels).map(([k, v]) => `${k}=${v}`).join(' ')} = <Text strong>{r.value}</Text>
          </div>
        ))}
        {rows.length > 8 && <Text type="secondary" style={{ fontSize: 12 }}>…共 {rows.length} 条</Text>}
      </div>
    );
  }
  if (source === 'query_logs') {
    const rows = lokiRows(parsed);
    if (rows.length === 0) return null;
    return (
      <div style={{ marginTop: 4 }}>
        {rows.slice(0, 6).map((r, i) => (
          <div key={i} style={{ fontSize: 12, fontFamily: 'monospace', display: 'flex', gap: 8 }}>
            <Tag color={LEVEL_COLOR[r.level] || 'default'} style={{ marginRight: 0 }}>{r.level}</Tag>
            <Text style={{ fontSize: 12 }} ellipsis={{ tooltip: r.line }}>{r.container}: {r.line}</Text>
          </div>
        ))}
        {rows.length > 6 && <Text type="secondary" style={{ fontSize: 12 }}>…共 {rows.length} 条</Text>}
      </div>
    );
  }
  if (source === 'query_trace') {
    const rows = traceRows(parsed);
    if (rows.length === 0) return null;
    return (
      <div style={{ marginTop: 4 }}>
        {rows.slice(0, 8).map((r, i) => (
          <div key={i} style={{ fontSize: 12, fontFamily: 'monospace', display: 'flex', gap: 8 }}>
            <Tag color={r.error ? 'red' : 'default'} style={{ marginRight: 0 }}>{r.error ? 'ERROR' : 'span'}</Tag>
            <span>{r.service}: {r.operation}{r.durationMs != null ? ` (${r.durationMs}ms)` : ''}</span>
          </div>
        ))}
        {rows.length > 8 && <Text type="secondary" style={{ fontSize: 12 }}>…共 {rows.length} 个 span</Text>}
      </div>
    );
  }
  return null;
}

/** 通用兜底：一层键值表 */
function KVFallback({ parsed }) {
  if (!parsed || typeof parsed !== 'object') return null;
  const entries = Object.entries(parsed).filter(([, v]) => typeof v !== 'object');
  if (entries.length === 0) return null;
  return (
    <div style={{ marginTop: 4 }}>
      {entries.slice(0, 6).map(([k, v]) => (
        <div key={k} style={{ fontSize: 12 }}>
          <Text type="secondary">{k}: </Text><Text strong>{String(v)}</Text>
        </div>
      ))}
    </div>
  );
}

/** 单条证据：结论句 + 明细 + 折叠原文 */
export function EvidenceItem({ item }) {
  const parsed = tryParse(item.content);
  const hasStructured = parsed && typeof parsed === 'object';
  return (
    <List.Item>
      <Space direction="vertical" size={2} style={{ width: '100%' }}>
        <Space>
          <Tag color="blue">{item.source}</Tag>
          <EvidenceSummary source={item.source} parsed={parsed} />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {item.collectedAt ? new Date(item.collectedAt).toLocaleTimeString() : ''}
          </Text>
        </Space>
        <EvidenceBody source={item.source} parsed={parsed} />
        {!hasStructured && item.content && (
          <Paragraph style={{ marginBottom: 0, fontSize: 12 }} ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}>
            {String(item.content)}
          </Paragraph>
        )}
        <details style={{ fontSize: 12, color: '#98A2B3' }}>
          <summary style={{ cursor: 'pointer' }}>原始 JSON</summary>
          <pre style={{ fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: '4px 0 0' }}>
            {typeof item.content === 'string' ? item.content : JSON.stringify(item.content, null, 2)}
          </pre>
        </details>
      </Space>
    </List.Item>
  );
}

const TOOL_LABEL = {
  query_prometheus: '查询 Prometheus 指标',
  query_logs: '查询 Loki 日志',
  query_trace: '查询 Jaeger 链路',
  retrieve_runbook: '检索 Runbook',
  list_pods: '列出 Pod',
  restart_pod: '重启 Pod',
  scale_deployment: '伸缩 Deployment',
  redis_info: '查询 Redis 信息',
  db_slow_query: '查询慢 SQL',
};

/** Tool 调用卡片 */
export function ToolCallItem({ item }) {
  const args = tryParse(item.argumentsJson) || {};
  const result = tryParse(item.resultSummary);
  return (
    <List.Item>
      <Space direction="vertical" size={2} style={{ width: '100%' }}>
        <Space>
          <Tag color={item.status === 'SUCCESS' ? 'green' : item.status === 'FAILED' ? 'red' : 'orange'}>{item.status}</Tag>
          <Text strong>{TOOL_LABEL[item.toolName] || item.toolName}</Text>
          <Tag>{item.riskLevel}</Tag>
        </Space>
        {Object.keys(args).length > 0 && (
          <div style={{ fontSize: 12 }}>
            <Text type="secondary">参数：</Text>
            {Object.entries(args).map(([k, v]) => (
              <Tag key={k} style={{ marginRight: 4 }}>{k}={String(v)}</Tag>
            ))}
          </div>
        )}
        {result && (
          <div style={{ fontSize: 12 }}>
            <Text type="secondary">返回：</Text>
            <Text>{result.status ? `${result.status} · ` : ''}{result.data?.result?.length != null ? `${result.data.result.length} 条结果` : ''}</Text>
          </div>
        )}
        <details style={{ fontSize: 12, color: '#98A2B3' }}>
          <summary style={{ cursor: 'pointer' }}>原始返回</summary>
          <pre style={{ fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: '4px 0 0' }}>
            {item.resultSummary || ''}
          </pre>
        </details>
      </Space>
    </List.Item>
  );
}

/** 修复记录卡片 */
export function RemediationItem({ item }) {
  const args = tryParse(item.argumentsJson) || {};
  const result = tryParse(item.resultSummary) || {};
  const executed = result.dryRun === true ? 'DRY-RUN（演练，未真实执行）' : result.executed === false ? '未执行' : '已执行';
  return (
    <List.Item>
      <Space direction="vertical" size={2} style={{ width: '100%' }}>
        <Space>
          <Tag color={item.status === 'SUCCESS' ? 'green' : item.status === 'FAILED' ? 'red' : 'orange'}>{item.status}</Tag>
          <Text strong>{TOOL_LABEL[item.toolName] || item.toolName}</Text>
          <Tag color={result.dryRun ? 'gold' : 'cyan'}>{executed}</Tag>
          {item.approvalId && <Text type="secondary" style={{ fontSize: 12 }}>审批 #{item.approvalId}</Text>}
        </Space>
        {Object.keys(args).length > 0 && (
          <div style={{ fontSize: 12 }}>
            <Text type="secondary">动作参数：</Text>
            {Object.entries(args).map(([k, v]) => (
              <Tag key={k} style={{ marginRight: 4 }}>{k}={String(v)}</Tag>
            ))}
          </div>
        )}
        {item.resultSummary && (
          <details style={{ fontSize: 12, color: '#98A2B3' }}>
            <summary style={{ cursor: 'pointer' }}>执行详情</summary>
            <pre style={{ fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: '4px 0 0' }}>
              {item.resultSummary}
            </pre>
          </details>
        )}
      </Space>
    </List.Item>
  );
}
