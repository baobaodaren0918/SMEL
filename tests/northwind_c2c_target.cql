-- Cassandra Schema: Northwind V2 (C2C Evolution Target)
-- 10 tables: 8 original - categories(MERGE) + customer_contacts(SPLIT) + region + territories + employee_territories

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

CREATE TABLE employees (
    employee_id TEXT,
    last_name TEXT,
    first_name TEXT,
    title TEXT,
    hire_date DATE,
    phone TEXT,
    street TEXT,
    city TEXT,
    region TEXT,
    postal_code TEXT,
    country TEXT,
    reports_to TEXT,
    email TEXT,
    PRIMARY KEY (employee_id)
);

CREATE TABLE customers (
    customer_id TEXT,
    company_name TEXT,
    street TEXT,
    city TEXT,
    region TEXT,
    postal_code TEXT,
    country TEXT,
    PRIMARY KEY (customer_id)
);

CREATE TABLE products (
    category_name TEXT,
    description TEXT,
    supplier_id TEXT,
    product_id TEXT,
    name TEXT,
    unit_price DOUBLE,
    units_in_stock INT,
    discontinued BOOLEAN,
    quantity_per_unit TEXT,
    PRIMARY KEY (product_id)
);

CREATE TABLE shippers (
    shipper_id TEXT,
    company_name TEXT,
    phone TEXT,
    PRIMARY KEY (shipper_id)
);

CREATE TABLE orders (
    order_date DATE,
    customer_id TEXT,
    order_id TEXT,
    required_date DATE,
    shipped_date DATE,
    shipping_cost DOUBLE,
    ship_name TEXT,
    ship_address TEXT,
    ship_city TEXT,
    ship_region TEXT,
    ship_postal_code TEXT,
    ship_country TEXT,
    employee_id TEXT,
    shipper_id TEXT,
    status TEXT,
    PRIMARY KEY ((order_date), customer_id, order_id)
);

CREATE TABLE order_details (
    order_id TEXT,
    product_id TEXT,
    unit_price DOUBLE,
    quantity INT,
    discount DOUBLE,
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE customer_contacts (
    customer_id TEXT,
    contact_name TEXT,
    contact_title TEXT,
    phone TEXT,
    fax TEXT,
    contact_id INT,
    PRIMARY KEY ((customer_id), contact_id)
);

CREATE TABLE sales_region (
    region_id TEXT,
    region_description TEXT,
    PRIMARY KEY (region_id)
);

CREATE TABLE territories (
    territory_id TEXT,
    territory_description TEXT,
    region_id TEXT,
    PRIMARY KEY (territory_id)
);

CREATE TABLE employee_territories (
    employee_id TEXT,
    region_id TEXT,
    territory_id TEXT,
    PRIMARY KEY ((employee_id, region_id), territory_id)
);
