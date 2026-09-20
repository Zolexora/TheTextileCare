/**
 * TanStack Query hooks for marketplace data.
 *
 * Rules:
 *  - These hooks own all server-state fetching and caching.
 *  - Business logic stays backend-authoritative; hooks only fetch and cache.
 *  - Keys are stable and reusable across the app.
 */

'use client';

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query';
import { useAuth } from './auth-context';
import * as api from './api';
import { useLocationStore } from './stores';
import type {
  CustomerProfile,
  CustomerAddress,
  CustomerAddressCreate,
  CustomerAddressUpdate,
  PricingCalculationRequest,
  OrderCreateRequest,
} from '@ttc/types';

// ---------------------------------------------------------------------------
// Query keys — centralised for cache invalidation consistency
// ---------------------------------------------------------------------------

export const qk = {
  profile: ['profile'] as const,
  addresses: ['addresses'] as const,
  address: (id: string) => ['address', id] as const,
  sellers: (params: api.SellerSearchParams) => ['sellers', params] as const,
  seller: (id: string) => ['seller', id] as const,
  categories: ['categories'] as const,
  services: (params: { category_id?: string; seller_id?: string }) =>
    ['services', params] as const,
  service: (id: string) => ['service', id] as const,
  serviceability: (params: api.ServiceabilityRequest) =>
    ['serviceability', params] as const,
  pricing: (body: PricingCalculationRequest) => ['pricing', body] as const,
  orders: (params: { limit?: number; offset?: number; status?: string }) =>
    ['orders', params] as const,
  order: (id: string) => ['order', id] as const,
} as const;

// ---------------------------------------------------------------------------
// Auth-aware fetch helper
// ---------------------------------------------------------------------------

function useToken(): string | null {
  const { token } = useAuth();
  return token;
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------

export function useProfile(opts?: Partial<UseQueryOptions<CustomerProfile>>) {
  const token = useToken();
  return useQuery<CustomerProfile>({
    queryKey: qk.profile,
    queryFn: () => api.getCustomerProfile(token!),
    enabled: !!token,
    staleTime: 5 * 60_000,
    ...opts,
  });
}

export function useUpdateProfile() {
  const token = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.updateCustomerProfile>[0]) =>
      api.updateCustomerProfile(body, token!),
    onSuccess: (data) => qc.setQueryData(qk.profile, data),
  });
}

// ---------------------------------------------------------------------------
// Addresses
// ---------------------------------------------------------------------------

export function useAddresses() {
  const token = useToken();
  return useQuery<CustomerAddress[]>({
    queryKey: qk.addresses,
    queryFn: () => api.getAddresses(token!),
    enabled: !!token,
    staleTime: 2 * 60_000,
  });
}

export function useCreateAddress() {
  const token = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CustomerAddressCreate) => api.createAddress(body, token!),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.addresses }),
  });
}

export function useUpdateAddress() {
  const token = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CustomerAddressUpdate }) =>
      api.updateAddress(id, body, token!),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.addresses }),
  });
}

export function useDeleteAddress() {
  const token = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteAddress(id, token!),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.addresses }),
  });
}

// ---------------------------------------------------------------------------
// Serviceability
// ---------------------------------------------------------------------------

export function useServiceability() {
  const token = useToken();
  const { coords, pincode, isSet } = useLocationStore();
  const params: api.ServiceabilityRequest = coords
    ? { latitude: coords.latitude, longitude: coords.longitude }
    : pincode
    ? { pincode }
    : {};

  return useQuery<api.ServiceabilityResult>({
    queryKey: qk.serviceability(params),
    queryFn: () => api.checkServiceability(params, token),
    enabled: isSet,
    staleTime: 5 * 60_000,
  });
}

// ---------------------------------------------------------------------------
// Sellers
// ---------------------------------------------------------------------------

export function useSellers(params: api.SellerSearchParams = {}) {
  const token = useToken();
  return useQuery<api.SellerListResponse>({
    queryKey: qk.sellers(params),
    queryFn: () => api.getMarketplaceSellers(params, token),
    staleTime: 2 * 60_000,
  });
}

export function useSeller(id: string) {
  const token = useToken();
  return useQuery({
    queryKey: qk.seller(id),
    queryFn: () => api.getMarketplaceSeller(id, token),
    enabled: !!id,
    staleTime: 5 * 60_000,
  });
}

// ---------------------------------------------------------------------------
// Categories & Services
// ---------------------------------------------------------------------------

export function useCategories() {
  return useQuery({
    queryKey: qk.categories,
    queryFn: () => api.getMarketplaceCategories(),
    staleTime: 10 * 60_000,
  });
}

export function useServices(params: { category_id?: string; seller_id?: string } = {}) {
  const token = useToken();
  return useQuery({
    queryKey: qk.services(params),
    queryFn: () => api.getMarketplaceServices(params, token),
    staleTime: 5 * 60_000,
  });
}

export function useService(id: string) {
  const token = useToken();
  return useQuery({
    queryKey: qk.service(id),
    queryFn: () => api.getMarketplaceService(id, token),
    enabled: !!id,
    staleTime: 5 * 60_000,
  });
}

// ---------------------------------------------------------------------------
// Pricing
// ---------------------------------------------------------------------------

export function usePricing(body: PricingCalculationRequest, enabled = true) {
  const token = useToken();
  return useQuery({
    queryKey: qk.pricing(body),
    queryFn: () => api.calculatePricing(body, token),
    enabled: enabled && body.items.length > 0,
    staleTime: 30_000,
  });
}

// ---------------------------------------------------------------------------
// Orders
// ---------------------------------------------------------------------------

export function useOrders(params: { limit?: number; offset?: number; status?: string } = {}) {
  const token = useToken();
  return useQuery({
    queryKey: qk.orders(params),
    queryFn: () => api.getOrders(params, token!),
    enabled: !!token,
  });
}

export function useOrder(id: string) {
  const token = useToken();
  return useQuery({
    queryKey: qk.order(id),
    queryFn: () => api.getOrder(id, token!),
    enabled: !!id && !!token,
    refetchInterval: (query) => {
      // Poll for active orders
      const data = query.state.data;
      if (!data) return false;
      const active = ['PENDING', 'CONFIRMED', 'IN_PROGRESS'];
      return active.includes(data.status) ? 30_000 : false;
    },
  });
}

export function useCreateOrder() {
  const token = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: OrderCreateRequest) => api.createOrder(body, token!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  });
}

export function useCancelOrder() {
  const token = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.cancelOrder(id, reason, token!),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: qk.order(id) });
      qc.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}
