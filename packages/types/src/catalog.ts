export interface Catalog {
  id: string;
  tenant_id: string;
  seller_id: string;
  name: string;
  description?: string;
  status: 'DRAFT' | 'ACTIVE' | 'INACTIVE';
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: string;
  tenant_id: string;
  catalog_id: string;
  parent_id?: string;
  name: string;
  slug: string;
  description?: string;
  image_url?: string;
  sort_order: number;
  status: 'ACTIVE' | 'INACTIVE';
  created_at: string;
  updated_at: string;
}

export interface Service {
  id: string;
  tenant_id: string;
  catalog_id: string;
  category_id?: string;
  name: string;
  slug: string;
  description?: string;
  short_description?: string;
  service_type: string;
  sort_order: number;
  image_url?: string;
  status: 'ACTIVE' | 'INACTIVE';
  created_at: string;
  updated_at: string;
}

export interface ServiceItem {
  id: string;
  tenant_id: string;
  service_id: string;
  name: string;
  code?: string;
  description?: string;
  unit_type: string;
  sort_order: number;
  status: 'ACTIVE' | 'INACTIVE';
  created_at: string;
  updated_at: string;
}

export interface ServiceAddon {
  id: string;
  tenant_id: string;
  service_id: string;
  name: string;
  code?: string;
  description?: string;
  sort_order: number;
  status: 'ACTIVE' | 'INACTIVE';
  created_at: string;
  updated_at: string;
}
