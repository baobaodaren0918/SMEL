-- Cassandra Schema: Northwind (Wide-column model for SMILE testing)
-- 8 tables with partition and clustering keys
-- Query-driven denormalized design with address fields flattened
-- Tests: partition/clustering keys, denormalized query tables

-- Table 1: categories (partition: category_id)
CREATE TABLE categories (
    category_id TEXT,
    category_name TEXT,
    description TEXT,
    PRIMARY KEY (category_id)
);

-- Table 2: suppliers (partition: supplier_id)
CREATE TABLE suppliers (
    supplier_id TEXT,
    company_name TEXT,
    contact_name TEXT,
    contact_title TEXT,
    phone TEXT,
    fax TEXT,
    street TEXT,
    city TEXT,
    region TEXT,
    postal_code TEXT,
    country TEXT,
    PRIMARY KEY (supplier_id)
);

-- Table 3: shippers (partition: shipper_id)
CREATE TABLE shippers (
    shipper_id TEXT,
    company_name TEXT,
    phone TEXT,
    PRIMARY KEY (shipper_id)
);

-- Table 4: employees (partition: employee_id)
CREATE TABLE employees (
    employee_id TEXT,
    last_name TEXT,
    first_name TEXT,
    title TEXT,
    birth_date DATE,
    hire_date DATE,
    phone TEXT,
    notes TEXT,
    street TEXT,
    city TEXT,
    region TEXT,
    postal_code TEXT,
    country TEXT,
    reports_to TEXT,
    PRIMARY KEY (employee_id)
);

-- Table 5: customers (partition: customer_id)
CREATE TABLE customers (
    customer_id TEXT,
    company_name TEXT,
    contact_name TEXT,
    contact_title TEXT,
    phone TEXT,
    fax TEXT,
    street TEXT,
    city TEXT,
    region TEXT,
    postal_code TEXT,
    country TEXT,
    PRIMARY KEY (customer_id)
);

-- Table 6: products (partition: category_id + supplier_id, clustering: product_id)
CREATE TABLE products (
    category_id TEXT,
    supplier_id TEXT,
    product_id TEXT,
    product_name TEXT,
    unit_price DOUBLE,
    units_in_stock INT,
    discontinued BOOLEAN,
    quantity_per_unit TEXT,
    PRIMARY KEY ((category_id, supplier_id), product_id)
);

-- Table 7: orders (partition: customer_id, clustering: order_date + order_id)
CREATE TABLE orders (
    customer_id TEXT,
    order_date DATE,
    order_id TEXT,
    required_date DATE,
    shipped_date DATE,
    freight DOUBLE,
    ship_name TEXT,
    ship_address TEXT,
    ship_city TEXT,
    ship_region TEXT,
    ship_postal_code TEXT,
    ship_country TEXT,
    employee_id TEXT,                   -- logically NOT NULL (FK in PG), CQL cannot enforce
    shipper_id TEXT,                    -- logically NOT NULL (FK in PG), CQL cannot enforce
    PRIMARY KEY ((customer_id), order_date, order_id)
);

-- Table 8: order_details (partition: order_id + product_id)
CREATE TABLE order_details (
    order_id TEXT,
    product_id TEXT,
    unit_price DOUBLE,
    quantity INT,
    discount DOUBLE,
    PRIMARY KEY ((order_id, product_id))
);
