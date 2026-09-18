import * as React from 'react';

export function Typography({ as: Component = 'p', className = '', children }: { as?: keyof JSX.IntrinsicElements; className?: string; children: React.ReactNode }) {
  return React.createElement(Component, { className: ['text-slate-700', className].join(' ') }, children);
}
