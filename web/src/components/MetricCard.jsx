import React from 'react';

export default function MetricCard({ label, value, hint, color = '#111827', onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: '#fff',
        border: '1px solid #E5E7EB',
        borderRadius: 10,
        padding: '16px 20px',
        minHeight: 104,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        ...(onClick ? { cursor: 'pointer', transition: 'box-shadow .2s' } : {}),
      }}
      onMouseEnter={onClick ? (e) => { e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,.08)'; } : undefined}
      onMouseLeave={onClick ? (e) => { e.currentTarget.style.boxShadow = 'none'; } : undefined}
    >
      <div style={{ fontSize: 13, color: '#667085', fontWeight: 500 }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 600, color, lineHeight: 1.2, marginTop: 4 }}>{value}</div>
      {hint && <div style={{ fontSize: 12, color: '#98A2B3', marginTop: 4 }}>{hint}</div>}
      {onClick && <div style={{ fontSize: 11, color: '#B6BEC9', marginTop: 2 }}>点击筛选 ↓</div>}
    </div>
  );
}
