/**
 * Phase 6 — Customer Types for TTC.
 */

export interface CustomerAddressCreate {
  label?: string | null;
  recipient_name?: string | null;
  phone?: string | null;
  address_line_1: string;
  address_line_2?: string | null;
  locality?: string | null;
  city: string;
  state: string;
  postal_code: string;
  country?: string;
  latitude?: number | null;
  longitude?: number | null;
  is_default?: boolean;
}

export interface CustomerAddressUpdate extends Partial<CustomerAddressCreate> {}

export interface CustomerAddress {
  id: string;
  label: string | null;
  recipient_name: string | null;
  phone: string | null;
  address_line_1: string;
  address_line_2: string | null;
  locality: string | null;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  latitude: number | null;
  longitude: number | null;
  is_default: boolean;
}

export interface CustomerProfileUpdate {
  display_name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  email?: string | null;
}

export interface CustomerProfile {
  id: string;
  display_name: string | null;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  email: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CustomerSellerLink {
  id: string;
  seller_id: string;
  status: string;
  first_interaction_at: string;
  last_interaction_at: string;
}
