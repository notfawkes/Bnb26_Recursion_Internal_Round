import React from 'react';
import { BuilderCard } from './BuilderCard';
import type { BuilderData, BuilderId } from '../../types';

export interface BuilderGridProps {
  builders: BuilderData[];
  onSelectBuilder: (builder: BuilderData) => void;
  mismatchedBuilders?: BuilderId[];
}

export const BuilderGrid: React.FC<BuilderGridProps> = ({
  builders,
  onSelectBuilder,
  mismatchedBuilders = [],
}) => {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '20px',
        width: '100%',
        marginBottom: '32px',
      }}
    >
      {builders.map((builder) => {
        const isMismatch = mismatchedBuilders.includes(builder.id);
        return (
          <BuilderCard
            key={builder.id}
            builder={builder}
            onClick={onSelectBuilder}
            isMismatch={isMismatch}
          />
        );
      })}
    </div>
  );
};
