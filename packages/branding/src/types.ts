export interface BrandTheme {
  primaryColor: string;
  secondaryColor: string;
  accentColor?: string;
  fontFamily?: string;
}

export interface BrandAssets {
  logo?: string;
  icon?: string;
  favicon?: string;
  banner?: string;
}

export interface BrandConfiguration {
  name: string;
  theme: BrandTheme;
  assets: BrandAssets;
}
