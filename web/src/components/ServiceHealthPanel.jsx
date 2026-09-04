import React from 'react';
import { Skeleton } from 'antd';

export default function ServiceHealthPanel({ services }) {
  if (!services.length) {
    return <Skeleton active paragraph={{ rows: 4 }} />;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {services.map((s) => {
        const healthy = s.status === 'UP';
        return (
          <div
            key={s.service}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 4px',
              borderBottom: '1px solid #F2F4F7',
              minHeight: 48,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: healthy ? '#16A34A' : '#DC2626' }} />
              <span style={{ fontSize: 13, fontWeight: 500, color: '#111827' }}>{s.service}</span>
            </div>
            <div style={{ fontSize: 12, color: healthy ? '#16A34A' : '#DC2626', fontWeight: 500 }}>
              {healthy ? 'Healthy' : 'Down'} · {s.latencyMs}ms
            </div>
          </div>
        );
      })}
    </div>
  );
}