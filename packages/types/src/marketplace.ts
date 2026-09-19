/**
 * Phase 6 — Marketplace Types for TTC.
 */

export interface MarketplaceSeller {
  id: string;
  business_name: string;
  display_name: string | null;
  slug: string;
  description: string | null;
  logo_url: string | null;
}

export interface MarketplaceBranch {
  id: string;
  seller_id: string;
  name: string;
  phone: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface MarketplaceCategory {
  id: string;
  parent_id: string | null;
  name: string;
  description: string | null;
  image_url: string | null;
}

export interface MarketplaceServiceItem {
  id: string;
  name: string;
  description: string | null;
  image_url: string | null;
}

export interface MarketplaceServiceAddon {
  id: string;
  name: string;
  description: string | null;
}

export interface MarketplaceService {
  id: string;
  category_id: string;
  name: string;
  description: string | null;
  image_url: string | null;
  is_per_weight: boolean;
  is_per_item: boolean;
  is_per_unit: boolean;
  
  items: MarketplaceServiceItem[];
  addons: MarketplaceServiceAddon[];
}
