import React from 'react';

export interface FlowLinesProps {
  isFlowing: boolean;
}

export const FlowLines: React.FC<FlowLinesProps> = ({ isFlowing }) => {
  return (
    <div
      style={{
        width: '100%',
        height: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        margin: '0 auto',
      }}
    >
      <svg
        viewBox="0 0 900 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
        style={{
          width: '100%',
          height: '100%',
          overflow: 'visible',
        }}
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="6"
            markerHeight="6"
            refX="4"
            refY="3"
            orient="auto"
          >
            <polygon
              points="0 0, 6 3, 0 6"
              fill="var(--flow-line)"
            />
          </marker>
        </defs>

        {/* Path to Builder A (Left Curve) */}
        <path
          d="M 450 0 C 450 28, 150 20, 150 58"
          stroke="var(--flow-line)"
          strokeWidth="2"
          strokeDasharray={isFlowing ? '6 6' : 'none'}
          className={isFlowing ? 'animate-flow' : ''}
          markerEnd="url(#arrowhead)"
          opacity={isFlowing ? 1 : 0.6}
        />

        {/* Path to Builder B (Straight Center Down) */}
        <line
          x1="450"
          y1="0"
          x2="450"
          y2="58"
          stroke="var(--flow-line)"
          strokeWidth="2"
          strokeDasharray={isFlowing ? '6 6' : 'none'}
          className={isFlowing ? 'animate-flow' : ''}
          markerEnd="url(#arrowhead)"
          opacity={isFlowing ? 1 : 0.6}
        />

        {/* Path to Builder C (Right Curve) */}
        <path
          d="M 450 0 C 450 28, 750 20, 750 58"
          stroke="var(--flow-line)"
          strokeWidth="2"
          strokeDasharray={isFlowing ? '6 6' : 'none'}
          className={isFlowing ? 'animate-flow' : ''}
          markerEnd="url(#arrowhead)"
          opacity={isFlowing ? 1 : 0.6}
        />
      </svg>
    </div>
  );
};
