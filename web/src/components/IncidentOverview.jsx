import React from 'react';

export default function IncidentOverview({ incidents }) {
  const p1 = incidents.filter((i) => i.severity === 'P1').length;
  const p2 = incidents.filter((i) => i.severity === 'P2').length;
  const p3 = incidents.filter((i) => i.severity === 'P3').length;
  const recovered = incidents.filter((i) => i.status === 'RESOLVED').length;
  const total = Math.max(p1 + p2 + p3 + recovered, 1);
  const bars = [
    { label: 'Critical', value: p1, color: '#DC2626' },
    { label: 'High', value: p2, color: '#D97706' },
    { label: 'Medium', value: p3, color: '#B45309' },
    { label: 'Recovered', value: recovered, color: '#16A34A' },
  ];
  return (
    <div>
      {bars.map((b) => (
        <div key={b.label} style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#667085', marginBottom: 4 }}>
            <span>{b.label}</span>
            <span>{b.value}</span>
          </div>
          <div style={{ height: 6, background: '#F2F4F7', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ width: `${(b.value / total) * 100}%`, height: '100%', background: b.color }} />
          </div>
        </div>
      ))}
    </div>
  );
}