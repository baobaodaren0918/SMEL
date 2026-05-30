// Neo4j Graph Schema: Northwind
// 7 nodes, 7 relationships, 61 properties for SMILE Graph migration testing
// order_details modeled as CONTAINS relationship with properties (unit_price, quantity, discount)
// Tests: relationship-with-properties, self-reference, multi-hop paths

// Node: categories
// Key: category_id
// Properties: category_id (string), category_name (string), description (string)

// Node: suppliers
// Key: supplier_id
// Properties: supplier_id (string), company_name (string), contact_name (string), contact_title (string), phone (string), fax (string), street (string), city (string), region (string), postal_code (string), country (string)

// Node: shippers
// Key: shipper_id
// Properties: shipper_id (string), company_name (string), phone (string)

// Node: employees
// Key: employee_id
// Properties: employee_id (string), last_name (string), first_name (string), title (string), birth_date (date), hire_date (date), phone (string), notes (string), street (string), city (string), region (string), postal_code (string), country (string)

// Node: customers
// Key: customer_id
// Properties: customer_id (string), company_name (string), contact_name (string), contact_title (string), phone (string), fax (string), street (string), city (string), region (string), postal_code (string), country (string)

// Node: products
// Key: product_id
// Properties: product_id (string), product_name (string), unit_price (double), units_in_stock (integer), discontinued (boolean), quantity_per_unit (string)

// Node: orders
// Key: order_id
// Properties: order_id (string), order_date (date), required_date (date), shipped_date (date), freight (double), ship_name (string), ship_address (string), ship_city (string), ship_region (string), ship_postal_code (string), ship_country (string)

// Relationship: SUPPLIES (suppliers -> products)
// Per supplier: 0..n products; Per product: 1..1 supplier (NOT NULL FK in PG)
// Cardinality: 0..n
// Source-Cardinality: 1..1

// Relationship: PART_OF (products -> categories)
// Per product: 1..1 category (NOT NULL FK in PG); Per category: 0..n products
// Cardinality: 1..1
// Source-Cardinality: 0..n

// Relationship: PURCHASED (customers -> orders)
// Per customer: 0..n orders; Per order: 1..1 customer (NOT NULL FK in PG)
// Cardinality: 0..n
// Source-Cardinality: 1..1

// Relationship: SOLD (employees -> orders)
// Per employee: 0..n orders; Per order: 1..1 employee (NOT NULL FK in PG)
// Cardinality: 0..n
// Source-Cardinality: 1..1

// Relationship: SHIPPED_VIA (orders -> shippers)
// Per order: 1..1 shipper (NOT NULL FK in PG); Per shipper: 0..n orders
// Cardinality: 1..1
// Source-Cardinality: 0..n

// Relationship: REPORTS_TO (employees -> employees)
// Per employee: 0..1 manager (self-ref, nullable FK); per manager: 0..n direct reports
// Cardinality: 0..1
// Source-Cardinality: 0..n

// Relationship: CONTAINS (orders -> products)
// Properties: unit_price (double), quantity (integer), discount (double)
// Per order: 0..n products; Per product: 0..n orders (M:N junction)
// Cardinality: 0..n
// Source-Cardinality: 0..n
