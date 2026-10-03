import React from 'react';

export interface PageContainerProps {
  children: React.ReactNode;
  maxWidth?: string;
}

export const PageContainer: React.FC<PageContainerProps> = ({
  children,
  maxWidth = '1120px',
}) => {
  return (
    <main
      style={{
        flex: 1,
        width: '100%',
        maxWidth,
        margin: '0 auto',
        padding: '36px 24px 64px 24px',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {children}
    </main>
  );
};
