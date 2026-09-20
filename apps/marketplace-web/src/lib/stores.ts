/**
 * Zustand stores for lightweight cross-screen state.
 *
 * Rules:
 *  - Server data (sellers, services, pricing) stays in TanStack Query.
 *  - Zustand holds only: cart context, location context, customer preferences,
 *    checkout temporary state, and UI preferences.
 *  - Stores are persisted to localStorage where appropriate.
 */

import { create } from 'zustand';
import { persist, subscribeWithSelector } from 'zustand/middleware';
import type { CustomerAddress } from '@ttc/types';

// ---------------------------------------------------------------------------
// Location store
// ---------------------------------------------------------------------------

export interface LocationState {
  /** GPS coordinates if available */
  coords: { latitude: number; longitude: number } | null;
  /** Pincode selected by user */
  pincode: string | null;
  /** Post office / locality */
  locality: string | null;
  /** City resolved from pincode */
  city: string | null;
  /** State resolved from pincode */
  state: string | null;
  /** Selected saved address ID (overrides raw coords/pincode) */
  selectedAddressId: string | null;
  /** Whether user has explicitly set a location */
  isSet: boolean;

  setCoords: (coords: { latitude: number; longitude: number }) => void;
  setPincode: (pincode: string, locality?: string, city?: string, state?: string) => void;
  setSelectedAddress: (address: CustomerAddress) => void;
  clearLocation: () => void;
}

export const useLocationStore = create<LocationState>()(
  persist(
    (set) => ({
      coords: null,
      pincode: null,
      locality: null,
      city: null,
      state: null,
      selectedAddressId: null,
      isSet: false,

      setCoords: (coords) => set({ coords, isSet: true }),
      setPincode: (pincode, locality, city, state) =>
        set({ pincode, locality: locality ?? null, city: city ?? null, state: state ?? null, isSet: true }),
      setSelectedAddress: (address) =>
        set({
          selectedAddressId: address.id,
          pincode: address.postal_code,
          locality: address.locality,
          city: address.city,
          state: address.state,
          coords: address.latitude && address.longitude
            ? { latitude: address.latitude, longitude: address.longitude }
            : null,
          isSet: true,
        }),
      clearLocation: () =>
        set({
          coords: null,
          pincode: null,
          locality: null,
          city: null,
          state: null,
          selectedAddressId: null,
          isSet: false,
        }),
    }),
    { name: 'ttc-location' }
  )
);

// ---------------------------------------------------------------------------
// Cart store
// ---------------------------------------------------------------------------

export interface CartAddon {
  id: string;
  name: string;
  quantity: number;
  unit_price: string;
}

export interface CartItem {
  /** Unique key per line item */
  key: string;
  service_id: string;
  service_name: string;
  service_item_id?: string;
  service_item_name?: string;
  quantity: number;
  weight?: string;
  unit_type: string;
  unit_price: string;
  addons: CartAddon[];
  /** Seller this item belongs to */
  seller_id: string;
  seller_name: string;
  branch_id: string;
  /** Instructions from customer */
  instructions?: string;
  /** Selected turnaround option key */
  turnaround_key?: string;
}

export interface CartStore {
  items: CartItem[];
  /** Coupon codes keyed by seller_id */
  coupons: Record<string, string>;

  addItem: (item: CartItem) => void;
  removeItem: (key: string) => void;
  updateItem: (key: string, patch: Partial<CartItem>) => void;
  clearSellerItems: (seller_id: string) => void;
  clearCart: () => void;
  applyCoupon: (seller_id: string, code: string) => void;
  removeCoupon: (seller_id: string) => void;
  /** Merge a guest cart into the authenticated cart items */
  mergeGuestItems: (guestItems: CartItem[]) => void;

  // Selectors
  getSellerIds: () => string[];
  getItemsBySeller: (seller_id: string) => CartItem[];
  getTotalItemCount: () => number;
}

export const useCartStore = create<CartStore>()(
  persist(
    subscribeWithSelector((set, get) => ({
      items: [],
      coupons: {},

      addItem: (item) =>
        set((s) => {
          const existing = s.items.findIndex((i) => i.key === item.key);
          if (existing >= 0) {
            const updated = [...s.items];
            const prev = updated[existing]!;
            updated[existing] = { ...prev, quantity: prev.quantity + item.quantity };
            return { items: updated };
          }
          return { items: [...s.items, item] };
        }),

      removeItem: (key) =>
        set((s) => ({ items: s.items.filter((i) => i.key !== key) })),

      updateItem: (key, patch) =>
        set((s) => ({
          items: s.items.map((i) => (i.key === key ? { ...i, ...patch } : i)),
        })),

      clearSellerItems: (seller_id) =>
        set((s) => ({ items: s.items.filter((i) => i.seller_id !== seller_id) })),

      clearCart: () => set({ items: [], coupons: {} }),

      applyCoupon: (seller_id, code) =>
        set((s) => ({ coupons: { ...s.coupons, [seller_id]: code } })),

      removeCoupon: (seller_id) =>
        set((s) => {
          const c = { ...s.coupons };
          delete c[seller_id];
          return { coupons: c };
        }),

      mergeGuestItems: (guestItems) =>
        set((s) => {
          const merged = [...s.items];
          for (const gi of guestItems) {
            const existing = merged.findIndex((i) => i.key === gi.key);
            if (existing >= 0) {
              const prev = merged[existing]!;
              merged[existing] = { ...prev, quantity: prev.quantity + gi.quantity };
            } else {
              merged.push(gi);
            }
          }
          return { items: merged };
        }),

      getSellerIds: () => [...new Set(get().items.map((i) => i.seller_id))],
      getItemsBySeller: (seller_id) => get().items.filter((i) => i.seller_id === seller_id),
      getTotalItemCount: () => get().items.reduce((sum, i) => sum + i.quantity, 0),
    })),
    { name: 'ttc-cart' }
  )
);

// ---------------------------------------------------------------------------
// UI preferences store
// ---------------------------------------------------------------------------

export interface UIPreferencesStore {
  theme: 'light' | 'dark' | 'system';
  locale: string;
  currency: string;
  setTheme: (t: 'light' | 'dark' | 'system') => void;
  setLocale: (l: string) => void;
  setCurrency: (c: string) => void;
}

export const useUIPreferencesStore = create<UIPreferencesStore>()(
  persist(
    (set) => ({
      theme: 'system',
      locale: 'en-IN',
      currency: 'INR',
      setTheme: (theme) => set({ theme }),
      setLocale: (locale) => set({ locale }),
      setCurrency: (currency) => set({ currency }),
    }),
    { name: 'ttc-ui-prefs' }
  )
);

// ---------------------------------------------------------------------------
// Checkout context store (ephemeral — not persisted to localStorage)
// ---------------------------------------------------------------------------

export interface CheckoutStore {
  /** Address ID selected for this checkout */
  addressId: string | null;
  /** Pickup slot selections keyed by seller_id */
  pickupSlots: Record<string, { date: string; slot_id: string; label: string }>;
  /** Delivery slot selections keyed by seller_id */
  deliverySlots: Record<string, { date: string; slot_id: string; label: string }>;
  /** Turnaround selections keyed by seller_id */
  turnaroundKeys: Record<string, string>;
  /** Notes keyed by seller_id */
  notes: Record<string, string>;
  /** Whether a revalidation is needed before proceeding to payment */
  needsRevalidation: boolean;

  setAddressId: (id: string) => void;
  setPickupSlot: (seller_id: string, slot: { date: string; slot_id: string; label: string }) => void;
  setDeliverySlot: (seller_id: string, slot: { date: string; slot_id: string; label: string }) => void;
  setTurnaroundKey: (seller_id: string, key: string) => void;
  setNotes: (seller_id: string, notes: string) => void;
  setNeedsRevalidation: (v: boolean) => void;
  resetCheckout: () => void;
}



export const useCheckoutStore = create<CheckoutStore>()((set) => ({
  addressId: null,
  pickupSlots: {},
  deliverySlots: {},
  turnaroundKeys: {},
  notes: {},
  needsRevalidation: false,

  setAddressId: (id) => set({ addressId: id }),
  setPickupSlot: (seller_id, slot) =>
    set((s) => ({ pickupSlots: { ...s.pickupSlots, [seller_id]: slot } })),
  setDeliverySlot: (seller_id, slot) =>
    set((s) => ({ deliverySlots: { ...s.deliverySlots, [seller_id]: slot } })),
  setTurnaroundKey: (seller_id, key) =>
    set((s) => ({ turnaroundKeys: { ...s.turnaroundKeys, [seller_id]: key } })),
  setNotes: (seller_id, notes) =>
    set((s) => ({ notes: { ...s.notes, [seller_id]: notes } })),
  setNeedsRevalidation: (v) => set({ needsRevalidation: v }),
  resetCheckout: () =>
    set({
      addressId: null,
      pickupSlots: {},
      deliverySlots: {},
      turnaroundKeys: {},
      notes: {},
      needsRevalidation: false,
    }),
}));
