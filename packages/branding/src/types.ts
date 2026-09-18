export interface BrandTheme {
  primaryColor: string;
  secondaryColor: string;
  accentColor?: string;
  fontFamily?: string;
}

export interface BrandAssets {
  logo?: string;
  logoWhite?: string;
  logoMark?: string;
  symbol?: string;
  icon?: string;
  favicon?: string;
  appleTouchIcon?: string;
  svgLogo?: string;
  svgIcon?: string;
  svgSymbol?: string;
  manifest?: string;
  banner?: string;
}

export interface BrandConfiguration {
  name: string;
  theme: BrandTheme;
  assets: BrandAssets;
}

export interface FeatureConfig {
  features: Record<string, boolean>;
}

export interface TenantConfiguration extends BrandConfiguration, FeatureConfig {
  tenantId: string;
}
