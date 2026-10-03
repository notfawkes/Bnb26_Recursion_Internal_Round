import React from 'react';
import type { BuilderStatus } from '../../types';

export interface StatusIndicatorProps {
  status: BuilderStatus | 'online' | 'offline';
  label?: string;
  pulse?: boolean;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  pulse = true,
}) => {
  const getColor = (): string => {
    switch (status) {
      case 'complete':
      case 'online':
        return 'var(--success-color)';
      case 'failed':
      case 'offline':
        return 'var(--danger-color)';
      case 'processing':
        return 'var(--warning-color)';
      case 'idle':
      default:
        return 'var(--text-muted)';
    }
  };

  const color = getColor();

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        fontSize: '12px',
        fontWeight: 500,
        color: 'var(--text-secondary)',
      }}
    >
      <span
        style={{
          width: '7px',
          height: '7px',
          borderRadius: '50%',
          backgroundColor: color,
          display: 'inline-block',
          boxShadow: `0 0 6px ${color}`,
          animation: pulse && (status === 'processing' || status === 'online') ? 'pulseDot 1.5s infinite' : 'none',
        }}
      />
      {label && <span>{label}</span>}
    </span>
  );
};
