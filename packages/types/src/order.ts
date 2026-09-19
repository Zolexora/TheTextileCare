export type OrderStatus = 'DRAFT' | 'PENDING' | 'CONFIRMED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';

export interface CatalogSnapshot {
  items: Array<{
    service_id: string;
    service_name: string;
    service_item_name?: string;
    unit_type: string;
    addons: Array<{
      addon_id: string;
      addon_name: string;
    }>;
  }>;
}

export interface PricingSnapshot {
  currency: string;
  subtotal: string;
  total_surcharges: string;
  total_discounts: string;
  total_tax: string;
  grand_total: string;
  items: Array<any>;
}

export interface CustomerSnapshot {
  customer_id: string;
  display_name?: string;
  phone?: string;
  email?: string;
}

export interface AddressSnapshot {
  recipient_name?: string;
  phone?: string;
  address_line_1: string;
  address_line_2?: string;
  locality?: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface OrderItemAddonRequest {
  service_addon_id: string;
  quantity: string;
}

export interface OrderItemRequest {
  service_id: string;
  service_item_id?: string;
  quantity: string;
  weight?: string;
  unit_type: string;
  addons: OrderItemAddonRequest[];
}

export interface OrderCreateRequest {
  seller_id: string;
  branch_id: string;
  currency: string;
  items: OrderItemRequest[];
  customer_address_id?: string;
  previewed_grand_total?: string;
  notes?: string;
}

export interface OrderCancelRequest {
  cancellation_reason: string;
}

export interface OrderAddonResponse {
  id: string;
  service_addon_id?: string;
  addon_name_snapshot: string;
  quantity: string;
  unit_price: string;
  subtotal: string;
  discount_amount: string;
  surcharge_amount: string;
  tax_amount: string;
  total_amount: string;
}

export interface OrderItemResponse {
  id: string;
  service_id?: string;
  service_item_id?: string;
  service_name_snapshot: string;
  service_item_name_snapshot?: string;
  unit_type: string;
  quantity: string;
  unit_price: string;
  subtotal: string;
  discount_amount: string;
  surcharge_amount: string;
  tax_amount: string;
  total_amount: string;
  addons: OrderAddonResponse[];
}

export interface OrderStatusHistoryResponse {
  id: string;
  from_status?: string;
  to_status: string;
  reason?: string;
  created_at: string;
}

export interface OrderResponse {
  id: string;
  order_number: string;
  status: OrderStatus;
  currency: string;
  
  subtotal: string;
  discount_total: string;
  surcharge_total: string;
  tax_total: string;
  grand_total: string;
  
  seller_id: string;
  branch_id: string;
  customer_id: string;
  
  pricing_snapshot: PricingSnapshot;
  catalog_snapshot: CatalogSnapshot;
  customer_snapshot: CustomerSnapshot;
  customer_address_snapshot?: AddressSnapshot;
  
  placed_at: string;
  confirmed_at?: string;
  completed_at?: string;
  cancelled_at?: string;
  cancellation_reason?: string;
  
  created_at: string;
  updated_at: string;
  
  items: OrderItemResponse[];
  status_history: OrderStatusHistoryResponse[];
}

export interface OrderListItem {
  id: string;
  order_number: string;
  status: OrderStatus;
  currency: string;
  grand_total: string;
  seller_id: string;
  branch_id: string;
  customer_id: string;
  placed_at: string;
  created_at: string;
  items_count: number;
}

export interface OrderListResponse {
  items: OrderListItem[];
  total: number;
  limit: number;
  offset: number;
}
