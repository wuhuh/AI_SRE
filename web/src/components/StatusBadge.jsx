import React from 'react';
import { statusConfig, severityConfig } from '../theme';

export function SeverityBadge({ severity }) {
  const cfg = severityConfig[severity] || severityConfig.P3;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '2px 8px',
        borderRadius: 6,
        fontSize: 12,
        fontWeight: 500,
        color: cfg.color,
        background: cfg.bg,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: cfg.color }} />
      {cfg.label}
    </span>
  );
}

export function IncidentStatusBadge({ status }) {
  const cfg = statusConfig[status] || statusConfig.DETECTED;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 8px',
        borderRadius: 6,
        fontSize: 12,
        fontWeight: 500,
        color: cfg.color,
        background: cfg.bg,
      }}
    >
      {cfg.label}
    </span>
  );
}