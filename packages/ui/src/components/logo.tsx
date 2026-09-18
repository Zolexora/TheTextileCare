import * as React from 'react';

export type LogoVariant = 'full' | 'mark' | 'symbol' | 'icon';
export type LogoTheme = 'light' | 'dark';

export interface LogoProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  variant?: LogoVariant;
  theme?: LogoTheme;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | number;
}

const SIZE_MAP: Record<'xs' | 'sm' | 'md' | 'lg' | 'xl', number> = {
  xs: 24,
  sm: 32,
  md: 48,
  lg: 64,
  xl: 96,
};

export function Logo({
  variant = 'full',
  theme = 'light',
  size,
  width,
  height,
  className = '',
  style,
  ...props
}: LogoProps) {
  let computedHeight = height;
  if (size) {
    computedHeight = typeof size === 'number' ? size : SIZE_MAP[size];
  }

  // Next.js standard public directory mapping
  const src = variant === 'icon' 
    ? '/icon.svg' 
    : theme === 'dark' 
      ? '/logo-white.svg' 
      : '/logo.svg';

  return (
    <img
      src={src}
      alt="The Textile Care"
      height={computedHeight}
      width={width}
      className={className}
      style={style}
      {...props}
    />
  );
}

export function LogoIcon(props: Omit<LogoProps, 'variant'>) {
  return <Logo variant="icon" {...props} />;
}
