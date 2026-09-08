import React, { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  Layout,
  List,
  Modal,
  Select,
  DatePicker,
  Row,
  Space,
  Tabs,
  Tag,
  Timeline,
  Typography,
} from 'antd';
import { LoginOutlined, ReloadOutlined } from '@ant-design/icons';
import MetricCard from './components/MetricCard';
import SystemStatus from './components/SystemStatus';
import ServiceHealthPanel from './components/ServiceHealthPanel';
import IncidentOverview from './components/IncidentOverview';
import IncidentTable from './components/IncidentTable';
import { formatRootCause } from './theme';

const { Header, Content } = Layout;

// P3-FE-04: API base 注入点 —— 默认同源（nginx/vite 代理），构建期可用
// VITE_API_BASE 注入其它后端地址（如直连 CP :8080）
const API_BASE = import.meta.env.VITE_API_BASE || '';

export default function App() {
  const [incidents, setIncidents] = useState([]);
  const [services, setServices] = useState([]);
  const [selected, setSelected] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('aisre_token') || '');
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginUser, setLoginUser] = useState('');
  const [loginPass, setLoginPass] = useState('');
  // P2-FE-05: 列表筛选（状态/服务搜索/日期范围）
  const [fStatus, setFStatus] = useState('ALL');
  const [fSearch, setFSearch] = useState('');
  const [fRange, setFRange] = useState(null);
  const detailRef = React.useRef(null);
  const [evidence, setEvidence] = useState([]);
  const [toolCalls, setToolCalls] = useState([]);
  const [remediations, setRemediations] = useState([]);
  const [steps, setSteps] = useState([]);
  const [loading, setLoading] = useState(false);
  // P2-FE-03: 统一错误态（React 此前无 error 展示）
  const [error, setError] = useState('');

  // P2-FE-03: 统一 fetch —— 401 清 token 提示重登，非 2xx 抛错由调用方提示
  // P3-FE-04: 相对路径统一挂 API_BASE
  const apiFetch = async (url, opts = {}) => {
    const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
    const res = await fetch(fullUrl, { ...opts, headers: { ...authHeaders(), ...(opts.headers || {}) } });
    if (res.status === 401) {
      setAuthToken('');
      localStorage.removeItem('aisre_token');
      setError('登录已过期或未登录，请重新登录');
      throw new Error('401');
    }
    return res;
  };

  const load = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/incidents');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      setIncidents(await res.json());
      setError('');
    } catch (e) {
      if (String(e.message) !== '401') setError('加载事故列表失败：' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadServices = async () => {
    const res = await apiFetch('/api/v1/dashboard/services');
    if (res.ok) {
      setServices(await res.json());
    }
  };

  const login = async (username, password) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (res.ok && data.token) {
      setAuthToken(data.token);
      localStorage.setItem('aisre_token', data.token);
      setError(''); // 登录前轮询 401 留下的提示条要清掉，否则误导「仍未登录」
      setLoginOpen(false);
      load();           // 登录前那轮 401 已把列表打空——立即重拉（SSE 无新事件不会自动刷）
      loadServices();
      window.alert('登录成功');
    } else {
      window.alert(data.message || '登录失败');
    }
  };

  const logout = () => {
    setAuthToken('');
    localStorage.removeItem('aisre_token');
  };

  // token 以 localStorage 为 SSOT：轮询定时器/SSE 回调持有的是初始渲染闭包，
  // 读 state 会拿到登录前的空值 → 401 → 误清刚存的 token（死循环「未登录」）
  const authHeaders = () => {
    const t = localStorage.getItem('aisre_token') || authToken;
    return t ? { Authorization: `Bearer ${t}` } : {};
  };

  const loadApprovals = async (id) => {
    if (!id) return;
    const res = await apiFetch(`/api/v1/approvals/incident/${id}`);
    if (res.ok) {
      setApprovals(await res.json());
    }
  };

  // P2-FE-05: allSettled —— 单个子资源失败（如权限/网络）不再拖死其它 Tab
  const loadDetails = async (id) => {
    if (!id) return;
    const [ev, tc, rm, st] = await Promise.allSettled([
      apiFetch(`/api/v1/incidents/${id}/evidence`),
      apiFetch(`/api/v1/incidents/${id}/tool-calls`),
      apiFetch(`/api/v1/incidents/${id}/remediations`),
      apiFetch(`/api/v1/incidents/${id}/steps`),
    ]);
    const pick = async (r, setter) => {
      if (r.status === 'fulfilled' && r.value.ok) setter(await r.value.json());
      else setter([]);
    };
    await Promise.all([pick(ev, setEvidence), pick(tc, setToolCalls), pick(rm, setRemediations), pick(st, setSteps)]);
  };

  useEffect(() => {
    load();
    loadServices();
    // P2-FE-03: SSE 断线自动重连（指数退避，封顶 10s）；卸载时彻底清理
    let es = null;
    let retryTimer = null;
    let attempt = 0;
    let disposed = false;
    const connect = () => {
      if (disposed) return;
      es = new EventSource(`${API_BASE}/api/v1/stream/incidents`);
      es.onmessage = () => load();
      es.onopen = () => { attempt = 0; };
      es.onerror = () => {
        if (es) es.close();
        attempt += 1;
        retryTimer = setTimeout(connect, Math.min(1000 * 2 ** attempt, 10000));
      };
    };
    connect();
    const timer = setInterval(loadServices, 10000);
    return () => {
      disposed = true;
      if (es) es.close();
      if (retryTimer) clearTimeout(retryTimer);
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (selected) {
      setEvidence([]); setToolCalls([]); setRemediations([]); setSteps([]); setApprovals([]);
      loadApprovals(selected.id);
      loadDetails(selected.id);
      // 点击行后自动滚到详情卡（之前要手动滚到页底找）
      setTimeout(() => detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }
  }, [selected]);

  const decision = async (id, decisionType) => {
    if (!authToken) {
      window.alert('请先登录');
      return;
    }
    let res;
    try {
      res = await apiFetch(`/api/v1/approvals/${id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision: decisionType, operator: 'frontend-user' }),
      });
    } catch (e) {
      return; // 401 已由 apiFetch 统一提示
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      window.alert('操作失败：' + (data.message || res.status));
      return;
    }
    window.alert(decisionType === 'APPROVE' ? '已批准并执行' : '已拒绝');
    if (selected) {
      loadApprovals(selected.id);
      load();
    }
  };

  // P2-FE-05: 状态/服务/日期范围过滤
  const filteredIncidents = incidents.filter((i) => {
    if (fStatus === 'ACTIVE' && !['DETECTED', 'TRIAGING', 'DIAGNOSING', 'ROOT_CAUSE_FOUND', 'WAITING_APPROVAL', 'REMEDIATING', 'VERIFYING'].includes(i.status)) return false;
    if (!['ALL', 'ACTIVE'].includes(fStatus) && i.status !== fStatus) return false;
    if (fSearch && !(i.service || '').toLowerCase().includes(fSearch.toLowerCase())
        && !(i.summary || '').toLowerCase().includes(fSearch.toLowerCase())
        && String(i.id).includes(fSearch) === false && `INC-${String(i.id).padStart(4, '0')}`.toLowerCase().includes(fSearch.toLowerCase()) === false) return false;
    if (fRange && fRange[0] && fRange[1]) {
      const t = i.startedAt ? new Date(i.startedAt).getTime() : 0;
      if (t < fRange[0].startOf('day').valueOf() || t > fRange[1].endOf('day').valueOf()) return false;
    }
    return true;
  });

  const summary = {
    total: incidents.length,
    resolved: incidents.filter((i) => i.status === 'RESOLVED').length,
    active: incidents.filter((i) => ['DETECTED', 'TRIAGING', 'DIAGNOSING', 'ROOT_CAUSE_FOUND', 'WAITING_APPROVAL', 'REMEDIATING', 'VERIFYING'].includes(i.status)).length,
    waitingApproval: incidents.filter((i) => i.status === 'WAITING_APPROVAL').length,
    p1: incidents.filter((i) => i.severity === 'P1' && i.status !== 'RESOLVED').length,
  };

  const detailItems = selected ? [
    {
      key: 'info',
      label: '基本信息',
      children: (
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="服务">{selected.service}</Descriptions.Item>
          <Descriptions.Item label="状态">{selected.status}</Descriptions.Item>
          <Descriptions.Item label="Root Cause">{formatRootCause(selected.rootCause)}</Descriptions.Item>
          <Descriptions.Item label="置信度">{selected.confidence}</Descriptions.Item>
          <Descriptions.Item label="建议方案" span={2}>{selected.recommendedActions || '-'}</Descriptions.Item>
          <Descriptions.Item label="告警次数">{selected.alertCount ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="开始时间">{selected.startedAt ? new Date(selected.startedAt).toLocaleString() : '-'}</Descriptions.Item>
          <Descriptions.Item label="恢复时间">{selected.resolvedAt ? new Date(selected.resolvedAt).toLocaleString() : '-'}</Descriptions.Item>
        </Descriptions>
      ),
    },
    {
      key: 'steps',
      label: 'Agent 步骤',
      children: steps.length === 0 ? <Typography.Text type="secondary">暂无步骤</Typography.Text> : (
        <Timeline
          items={steps.map((s) => ({
            // P3-FE-04: 真实 createdAt（此前只有步骤文字，时间戳失真为渲染时刻）
            children: `${s.createdAt ? new Date(s.createdAt).toLocaleTimeString() + ' ' : ''}${s.stepType} - ${s.outputSummary || s.inputSummary || ''}`,
          }))}
        />
      ),
    },
    {
      key: 'evidence',
      label: '证据',
      children: evidence.length === 0 ? <Typography.Text type="secondary">暂无证据</Typography.Text> : (
        <List
          size="small"
          dataSource={evidence}
          renderItem={(e) => (
            <List.Item>
              <Space direction="vertical" size={0} style={{ width: '100%' }}>
                <Space>
                  <Tag color="blue">{e.source}</Tag>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>{e.evidenceKey || e.key}</Typography.Text>
                </Space>
                <Typography.Paragraph style={{ marginBottom: 0 }} ellipsis={{ rows: 2, expandable: true, symbol: '展开' }}>
                  {typeof e.content === 'string' ? e.content : JSON.stringify(e.content)}
                </Typography.Paragraph>
              </Space>
            </List.Item>
          )}
        />
      ),
    },
    {
      key: 'tools',
      label: 'Tool 调用',
      children: toolCalls.length === 0 ? <Typography.Text type="secondary">暂无 Tool 调用</Typography.Text> : (
        <List
          size="small"
          dataSource={toolCalls}
          renderItem={(t) => (
            <List.Item>
              <Space>
                <Tag color={t.status === 'SUCCESS' ? 'green' : 'red'}>{t.status}</Tag>
                <span>{t.toolName}</span>
                <span>{t.resultSummary || t.error || ''}</span>
              </Space>
            </List.Item>
          )}
        />
      ),
    },
    {
      key: 'remediation',
      label: '修复记录',
      children: remediations.length === 0 ? <Typography.Text type="secondary">暂无修复记录</Typography.Text> : (
        <List
          size="small"
          dataSource={remediations}
          renderItem={(r) => (
            <List.Item>
              <Space>
                <Tag color={r.status === 'SUCCESS' ? 'green' : 'orange'}>{r.status}</Tag>
                <span>{r.toolName}</span>
                <span>{r.resultSummary}</span>
              </Space>
            </List.Item>
          )}
        />
      ),
    },
    {
      key: 'approval',
      label: '审批',
      children: approvals.length === 0 ? <Typography.Text type="secondary">暂无审批记录</Typography.Text> : approvals.map((a) => (
        <Card size="small" key={a.id} style={{ marginBottom: 8 }}>
          <Space>
            <Tag color={a.status === 'PENDING' ? 'gold' : a.status === 'APPROVE' ? 'green' : 'red'}>{a.status}</Tag>
            <span>{a.actionType}</span>
            {a.status === 'PENDING' && (
              <>
                <Button size="small" type="primary" onClick={() => decision(a.id, 'APPROVE')}>批准</Button>
                <Button size="small" danger onClick={() => decision(a.id, 'REJECT')}>拒绝</Button>
              </>
            )}
          </Space>
        </Card>
      )),
    },
  ] : [];

  return (
    <Layout style={{ minHeight: '100vh', background: '#F7F8FA' }}>
      {error && (
        <Alert type='error' message={error} showIcon closable onClose={() => setError('')} />
      )}
      <Header style={{
        background: '#FFFFFF',
        borderBottom: '1px solid #E5E7EB',
        height: 60,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0 32px',
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
          <span style={{ fontSize: 16, fontWeight: 600, color: '#111827' }}>AI SRE</span>
          <span style={{ fontSize: 12, color: '#667085' }}>Intelligent Reliability Platform</span>
        </div>
        <Space>
          {authToken && <span style={{ fontSize: 12, color: '#667085' }}>admin 已登录</span>}
          {authToken ? (
            <Button onClick={logout}>退出</Button>
          ) : (
            <Button type="primary" icon={<LoginOutlined />} onClick={() => setLoginOpen(true)}>登录</Button>
          )}
        </Space>
      </Header>
      <Modal
        title="登录 AI SRE 控制台"
        open={loginOpen}
        okText="登录"
        cancelText="取消"
        onOk={() => login(loginUser, loginPass)}
        onCancel={() => setLoginOpen(false)}
      >
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Input placeholder="用户名（本地默认 admin）" value={loginUser}
                 onChange={(e) => setLoginUser(e.target.value)} onPressEnter={() => login(loginUser, loginPass)} />
          <Input.Password placeholder="密码" value={loginPass}
                 onChange={(e) => setLoginPass(e.target.value)} onPressEnter={() => login(loginUser, loginPass)} />
        </Space>
      </Modal>
      <Content style={{ padding: '24px 32px', maxWidth: 1440, width: '100%', margin: '0 auto' }}>
        <Row justify="space-between" align="middle" style={{ marginBottom: 20 }}>
          <Col>
            <div style={{ fontSize: 24, fontWeight: 600, color: '#111827' }}>系统概览</div>
            <div style={{ fontSize: 13, color: '#667085', marginTop: 2 }}>实时监控服务健康状态、Incident 与 AI 诊断结果</div>
          </Col>
          <Col>
            <Space>
              <SystemStatus incidents={incidents} />
              <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
            </Space>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={12} lg={6}><MetricCard label="Incident" value={summary.total} hint={`${summary.p1} active critical`} /></Col>
          <Col xs={12} lg={6}><MetricCard label="Active" value={summary.active} hint="Currently processing" color="#D97706" /></Col>
          <Col xs={12} lg={6}><MetricCard label="Recovered" value={summary.resolved} hint="Recovered incidents" color="#16A34A" /></Col>
          <Col xs={12} lg={6}><MetricCard label="Pending Approval" value={summary.waitingApproval} hint="Require human action" color="#7C3AED" /></Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={14}>
            <Card title="Service Health" styles={{ body: { padding: '8px 16px' } }}>
              <ServiceHealthPanel services={services} />
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title="Incident Overview">
              <IncidentOverview incidents={incidents} />
            </Card>
          </Col>
        </Row>

        <Card title="Incidents" style={{ marginBottom: 16 }} extra={
          <Space wrap>
            <Input.Search placeholder="搜索 ID / 服务 / 摘要" allowClear style={{ width: 200 }}
                          onSearch={setFSearch} onChange={(e) => { if (!e.target.value) setFSearch(''); }} />
            <Select value={fStatus} style={{ width: 160 }} onChange={setFStatus}
                    options={[
                      { value: 'ALL', label: '全部状态' },
                      { value: 'ACTIVE', label: '活跃（未恢复）' },
                      { value: 'DETECTED', label: 'DETECTED' },
                      { value: 'ROOT_CAUSE_FOUND', label: 'ROOT_CAUSE_FOUND' },
                      { value: 'WAITING_APPROVAL', label: 'WAITING_APPROVAL' },
                      { value: 'REMEDIATING', label: 'REMEDIATING' },
                      { value: 'RESOLVED', label: 'RESOLVED' },
                      { value: 'FAILED', label: 'FAILED' },
                    ]} />
            <DatePicker.RangePicker onChange={setFRange} style={{ width: 240 }} placeholder={['开始日期', '结束日期']} />
            <span style={{ fontSize: 12, color: '#98A2B3' }}>{filteredIncidents.length}/{incidents.length} 条</span>
          </Space>
        }>
          <IncidentTable incidents={filteredIncidents} onSelect={setSelected} loading={loading} selectedId={selected?.id} />
        </Card>

        <div ref={detailRef}>
        {selected && (
          <Card title={`INC-${String(selected.id).padStart(4, '0')} 详情 — ${selected.service} [${selected.status}]`}
                extra={<Button size="small" onClick={() => setSelected(null)}>关闭</Button>}
                style={{ marginBottom: 16 }}>
            <Tabs items={detailItems} />
          </Card>
        )}
        </div>
      </Content>
    </Layout>
  );
}
