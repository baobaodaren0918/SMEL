-- PostgreSQL Schema: Northwind V2 (R2R Evolution Target)
-- 10 tables: 8 original - categories(MERGE) + customer_contacts(SPLIT) + region + territories + employee_territories

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

CREATE TABLE employees (
    employee_id VARCHAR(255) PRIMARY KEY,
    last_name VARCHAR(255),
    first_name VARCHAR(255),
    title VARCHAR(255),
    hire_date DATE,
    phone VARCHAR(255),
    street VARCHAR(255),
    city VARCHAR(255),
    region VARCHAR(255),
    postal_code VARCHAR(255),
    country VARCHAR(255),
    reports_to VARCHAR(255) REFERENCES employees(employee_id),
    email VARCHAR(255)
);

CREATE TABLE customers (
    customer_id VARCHAR(255) PRIMARY KEY,
    company_name VARCHAR(255),
    street VARCHAR(255),
    city VARCHAR(255),
    region VARCHAR(255),
    postal_code VARCHAR(255),
    country VARCHAR(255)
);

CREATE TABLE products (
    category_name VARCHAR(255),
    description VARCHAR(255),
    product_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    unit_price DOUBLE PRECISION,
    units_in_stock INTEGER,
    discontinued BOOLEAN,
    quantity_per_unit VARCHAR(255),
    supplier_id VARCHAR(255) NOT NULL REFERENCES suppliers(supplier_id)
);

CREATE TABLE shippers (
    shipper_id VARCHAR(255) PRIMARY KEY,
    company_name VARCHAR(255),
    phone VARCHAR(255)
);

CREATE TABLE orders (
    order_id VARCHAR(255) PRIMARY KEY,
    order_date DATE,
    required_date DATE,
    shipped_date DATE,
    shipping_cost DOUBLE PRECISION,
    ship_name VARCHAR(255),
    ship_address VARCHAR(255),
    ship_city VARCHAR(255),
    ship_region VARCHAR(255),
    ship_postal_code VARCHAR(255),
    ship_country VARCHAR(255),
    customer_id VARCHAR(255) NOT NULL REFERENCES customers(customer_id),
    employee_id VARCHAR(255) NOT NULL REFERENCES employees(employee_id),
    shipper_id VARCHAR(255) NOT NULL REFERENCES shippers(shipper_id),
    status VARCHAR(255)
);

CREATE TABLE order_details (
    order_id VARCHAR(255) NOT NULL REFERENCES orders(order_id),
    product_id VARCHAR(255) NOT NULL REFERENCES products(product_id),
    unit_price DOUBLE PRECISION,
    quantity INTEGER,
    discount DOUBLE PRECISION,
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE customer_contacts (
    customer_id VARCHAR(255) NOT NULL REFERENCES customers(customer_id),
    contact_name VARCHAR(255),
    contact_title VARCHAR(255),
    phone VARCHAR(255),
    fax VARCHAR(255),
    contact_id VARCHAR(255) PRIMARY KEY
);

CREATE TABLE region (
    region_id VARCHAR(255) PRIMARY KEY,
    region_description VARCHAR(255)
);

CREATE TABLE territories (
    territory_id VARCHAR(255) PRIMARY KEY,
    territory_description VARCHAR(255),
    region_id VARCHAR(255) NOT NULL REFERENCES region(region_id)
);

CREATE TABLE employee_territories (
    employee_id VARCHAR(255) NOT NULL REFERENCES employees(employee_id),
    territory_id VARCHAR(255) NOT NULL REFERENCES territories(territory_id),
    PRIMARY KEY (employee_id, territory_id)
);
