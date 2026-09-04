import React from 'react';

export default function SystemStatus({ incidents }) {
  const active = incidents.filter((i) => ['DETECTED', 'TRIAGING', 'DIAGNOSING', 'ROOT_CAUSE_FOUND', 'WAITING_APPROVAL', 'REMEDIATING', 'VERIFYING'].includes(i.status)).length;
  const critical = incidents.filter((i) => i.severity === 'P1' && i.status !== 'RESOLVED').length;
  let state = 'HEALTHY';
  let color = '#16A34A';
  if (critical > 0) {
    state = 'CRITICAL';
    color = '#DC2626';
  } else if (active > 0) {
    state = 'DEGRADED';
    color = '#D97706';
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <span style={{ width: 10, height: 10, borderRadius: '50%', background: color }} />
      <div>
        <div style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>{state}</div>
        <div style={{ fontSize: 12, color: '#667085' }}>
          {active} active incidents · {critical} critical services
        </div>
      </div>
    </div>
  );
}