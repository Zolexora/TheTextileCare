import * as React from 'react';

export function Card({ className = '', children }: { className?: string; children: React.ReactNode }) {
  return <div className={['rounded-xl border border-slate-200 bg-white p-6 shadow-sm', className].join(' ')}>{children}</div>;
}
