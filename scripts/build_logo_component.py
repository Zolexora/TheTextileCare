import json

with open('scratch/assets/paths.json') as f:
    data = json.load(f)

wave_json = json.dumps(data['wave'], indent=2)
ttc_json = json.dumps(data['ttc'], indent=2)
sub_json = json.dumps(data['subtitle'], indent=2)
icon_json = json.dumps(data['icon'], indent=2)

template = '''import * as React from 'react';

const WAVE_PATHS: string[] = {wave};
const TTC_PATHS: string[] = {ttc};
const SUBTITLE_PATHS: string[] = {subtitle};
const ICON_PATHS: string[] = {icon};

export type LogoVariant = 'full' | 'mark' | 'symbol' | 'icon';
export type LogoTheme = 'light' | 'dark';

export interface LogoProps extends React.SVGAttributes<SVGSVGElement> {
  /**
   * - 'full': Logo mark + TTC + THE TEXTILE CARE (viewBox 0 0 813 285)
   * - 'mark': Logo mark + TTC without subtitle (viewBox 0 0 813 196)
   * - 'symbol': Flowing wave ribbons alone (viewBox 0 0 380 196)
   * - 'icon': Squircle app icon with white wave (viewBox 0 0 324 324)
   */
  variant?: LogoVariant;
  /**
   * - 'light': Dark navy text (#062B5F) for light backgrounds (default)
   * - 'dark': White text (#FFFFFF) for dark backgrounds
   */
  theme?: LogoTheme;
  /** Pre-configured height presets */
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
  const textColor = theme === 'dark' ? '#FFFFFF' : '#062B5F';
  const idSuffix = React.useId().replace(/:/g, '');
  const waveGradientId = `ttcWaveGrad_${idSuffix}`;
  const iconGradientId = `ttcIconGrad_${idSuffix}`;

  let viewBox = '0 0 813 285';
  let aspectRatio = 813 / 285;
  if (variant === 'mark') {
    viewBox = '0 0 813 196';
    aspectRatio = 813 / 196;
  } else if (variant === 'symbol') {
    viewBox = '0 0 380 196';
    aspectRatio = 380 / 196;
  } else if (variant === 'icon') {
    viewBox = '0 0 324 324';
    aspectRatio = 1;
  }

  let computedHeight = height;
  let computedWidth = width;
  if (size) {
    const numericHeight = typeof size === 'number' ? size : SIZE_MAP[size];
    computedHeight = numericHeight;
    if (!width) {
      computedWidth = Math.round(numericHeight * aspectRatio);
    }
  }

  if (variant === 'icon') {
    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 324 324"
        width={computedWidth || 48}
        height={computedHeight || 48}
        className={className}
        style={style}
        role="img"
        aria-label="The Textile Care Icon"
        {...props}
      >
        <defs>
          <linearGradient id={iconGradientId} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#0887F5" />
            <stop offset="100%" stopColor="#0C3ACF" />
          </linearGradient>
        </defs>
        <rect width="324" height="324" rx="72" fill={`url(#${iconGradientId})`} />
        <g transform="translate(0, 324) scale(0.025, -0.025)" stroke="none">
          {ICON_PATHS.map((d, i) => (
            <path key={i} d={d} fill="#FFFFFF" />
          ))}
        </g>
      </svg>
    );
  }

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={viewBox}
      width={computedWidth}
      height={computedHeight}
      className={className}
      style={style}
      role="img"
      aria-label="The Textile Care"
      {...props}
    >
      <defs>
        <linearGradient id={waveGradientId} x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#00A3FF" />
          <stop offset="40%" stopColor="#0084FF" />
          <stop offset="100%" stopColor="#0052CC" />
        </linearGradient>
      </defs>
      <g transform="translate(0, 285) scale(0.025, -0.025)" stroke="none">
        {/* Wave Ribbon (Cyan-to-blue gradient) */}
        {WAVE_PATHS.map((d, i) => (
          <path key={`wave-${i}`} d={d} fill={`url(#${waveGradientId})`} />
        ))}

        {/* TTC Letters */}
        {(variant === 'full' || variant === 'mark') &&
          TTC_PATHS.map((d, i) => (
            <path key={`ttc-${i}`} d={d} fill={textColor} />
          ))}

        {/* THE TEXTILE CARE Subtitle */}
        {variant === 'full' &&
          SUBTITLE_PATHS.map((d, i) => (
            <path key={`sub-${i}`} d={d} fill={textColor} />
          ))}
      </g>
    </svg>
  );
}

export function LogoIcon(props: Omit<LogoProps, 'variant'>) {
  return <Logo variant="icon" {...props} />;
}
'''

content = template.replace(
    '{wave}', wave_json
).replace(
    '{ttc}', ttc_json
).replace(
    '{subtitle}', sub_json
).replace(
    '{icon}', icon_json
)

with open('packages/ui/src/components/logo.tsx', 'w') as f:
    f.write(content)

print('Generated packages/ui/src/components/logo.tsx successfully!')
