import * as React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'secondary' | 'outline';
}

export function Button({ variant = 'default', className = '', children, ...props }: ButtonProps) {
  const variantClassName = {
    default: 'bg-slate-900 text-white hover:bg-slate-700',
    secondary: 'bg-slate-100 text-slate-900 hover:bg-slate-200',
    outline: 'border border-slate-300 bg-white text-slate-900 hover:bg-slate-50',
  }[variant];

  return (
    <button
      className={['inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors', variantClassName, className].join(' ')}
      {...props}
    >
      {children}
    </button>
  );
}
