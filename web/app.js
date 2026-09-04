const API = window.API_BASE || '';
let authToken = localStorage.getItem('aisre_token') || '';
let currentDetailId = null;

function authHeaders() {
  return authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
}

async function login() {
  const username = prompt('用户名');
  if (!username) return;
  const password = prompt('密码');
  if (!password) return;
  try {
    const res = await fetch(`${API}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (res.ok && data.token) {
      authToken = data.token;
      localStorage.setItem('aisre_token', authToken);
      alert('登录成功');
      loadIncidents();
    } else {
      alert(data.message || '登录失败');
    }
  } catch (e) {
    alert('登录失败：' + e.message);
  }
}


const STATUS_TEXT = {
  DETECTED: '已检测',
  TRIAGING: '分类中',
  DIAGNOSING: '诊断中',
  ROOT_CAUSE_FOUND: '已定位根因',
  WAITING_APPROVAL: '等待审批',
  REMEDIATING: '修复中',
  VERIFYING: '验证中',
  RESOLVED: '已恢复',
  FAILED: '失败'
};

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function badge(status) {
  return `<span class="badge st-${esc(status)}">${esc(STATUS_TEXT[status] || status)}</span>`;
}

async function loadIncidents() {
  const el = document.getElementById('incident-list');
  el.innerHTML = '<div class="empty">加载中...</div>';
  try {
    const res = await fetch(`${API}/api/v1/incidents`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const incidents = await res.json();
    renderStats(incidents);
    if (!incidents.length) {
      el.innerHTML = '<div class="empty">暂无 Incident，请先注入故障并发送告警</div>';
      return;
    }
    const rows = incidents.map((inc) => `
      <tr onclick="showDetail(${inc.id})">
        <td>#${inc.id}</td>
        <td>${esc(inc.service || '-')}</td>
        <td><span class="badge sev-${esc(inc.severity || 'P3')}">${esc(inc.severity || '-')}</span></td>
        <td>${badge(inc.status)}</td>
        <td>${new Date(inc.startedAt).toLocaleString()}</td>
        <td>${esc(inc.rootCause || '尚未诊断')}</td>
      </tr>
    `).join('');
    el.innerHTML = `
      <table>
        <thead><tr><th>ID</th><th>服务</th><th>级别</th><th>状态</th><th>开始时间</th><th>Root Cause</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted" style="margin-top:12px;">点击任意一行查看详情</p>
    `;
  } catch (err) {
    el.innerHTML = `<div class="empty">加载失败：${esc(err.message)}<br>请确认 Control Plane 已启动</div>`;
  }
}

function renderStats(incidents) {
  document.getElementById('stat-total').textContent = incidents.length;
  document.getElementById('stat-resolved').textContent = incidents.filter(i => i.status === 'RESOLVED').length;
  document.getElementById('stat-diagnosing').textContent = incidents.filter(i => ['DETECTED', 'TRIAGING', 'DIAGNOSING', 'ROOT_CAUSE_FOUND'].includes(i.status)).length;
  document.getElementById('stat-approval').textContent = incidents.filter(i => i.status === 'WAITING_APPROVAL').length;
}

async function showDetail(id) {
  currentDetailId = id;
  const detail = document.getElementById('detail');
  detail.style.display = 'block';
  detail.innerHTML = '<div class="empty">加载详情...</div>';
  try {
    const res = await fetch(`${API}/api/v1/incidents/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const inc = await res.json();

    let approvalsHtml = '<div class="empty">暂无审批记录</div>';
    try {
      const ar = await fetch(`${API}/api/v1/approvals/incident/${id}`);
      if (ar.ok) {
        const approvals = await ar.json();
        if (approvals.length) {
          approvalsHtml = '<ul class="timeline">' + approvals.map(a => `
            <li>
              <strong>${esc(a.actionType)}</strong>
              <span class="badge st-${esc(a.status)}">${esc(a.status)}</span>
              <div class="muted">操作人：${esc(a.decidedBy || a.requestedBy || '-')}</div>
              <div class="muted">${esc(a.comment || '')}</div>
              <div class="muted">${new Date(a.createdAt).toLocaleString()}</div>
            </li>
          `).join('') + '</ul>';
        }
      }
    } catch (e) { /* approval is optional */ }

    let evidenceHtml = '<div class="empty">暂无证据</div>';
      try {
        const er = await fetch(`${API}/api/v1/incidents/${id}/evidence`);
        if (er.ok) {
          const evidence = await er.json();
          if (evidence.length) {
            evidenceHtml = '<ul>' + evidence.map(e => `
              <li>
                <strong>[${esc(e.source)}] ${esc(e.evidenceKey || e.key)}</strong>
                <div class="muted">${esc(e.content)}</div>
                <div class="muted">${new Date(e.collectedAt).toLocaleString()}</div>
              </li>
            `).join('') + '</ul>';
          }
        }
      } catch (e) { /* evidence is optional */ }

      let toolCallsHtml = '<div class="empty">暂无 Tool 调用记录</div>';
      try {
        const tr = await fetch(`${API}/api/v1/incidents/${id}/tool-calls`);
        if (tr.ok) {
          const calls = await tr.json();
          if (calls.length) {
            toolCallsHtml = '<table><thead><tr><th>工具</th><th>状态</th><th>耗时</th><th>结果摘要</th></tr></thead><tbody>' + calls.map(c => `
              <tr>
                <td>${esc(c.toolName)}</td>
                <td>${esc(c.status)}</td>
                <td>${c.durationMs != null ? c.durationMs + 'ms' : '-'}</td>
                <td>${esc(c.resultSummary || c.error || '-')}</td>
              </tr>
            `).join('') + '</tbody></table>';
          }
        }
      } catch (e) { /* tool calls are optional */ }

      let remediationsHtml = '<div class="empty">暂无修复记录</div>';
      try {
        const rr = await fetch(`${API}/api/v1/incidents/${id}/remediations`);
        if (rr.ok) {
          const remediations = await rr.json();
          if (remediations.length) {
            remediationsHtml = '<ul>' + remediations.map(r => `
              <li>
                <strong>${esc(r.toolName)}</strong>
                <span class="badge st-${esc(r.status)}">${esc(r.status)}</span>
                <div class="muted">${esc(r.resultSummary)}</div>
                <div class="muted">${new Date(r.createdAt).toLocaleString()}</div>
              </li>
            `).join('') + '</ul>';
          }
        }
      } catch (e) { /* remediations are optional */ }

      let stepsHtml = '<div class="empty">暂无 Agent 步骤</div>';
      try {
        const sr = await fetch(`${API}/api/v1/incidents/${id}/steps`);
        if (sr.ok) {
          const steps = await sr.json();
          if (steps.length) {
            stepsHtml = '<ul>' + steps.map(s => `
              <li>
                <strong>${esc(s.stepType)}</strong>
                <span class="badge st-${esc(s.status)}">${esc(s.status)}</span>
                <div class="muted">${esc(s.outputSummary || s.inputSummary || '')}</div>
                <div class="muted">${new Date(s.createdAt).toLocaleString()}</div>
              </li>
            `).join('') + '</ul>';
          }
        }
      } catch (e) { /* steps are optional */ }

      let auditHtml = '<div class="empty">暂无审计日志</div>';
      try {
        const ar = await fetch(`${API}/api/v1/incidents/${id}/audit-logs`);
        if (ar.ok) {
          const logs = await ar.json();
          if (logs.length) {
            auditHtml = '<ul>' + logs.map(l => `
              <li>
                <strong>${esc(l.action)}</strong>
                <span class="muted">by ${esc(l.actor)}</span>
                <div class="muted">${esc(l.detail || '')}</div>
                <div class="muted">${new Date(l.createdAt).toLocaleString()}</div>
              </li>
            `).join('') + '</ul>';
          }
        }
      } catch (e) { /* audit optional */ }

      const timelineItems = buildTimeline(inc);
    detail.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2 style="margin:0">Incident #${inc.id} 详情</h2>
        <button class="btn btn-secondary" onclick="document.getElementById('detail').style.display='none'">关闭</button>
          <button class="btn" onclick="showReport(${inc.id})">生成报告</button>
      </div>
      <div class="detail-section">
        <h3>基本信息</h3>
        <table>
          <tr><th>服务</th><td>${esc(inc.service || '-')}</td><th>级别</th><td><span class="badge sev-${esc(inc.severity || 'P3')}">${esc(inc.severity || '-')}</span></td></tr>
          <tr><th>状态</th><td>${badge(inc.status)}</td><th>告警数量</th><td>${inc.alertCount ?? 0}</td></tr>
          <tr><th>开始时间</th><td>${new Date(inc.startedAt).toLocaleString()}</td><th>恢复时间</th><td>${inc.resolvedAt ? new Date(inc.resolvedAt).toLocaleString() : '-'}</td></tr>
          <tr><th>摘要</th><td colspan="3">${esc(inc.summary || '-')}</td></tr>
          <tr><th>Root Cause</th><td colspan="3">${esc(inc.rootCause || '尚未诊断')}</td></tr>
          <tr><th>置信度</th><td colspan="3">${inc.confidence != null ? (inc.confidence * 100).toFixed(1) + '%' : '-'}</td></tr>
        </table>
      </div>
      <div class="detail-section">
        <h3>诊断时间线</h3>
        <ul class="timeline">${timelineItems}</ul>
      </div>
      <div class="detail-section">
          <h3>Agent 步骤</h3>
          ${stepsHtml}
        </div>
        <div class="detail-section">
          <h3>证据 Evidence</h3>
          ${evidenceHtml}
        </div>
        <div class="detail-section">
          <h3>Tool 调用记录</h3>
          ${toolCallsHtml}
        </div>
        <div class="detail-section">
          <h3>修复记录</h3>
          ${remediationsHtml}
        </div>
        <div class="detail-section">
        <h3>审计日志</h3>
        ${auditHtml}
        </div>
        <div class="detail-section">
        <h3>审批记录</h3>
        ${approvalsHtml}
      </div>
    `;
  } catch (err) {
    detail.innerHTML = `<div class="empty">加载详情失败：${esc(err.message)}</div>`;
  }
}

function buildTimeline(inc) {
  const items = [
    { time: inc.startedAt, text: '告警接入，Incident 创建' },
  ];
  if (['TRIAGING', 'DIAGNOSING', 'ROOT_CAUSE_FOUND', 'WAITING_APPROVAL', 'REMEDIATING', 'VERIFYING', 'RESOLVED', 'FAILED'].includes(inc.status)) {
    items.push({ time: inc.startedAt, text: 'Agent 开始诊断，查询 Metrics / Logs / Trace / Runbook' });
  }
  if (['ROOT_CAUSE_FOUND', 'WAITING_APPROVAL', 'REMEDIATING', 'VERIFYING', 'RESOLVED', 'FAILED'].includes(inc.status)) {
    items.push({ time: inc.startedAt, text: `定位 Root Cause：${inc.rootCause || 'unknown'}` });
  }
  if (['WAITING_APPROVAL', 'REMEDIATING', 'VERIFYING', 'RESOLVED', 'FAILED'].includes(inc.status)) {
    items.push({ time: inc.startedAt, text: '高风险修复操作等待人工审批' });
  }
  if (['REMEDIATING', 'VERIFYING', 'RESOLVED', 'FAILED'].includes(inc.status)) {
    items.push({ time: inc.startedAt, text: '审批通过，执行修复操作' });
  }
  if (['VERIFYING', 'RESOLVED', 'FAILED'].includes(inc.status)) {
    items.push({ time: inc.startedAt, text: 'Agent 验证恢复状态' });
  }
  if (inc.status === 'RESOLVED') {
    items.push({ time: inc.resolvedAt, text: '✅ Incident 已恢复并关闭' });
  }
  if (inc.status === 'FAILED') {
    items.push({ time: inc.startedAt, text: '❌ 流程失败，需要人工介入' });
  }
  return items.map((item, idx) => `
    <li>
      <strong>${idx + 1}. ${esc(item.text)}</strong>
      <div class="muted">${new Date(item.time).toLocaleString()}</div>
    </li>
  `).join('');
}

function showDemoHelp() {
  const detail = document.getElementById('detail');
  detail.style.display = 'block';
  detail.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <h2 style="margin:0">🎯 演示帮助</h2>
      <button class="btn btn-secondary" onclick="document.getElementById('detail').style.display='none'">关闭</button>
    </div>
    <div class="detail-section">
      <h3>如何看到完整功能？</h3>
      <div class="code-block">
        1. 注入故障：<br>
        &nbsp;&nbsp;python fault-injection/inject_fault.py redis_pool_exhausted --enable<br><br>
        2. 发送告警：<br>
        &nbsp;&nbsp;curl -X POST http://localhost:8080/api/v1/alerts \<br>
        &nbsp;&nbsp;&nbsp;-H "Content-Type: application/json" \<br>
        &nbsp;&nbsp;&nbsp;-d '{"service":"payment-service","alertName":"latency_high","resource":"payment-1","severity":"P1","summary":"payment p99 high"}'<br><br>
        3. 回到本页面点击“刷新”，即可看到新 Incident。<br>
        4. 点击 Incident 查看状态、Root Cause、时间线和审批记录。
      </div>
    </div>
    <div class="detail-section">
      <h3>当前页面能做什么？</h3>
      <ul>
        <li>查看 Incident 列表和实时状态</li>
        <li>查看 Root Cause / 置信度 / 告警数量</li>
        <li>查看诊断时间线</li>
        <li>查看审批记录</li>
      </ul>
    </div>
  `;
}

async function showReport(id) {
  const detail = document.getElementById('detail');
  try {
    const res = await fetch(`${API}/api/v1/incidents/${id}/report`);
    const data = await res.json();
    detail.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2 style="margin:0">Incident Report #${id}</h2>
        <button class="btn btn-secondary" onclick="document.getElementById('detail').style.display='none'">关闭</button>
      </div>
      <pre style="background:#0f172a;color:#e2e8f0;padding:16px;border-radius:8px;overflow-x:auto;white-space:pre-wrap;">${esc(data.report || '')}</pre>
    `;
  } catch (e) {
    detail.innerHTML = `<div class="empty">报告生成失败：${esc(e.message)}</div>`;
  }
}

async function decision(id, decisionType) {
  if (!authToken) {
    alert('请先登录');
    return;
  }
  try {
    const res = await fetch(`${API}/api/v1/approvals/${id}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ decision: decisionType, operator: 'frontend-user' }),
    });
    if (!res.ok) {
      const data = await res.json();
      alert('操作失败：' + (data.message || res.status));
      return;
    }
    alert((decisionType === 'APPROVE' ? '已批准' : '已拒绝') + '，并已执行/刷新');
    if (currentDetailId) showDetail(currentDetailId);
    loadIncidents();
  } catch (e) {
    alert('操作失败：' + e.message);
  }
}

window.loadIncidents = loadIncidents;
window.showDetail = showDetail;
window.showDemoHelp = showDemoHelp;
loadIncidents();

// 实时订阅 Incident 事件，收到后自动刷新列表
if (window.EventSource) {
  const es = new EventSource(`${API}/api/v1/stream/incidents`);
  es.onmessage = () => loadIncidents();
  es.onerror = () => es.close();
}