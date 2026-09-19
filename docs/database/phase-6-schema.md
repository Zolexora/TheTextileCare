# Phase 6 Schema

## Customer Schema

```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES users(id),
    display_name VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE customer_addresses (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(id),
    address_line_1 VARCHAR(255) NOT NULL,
    address_line_2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(50) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE customer_sellers (
    id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(id),
    seller_id UUID NOT NULL REFERENCES sellers(id),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    UNIQUE (customer_id, seller_id)
);
```

## Seller Discoverability

```sql
ALTER TABLE sellers ADD COLUMN marketplace_status VARCHAR(50) NOT NULL DEFAULT 'DRAFT';
ALTER TABLE seller_branches ADD COLUMN is_marketplace_visible BOOLEAN NOT NULL DEFAULT TRUE;
```
