export const colors = {
  primary: '#2563EB',
  textPrimary: '#111827',
  textSecondary: '#667085',
  border: '#E5E7EB',
  background: '#F7F8FA',
  success: '#16A34A',
  warning: '#D97706',
  error: '#DC2626',
  critical: '#B42318',
};

export const severityConfig = {
  P1: { color: '#DC2626', bg: '#FEF2F2', label: 'Critical' },
  P2: { color: '#D97706', bg: '#FFF7ED', label: 'High' },
  P3: { color: '#B45309', bg: '#FFFBEB', label: 'Medium' },
  P4: { color: '#667085', bg: '#F9FAFB', label: 'Low' },
};

export const statusConfig = {
  DETECTED: { color: '#667085', bg: '#F9FAFB', label: 'Detected' },
  TRIAGING: { color: '#2563EB', bg: '#EFF6FF', label: 'Triaging' },
  DIAGNOSING: { color: '#2563EB', bg: '#EFF6FF', label: 'Diagnosing' },
  ROOT_CAUSE_FOUND: { color: '#C2410C', bg: '#FFF7ED', label: 'Root Cause Found' },
  WAITING_APPROVAL: { color: '#7C3AED', bg: '#F5F3FF', label: 'Pending Approval' },
  REMEDIATING: { color: '#D97706', bg: '#FFFBEB', label: 'Remediating' },
  VERIFYING: { color: '#0284C7', bg: '#F0F9FF', label: 'Verifying' },
  RESOLVED: { color: '#16A34A', bg: '#F0FDF4', label: 'Resolved' },
  FAILED: { color: '#DC2626', bg: '#FEF2F2', label: 'Failed' },
};

export function formatRootCause(value) {
  if (!value || value === 'unknown') return 'Investigating...';
  if (value === 'diagnosis_timeout') return 'Diagnosis timeout';
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  const now = Date.now();
  const diff = now - date.getTime();
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}