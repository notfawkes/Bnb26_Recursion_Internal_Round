import React, { useState } from 'react';
import { StatusIndicator } from '../ui/StatusIndicator';
import { ThemeToggle } from '../ui/ThemeToggle';

export interface NavbarProps {
  onNavClick?: (section: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onNavClick }) => {
  const [activeTab, setActiveTab] = useState<'Dashboard' | 'Builders' | 'Audit' | 'Blockchain'>('Dashboard');

  const navItems: ('Dashboard' | 'Builders' | 'Audit' | 'Blockchain')[] = [
    'Dashboard',
    'Builders',
    'Audit',
    'Blockchain',
  ];

  const handleTabClick = (item: typeof activeTab) => {
    setActiveTab(item);
    if (onNavClick) onNavClick(item);
  };

  return (
    <header
      style={{
        borderBottom: '1px solid var(--border-color)',
        backgroundColor: 'var(--bg-card)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        transition: 'background-color 0.25s ease, border-color 0.25s ease',
      }}
    >
      <div
        style={{
          maxWidth: '1280px',
          margin: '0 auto',
          padding: '0 24px',
          height: '56px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '24px',
        }}
      >
        {/* Left: Brand & Tagline */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontWeight: 800,
                fontSize: '17px',
                letterSpacing: '0.08em',
                color: 'var(--brand-color)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span style={{ color: 'var(--brand-color)', opacity: 0.85 }}>◈</span> QUORUM
            </span>
            <span
              style={{
                fontSize: '11px',
                color: 'var(--text-muted)',
                fontWeight: 500,
                display: 'none',
              }}
              className="navbar-tagline"
            >
              Don't Trust the Binary. Trust the Builders.
            </span>
          </div>

          <style>{`
            @media (min-width: 860px) {
              .navbar-tagline { display: inline-block !important; }
            }
          `}</style>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {navItems.map((item) => {
            const isActive = activeTab === item;
            return (
              <button
                key={item}
                onClick={() => handleTabClick(item)}
                style={{
                  padding: '6px 12px',
                  fontSize: '13px',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: isActive ? 'var(--bg-surface)' : 'transparent',
                  border: isActive ? '1px solid var(--border-color)' : '1px solid transparent',
                  transition: 'all 0.15s ease',
                }}
              >
                {item}
              </button>
            );
          })}
        </nav>

        {/* Right: Network Status & Theme Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <StatusIndicator status="online" label="Network Connected" />
          </div>

          <ThemeToggle />
        </div>
      </div>
    </header>
  );
};
