/**
 * Marketplace API client — wraps @ttc/api-client with auth token injection
 * and provides typed endpoint methods consumed by TanStack Query hooks.
 *
 * All business logic stays server-authoritative. The client only handles:
 *  - HTTP transport with auth headers
 *  - Request cancellation via AbortSignal
 *  - Typed request/response shapes from @ttc/types
 */

import { ApiClient, ApiClientError } from '@ttc/api-client';
import { getRuntimeConfig } from '@ttc/config';
import type {
  CustomerProfile,
  CustomerProfileUpdate,
  CustomerAddress,
  CustomerAddressCreate,
  CustomerAddressUpdate,
  MarketplaceSeller,
  MarketplaceService,
  MarketplaceCategory,
  PricingCalculationRequest,
  PricingCalculationResult,
  OrderCreateRequest,
  OrderResponse,
  OrderListResponse,
} from '@ttc/types';

export type { ApiClientError };

// ---------------------------------------------------------------------------
// Client factory — one instance per session, token provided at call time
// ---------------------------------------------------------------------------

let _client: ApiClient | null = null;

function getClient(): ApiClient {
  if (!_client) {
    const { apiBaseUrl } = getRuntimeConfig();
    _client = new ApiClient({ baseUrl: apiBaseUrl, timeoutMs: 30_000 });
  }
  return _client;
}

function authed(token?: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---------------------------------------------------------------------------
// Generic helpers
// ---------------------------------------------------------------------------

type Q = Record<string, string | number | boolean | null | undefined>;

function qs(params: Q): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v != null && v !== '') p.append(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : '';
}

// ---------------------------------------------------------------------------
// Marketplace discovery
// ---------------------------------------------------------------------------

export interface SellerSearchParams {
  pincode?: string;
  latitude?: number;
  longitude?: number;
  service_id?: string;
  category_id?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
}

export interface SellerListResponse {
  sellers: MarketplaceSeller[];
  total: number;
}

export async function getMarketplaceSellers(
  params: SellerSearchParams,
  token?: string | null
): Promise<SellerListResponse> {
  const raw = await getClient().request<any>(`/api/v1/marketplace/sellers${qs(params as Q)}`, {
    headers: authed(token),
  });
  if (Array.isArray(raw)) {
    return { sellers: raw, total: raw.length };
  }
  return raw;
}

export async function getMarketplaceSeller(
  sellerId: string,
  token?: string | null
): Promise<MarketplaceSeller> {
  return getClient().request<MarketplaceSeller>(`/api/v1/marketplace/sellers/${sellerId}`, {
    headers: authed(token),
  });
}

export async function getMarketplaceCategories(
  token?: string | null
): Promise<MarketplaceCategory[]> {
  // Global categories not yet supported by backend, mocking fallback
  return [
    { id: 'cat_1', name: 'Wash & Fold', slug: 'wash-and-fold', description: null, image_url: 'https://images.unsplash.com/photo-1545173168-9f1947eebb7f?auto=format&fit=crop&q=80&w=400', is_active: true, display_order: 1 },
    { id: 'cat_2', name: 'Dry Cleaning', slug: 'dry-cleaning', description: null, image_url: 'https://images.unsplash.com/photo-1582735689369-4fe89db7114c?auto=format&fit=crop&q=80&w=400', is_active: true, display_order: 2 },
  ] as MarketplaceCategory[];
}

export async function getMarketplaceServices(
  params: { category_id?: string; seller_id?: string },
  token?: string | null
): Promise<MarketplaceService[]> {
  return getClient().request<MarketplaceService[]>(`/api/v1/marketplace/services${qs(params as Q)}`, {
    headers: authed(token),
  });
}

export async function getMarketplaceService(
  serviceId: string,
  token?: string | null
): Promise<MarketplaceService> {
  return getClient().request<MarketplaceService>(`/api/v1/marketplace/services/${serviceId}`, {
    headers: authed(token),
  });
}

// ---------------------------------------------------------------------------
// Serviceability
// ---------------------------------------------------------------------------

export interface ServiceabilityRequest {
  pincode?: string;
  latitude?: number;
  longitude?: number;
}

export interface ServiceabilityResult {
  is_serviceable: boolean;
  eligible_sellers: string[];
  eligible_services: string[];
  message?: string;
}

export async function checkServiceability(
  params: ServiceabilityRequest,
  token?: string | null
): Promise<ServiceabilityResult> {
  return getClient().request<ServiceabilityResult>(
    `/api/v1/marketplace/serviceability${qs(params as Q)}`,
    { headers: authed(token) }
  );
}

// ---------------------------------------------------------------------------
// Pricing
// ---------------------------------------------------------------------------

export async function calculatePricing(
  body: PricingCalculationRequest,
  token?: string | null
): Promise<PricingCalculationResult> {
  return getClient().request<PricingCalculationResult>(`/api/v1/marketplace/pricing/calculate`, {
    method: 'POST',
    body,
    headers: authed(token),
  });
}

// ---------------------------------------------------------------------------
// Customer profile
// ---------------------------------------------------------------------------

export async function getCustomerProfile(token: string): Promise<CustomerProfile> {
  return getClient().request<CustomerProfile>(`/api/v1/customers/me`, {
    headers: authed(token),
  });
}

export async function updateCustomerProfile(
  body: CustomerProfileUpdate,
  token: string
): Promise<CustomerProfile> {
  return getClient().request<CustomerProfile>(`/api/v1/customers/me`, {
    method: 'PATCH',
    body,
    headers: authed(token),
  });
}

// ---------------------------------------------------------------------------
// Addresses
// ---------------------------------------------------------------------------

export async function getAddresses(token: string): Promise<CustomerAddress[]> {
  return getClient().request<CustomerAddress[]>(`/api/v1/customers/me/addresses`, {
    headers: authed(token),
  });
}

export async function createAddress(
  body: CustomerAddressCreate,
  token: string
): Promise<CustomerAddress> {
  return getClient().request<CustomerAddress>(`/api/v1/customers/me/addresses`, {
    method: 'POST',
    body,
    headers: authed(token),
  });
}

export async function updateAddress(
  id: string,
  body: CustomerAddressUpdate,
  token: string
): Promise<CustomerAddress> {
  return getClient().request<CustomerAddress>(`/api/v1/customers/me/addresses/${id}`, {
    method: 'PATCH',
    body,
    headers: authed(token),
  });
}

export async function deleteAddress(id: string, token: string): Promise<void> {
  return getClient().request<void>(`/api/v1/customers/me/addresses/${id}`, {
    method: 'DELETE',
    headers: authed(token),
  });
}

// ---------------------------------------------------------------------------
// Orders
// ---------------------------------------------------------------------------

export async function createOrder(body: OrderCreateRequest, token: string): Promise<OrderResponse> {
  return getClient().request<OrderResponse>(`/api/v1/orders`, {
    method: 'POST',
    body,
    headers: authed(token),
  });
}

export async function getOrders(
  params: { limit?: number; offset?: number; status?: string },
  token: string
): Promise<OrderListResponse> {
  return getClient().request<OrderListResponse>(`/api/v1/orders${qs(params as Q)}`, {
    headers: authed(token),
  });
}

export async function getOrder(id: string, token: string): Promise<OrderResponse> {
  return getClient().request<OrderResponse>(`/api/v1/orders/${id}`, {
    headers: authed(token),
  });
}

export async function cancelOrder(
  id: string,
  reason: string,
  token: string
): Promise<OrderResponse> {
  return getClient().request<OrderResponse>(`/api/v1/orders/${id}/cancel`, {
    method: 'POST',
    body: { cancellation_reason: reason },
    headers: authed(token),
  });
}
