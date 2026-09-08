import React from 'react';
import { Table, Tooltip } from 'antd';
import { SeverityBadge, IncidentStatusBadge } from './StatusBadge';
import { formatRootCause, formatTime } from '../theme';

export default function IncidentTable({ incidents, onSelect, loading, selectedId }) {
  const columns = [
    {
      title: 'Incident',
      dataIndex: 'id',
      width: 110,
      render: (id) => <span style={{ fontWeight: 500, color: '#111827' }}>INC-{String(id).padStart(4, '0')}</span>,
    },
    { title: 'Service', dataIndex: 'service' },
    {
      title: 'Severity',
      dataIndex: 'severity',
      render: (v) => <SeverityBadge severity={v} />,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      render: (v) => <IncidentStatusBadge status={v} />,
    },
    {
      title: 'Started',
      dataIndex: 'startedAt',
      render: (v) => (
        <Tooltip title={v}>
          <span>{formatTime(v)}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Root Cause',
      dataIndex: 'rootCause',
      render: (v, record) => (
        <div>
          <div style={{ fontSize: 13, color: '#111827', fontWeight: 500 }}>{formatRootCause(v)}</div>
          {record.confidence != null && record.confidence > 0 && (
            <div style={{ fontSize: 12, color: '#98A2B3' }}>confidence {Math.round(record.confidence * 100)}%</div>
          )}
        </div>
      ),
    },
  ];

  return (
    <Table
      rowKey="id"
      columns={columns}
      dataSource={incidents}
      loading={loading}
      rowClassName={(record) => (record.id === selectedId ? 'incident-row-selected' : '')}
      pagination={{ pageSize: 10, showSizeChanger: false, showTotal: (t) => `共 ${t} 条` }}
      onRow={(record) => ({
        onClick: () => onSelect(record),
        style: { cursor: 'pointer' },
      })}
    />
  );
}