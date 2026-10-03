import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'danger' | 'warning' | 'mono';
  size?: 'sm' | 'md';
  style?: React.CSSProperties;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  style,
}) => {
  const getStyles = (): React.CSSProperties => {
    switch (variant) {
      case 'success':
        return {
          backgroundColor: 'var(--success-bg)',
          color: 'var(--success-color)',
          borderColor: 'var(--success-border)',
        };
      case 'danger':
        return {
          backgroundColor: 'var(--danger-bg)',
          color: 'var(--danger-color)',
          borderColor: 'var(--danger-border)',
        };
      case 'warning':
        return {
          backgroundColor: 'var(--warning-bg)',
          color: 'var(--warning-color)',
          borderColor: 'var(--warning-border)',
        };
      case 'mono':
        return {
          backgroundColor: 'var(--bg-card-muted)',
          color: 'var(--text-secondary)',
          borderColor: 'var(--border-subtle)',
          fontFamily: 'var(--font-mono)',
        };
      case 'default':
      default:
        return {
          backgroundColor: 'var(--badge-bg)',
          color: 'var(--badge-text)',
          borderColor: 'var(--badge-border)',
        };
    }
  };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        fontSize: size === 'sm' ? '11px' : '12px',
        fontWeight: 600,
        padding: size === 'sm' ? '2px 6px' : '3px 8px',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid',
        letterSpacing: '0.02em',
        ...getStyles(),
        ...style,
      }}
    >
      {children}
    </span>
  );
};
