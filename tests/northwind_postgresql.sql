-- PostgreSQL Schema: Northwind (Relational Model)
-- 8 tables, 69 fields, 8 FK relationships (including 1 self-reference)
-- Adapted from the classic Northwind database for SMEL migration testing
-- Tests: multi-table FK chains, self-reference, composite PK, various data types

-- Table 1: categories (product categories)
CREATE TABLE categories (
    category_id VARCHAR(255) PRIMARY KEY,
    category_name VARCHAR(255),
    description VARCHAR(255)
);

-- Table 2: suppliers (product suppliers with flattened address)
CREATE TABLE suppliers (
    supplier_id VARCHAR(255) PRIMARY KEY,
    company_name VARCHAR(255),
    contact_name VARCHAR(255),
    contact_title VARCHAR(255),
    phone VARCHAR(255),
    fax VARCHAR(255),
    street VARCHAR(255),
    city VARCHAR(255),
    region VARCHAR(255),
    postal_code VARCHAR(255),
    country VARCHAR(255)
);

-- Table 3: shippers (shipping companies)
CREATE TABLE shippers (
    shipper_id VARCHAR(255) PRIMARY KEY,
    company_name VARCHAR(255),
    phone VARCHAR(255)
);

-- Table 4: employees (with self-reference reports_to)
-- SMEL tests: TRANSFORM self-reference, SPLIT employee fields
CREATE TABLE employees (
    employee_id VARCHAR(255) PRIMARY KEY,
    last_name VARCHAR(255),
    first_name VARCHAR(255),
    title VARCHAR(255),
    birth_date DATE,
    hire_date DATE,
    phone VARCHAR(255),
    notes VARCHAR(255),
    street VARCHAR(255),
    city VARCHAR(255),
    region VARCHAR(255),
    postal_code VARCHAR(255),
    country VARCHAR(255),
    reports_to VARCHAR(255) REFERENCES employees(employee_id)
);

-- Table 5: customers (with flattened address)
CREATE TABLE customers (
    customer_id VARCHAR(255) PRIMARY KEY,
    company_name VARCHAR(255),
    contact_name VARCHAR(255),
    contact_title VARCHAR(255),
    phone VARCHAR(255),
    fax VARCHAR(255),
    street VARCHAR(255),
    city VARCHAR(255),
    region VARCHAR(255),
    postal_code VARCHAR(255),
    country VARCHAR(255)
);

-- Table 6: products (FK to suppliers and categories)
-- SMEL tests: NEST product+supplier, NEST product+category
CREATE TABLE products (
    product_id VARCHAR(255) PRIMARY KEY,
    product_name VARCHAR(255),
    unit_price DOUBLE PRECISION,
    units_in_stock INTEGER,
    discontinued BOOLEAN,
    quantity_per_unit VARCHAR(255),
    supplier_id VARCHAR(255) NOT NULL REFERENCES suppliers(supplier_id),
    category_id VARCHAR(255) NOT NULL REFERENCES categories(category_id)
);

-- Table 7: orders (FK to customers, employees, shippers)
-- SMEL tests: NEST order+customer, NEST order+employee, NEST order+shipper
CREATE TABLE orders (
    order_id VARCHAR(255) PRIMARY KEY,
    order_date DATE,
    required_date DATE,
    shipped_date DATE,
    freight DOUBLE PRECISION,
    ship_name VARCHAR(255),
    ship_address VARCHAR(255),
    ship_city VARCHAR(255),
    ship_region VARCHAR(255),
    ship_postal_code VARCHAR(255),
    ship_country VARCHAR(255),
    customer_id VARCHAR(255) NOT NULL REFERENCES customers(customer_id),
    employee_id VARCHAR(255) NOT NULL REFERENCES employees(employee_id),
    shipper_id VARCHAR(255) NOT NULL REFERENCES shippers(shipper_id)
);

-- Table 8: order_details (composite PK, FK to orders and products)
-- Each row links an order to a product with quantity and pricing
-- SMEL tests: NEST order_details into orders, composite PK handling
CREATE TABLE order_details (
    order_id VARCHAR(255) NOT NULL REFERENCES orders(order_id),
    product_id VARCHAR(255) NOT NULL REFERENCES products(product_id),
    unit_price DOUBLE PRECISION,
    quantity INTEGER,
    discount DOUBLE PRECISION,
    PRIMARY KEY (order_id, product_id)
);
