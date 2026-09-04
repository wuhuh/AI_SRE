import React, { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Col,
  Descriptions,
  Layout,
  List,
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

export default function App() {
  const [incidents, setIncidents] = useState([]);
  const [services, setServices] = useState([]);
  const [selected, setSelected] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('aisre_token') || '');
  const [evidence, setEvidence] = useState([]);
  const [toolCalls, setToolCalls] = useState([]);
  const [remediations, setRemediations] = useState([]);
  const [steps, setSteps] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/incidents');
      setIncidents(await res.json());
    } finally {
      setLoading(false);
    }
  };

  const loadServices = async () => {
    const res = await fetch('/api/v1/dashboard/services');
    if (res.ok) {
      setServices(await res.json());
    }
  };

  const login = async () => {
    const username = window.prompt('用户名');
    if (!username) return;
    const password = window.prompt('密码');
    if (!password) return;
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (res.ok && data.token) {
      setAuthToken(data.token);
      localStorage.setItem('aisre_token', data.token);
      window.alert('登录成功');
    } else {
      window.alert(data.message || '登录失败');
    }
  };

  const authHeaders = () => (authToken ? { Authorization: `Bearer ${authToken}` } : {});

  const loadApprovals = async (id) => {
    if (!id) return;
    const res = await fetch(`/api/v1/approvals/incident/${id}`);
    if (res.ok) {
      setApprovals(await res.json());
    }
  };

  const loadDetails = async (id) => {
    if (!id) return;
    const [ev, tc, rm, st] = await Promise.all([
      fetch(`/api/v1/incidents/${id}/evidence`),
      fetch(`/api/v1/incidents/${id}/tool-calls`),
      fetch(`/api/v1/incidents/${id}/remediations`),
      fetch(`/api/v1/incidents/${id}/steps`),
    ]);
    if (ev.ok) setEvidence(await ev.json());
    if (tc.ok) setToolCalls(await tc.json());
    if (rm.ok) setRemediations(await rm.json());
    if (st.ok) setSteps(await st.json());
  };

  useEffect(() => {
    load();
    loadServices();
    const es = new EventSource('/api/v1/stream/incidents');
    es.onmessage = () => load();
    const timer = setInterval(loadServices, 10000);
    return () => {
      es.close();
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (selected) {
      loadApprovals(selected.id);
      loadDetails(selected.id);
    }
  }, [selected]);

  const decision = async (id, decisionType) => {
    if (!authToken) {
      window.alert('请先登录');
      return;
    }
    const res = await fetch(`/api/v1/approvals/${id}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ decision: decisionType, operator: 'frontend-user' }),
    });
    if (!res.ok) {
      const data = await res.json();
      window.alert('操作失败：' + (data.message || res.status));
      return;
    }
    window.alert(decisionType === 'APPROVE' ? '已批准并执行' : '已拒绝');
    if (selected) {
      loadApprovals(selected.id);
      load();
    }
  };

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
        </Descriptions>
      ),
    },
    {
      key: 'steps',
      label: 'Agent 步骤',
      children: steps.length === 0 ? <Typography.Text type="secondary">暂无步骤</Typography.Text> : (
        <Timeline
          items={steps.map((s) => ({
            children: `${s.stepType} - ${s.outputSummary || s.inputSummary || ''}`,
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
              <Space>
                <Tag color="blue">{e.source}</Tag>
                <span>{e.evidenceKey || e.key}: {e.content}</span>
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
        <Button icon={<LoginOutlined />} onClick={login}>登录</Button>
      </Header>
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

        <Card title="Recent Incidents" style={{ marginBottom: 16 }}>
          <IncidentTable incidents={incidents} onSelect={setSelected} loading={loading} />
        </Card>

        {selected && (
          <Card title={`INC-${String(selected.id).padStart(4, '0')} 详情`} style={{ marginBottom: 16 }}>
            <Tabs items={detailItems} />
          </Card>
        )}
      </Content>
    </Layout>
  );
}
