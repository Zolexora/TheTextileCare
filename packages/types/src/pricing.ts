/**
 * Phase 5 — Pricing Engine TypeScript types for TTC.
 * Shared across seller-web, seller-mobile, marketplace-web, marketplace-mobile.
 */

export type PriceBookScope = 'PLATFORM_DEFAULT' | 'SELLER' | 'BRANCH';
export type PriceBookStatus = 'DRAFT' | 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';
export type PriceRuleType = 'FIXED' | 'PER_ITEM' | 'PER_UNIT' | 'PER_WEIGHT';
export type ComponentType = 'BASE_PRICE' | 'SURCHARGE' | 'DISCOUNT' | 'TAX';
export type RateType = 'FLAT' | 'PERCENTAGE';

export interface PriceBook {
  id: string;
  tenant_id: string | null;
  seller_id: string | null;
  branch_id: string | null;
  name: string;
  description?: string;
  scope: PriceBookScope;
  status: PriceBookStatus;
  currency: string;
  priority: number;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PriceRule {
  id: string;
  tenant_id: string | null;
  price_book_id: string;
  name?: string;
  description?: string;
  service_id?: string;
  service_item_id?: string;
  service_addon_id?: string;
  rule_type: PriceRuleType;
  component_type: ComponentType;
  rate_type: RateType;
  /** Stored as string to preserve Decimal precision */
  rate: string;
  status: string;
  is_active: boolean;
  priority: number;
  effective_from?: string;
  effective_to?: string;
  created_at: string;
  updated_at: string;
}

export interface PricingCalculationItemRequest {
  service_id: string;
  service_item_id?: string;
  quantity: string;
  weight?: string;
  unit_type?: string;
  addon_ids?: string[];
}

export interface PricingCalculationRequest {
  seller_id: string;
  branch_id?: string;
  currency?: string;
  calculation_time?: string;
  items: PricingCalculationItemRequest[];
}

export interface PricingCalculationComponentBreakdown {
  name: string;
  component_type: ComponentType;
  rate_type: RateType;
  /** Decimal string */
  rate: string;
  /** Decimal string */
  amount: string;
}

export interface PricingCalculationItemResult {
  service_id: string;
  service_item_id?: string;
  /** Decimal strings */
  unit_price: string;
  quantity: string;
  weight?: string;
  base_price: string;
  surcharges: string;
  discounts: string;
  tax: string;
  subtotal: string;
  total: string;
  applied_rule_ids: string[];
  breakdown: PricingCalculationComponentBreakdown[];
}

export interface PricingCalculationResult {
  currency: string;
  /** All monetary values are Decimal strings */
  subtotal: string;
  total_surcharges: string;
  total_discounts: string;
  total_tax: string;
  grand_total: string;
  items: PricingCalculationItemResult[];
}
