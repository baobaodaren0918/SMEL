"""Generate PDF of Northwind 4-database schemas for printing."""
from fpdf import FPDF

class SchemaPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "Northwind Schema - 4 Database Models", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(220, 220, 220)
        self.cell(0, 7, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def code_block(self, text):
        self.set_font("Courier", "", 8)
        for line in text.strip().split("\n"):
            self.cell(0, 3.8, "  " + line, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def info_text(self, text):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 4.5, text)
        self.ln(1)

    def table_row(self, cols, widths, bold=False):
        self.set_font("Helvetica", "B" if bold else "", 8)
        for i, col in enumerate(cols):
            self.cell(widths[i], 5, col, border=1)
        self.ln()


pdf = SchemaPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=15)

# ============================================================
# Page 1: PostgreSQL
# ============================================================
pdf.add_page()
pdf.section_title("1. PostgreSQL (Relational) - 8 Tables, 8 FK, 69 Fields")

sql = """-- Table 1: categories
CREATE TABLE categories (
    category_id VARCHAR(255) PRIMARY KEY,
    category_name VARCHAR(255),
    description VARCHAR(255)
);

-- Table 2: suppliers (flattened address)
CREATE TABLE suppliers (
    supplier_id VARCHAR(255) PRIMARY KEY,
    company_name VARCHAR(255), contact_name VARCHAR(255),
    contact_title VARCHAR(255), phone VARCHAR(255), fax VARCHAR(255),
    street VARCHAR(255), city VARCHAR(255), region VARCHAR(255),
    postal_code VARCHAR(255), country VARCHAR(255)
);

-- Table 3: shippers
CREATE TABLE shippers (
    shipper_id VARCHAR(255) PRIMARY KEY,
    company_name VARCHAR(255), phone VARCHAR(255)
);

-- Table 4: employees (self-reference: reports_to)
CREATE TABLE employees (
    employee_id VARCHAR(255) PRIMARY KEY,
    last_name VARCHAR(255), first_name VARCHAR(255),
    title VARCHAR(255), birth_date VARCHAR(255), hire_date VARCHAR(255),
    phone VARCHAR(255), notes VARCHAR(255),
    street VARCHAR(255), city VARCHAR(255), region VARCHAR(255),
    postal_code VARCHAR(255), country VARCHAR(255),
    reports_to VARCHAR(255) REFERENCES employees(employee_id)
);

-- Table 5: customers (flattened address)
CREATE TABLE customers (
    customer_id VARCHAR(255) PRIMARY KEY,
    company_name VARCHAR(255), contact_name VARCHAR(255),
    contact_title VARCHAR(255), phone VARCHAR(255), fax VARCHAR(255),
    street VARCHAR(255), city VARCHAR(255), region VARCHAR(255),
    postal_code VARCHAR(255), country VARCHAR(255)
);

-- Table 6: products (FK -> suppliers, categories)
CREATE TABLE products (
    product_id VARCHAR(255) PRIMARY KEY,
    product_name VARCHAR(255), unit_price DOUBLE PRECISION,
    units_in_stock INTEGER, discontinued BOOLEAN,
    quantity_per_unit VARCHAR(255),
    supplier_id VARCHAR(255) NOT NULL REFERENCES suppliers(supplier_id),
    category_id VARCHAR(255) NOT NULL REFERENCES categories(category_id)
);

-- Table 7: orders (FK -> customers, employees, shippers)
CREATE TABLE orders (
    order_id VARCHAR(255) PRIMARY KEY,
    order_date VARCHAR(255), required_date VARCHAR(255),
    shipped_date VARCHAR(255), freight DOUBLE PRECISION,
    ship_name VARCHAR(255), ship_address VARCHAR(255),
    ship_city VARCHAR(255), ship_region VARCHAR(255),
    ship_postal_code VARCHAR(255), ship_country VARCHAR(255),
    customer_id VARCHAR(255) NOT NULL REFERENCES customers(customer_id),
    employee_id VARCHAR(255) NOT NULL REFERENCES employees(employee_id),
    shipper_id VARCHAR(255) NOT NULL REFERENCES shippers(shipper_id)
);

-- Table 8: order_details (composite PK, FK -> orders, products)
CREATE TABLE order_details (
    order_id VARCHAR(255) NOT NULL REFERENCES orders(order_id),
    product_id VARCHAR(255) NOT NULL REFERENCES products(product_id),
    unit_price DOUBLE PRECISION, quantity INTEGER, discount DOUBLE PRECISION,
    PRIMARY KEY (order_id, product_id)
);"""
pdf.code_block(sql)

pdf.info_text("FK Relations: suppliers->products, categories->products, customers->orders, "
              "employees->orders, shippers->orders, orders->order_details, "
              "products->order_details, employees->employees (self-ref)")

# ============================================================
# Page 2: MongoDB
# ============================================================
pdf.add_page()
pdf.section_title("2. MongoDB (Document) - 1 Root Document 'orders', 4-Level Nesting")

pdf.info_text("Single collection 'orders' with all entities embedded as nested documents/arrays.")
pdf.ln(1)

mongo_tree = """orders (root document)
|-- _id: string (order_id, primary key)
|-- order_date: string
|-- required_date: string
|-- shipped_date: string
|-- freight: double
|-- ship_name: string
|-- ship_destination: object (Level 1)
|   |-- ship_address: string
|   |-- ship_city: string
|   |-- ship_region: string
|   |-- ship_postal_code: string
|   +-- ship_country: string
|
|-- customer: object (Level 1 - embedded, required)
|   |-- company_name: string
|   |-- contact_name: string
|   |-- contact_title: string
|   |-- phone: string
|   |-- fax: string
|   +-- address: object (Level 2)
|       |-- street: string
|       |-- city: string
|       |-- region: string
|       |-- postal_code: string
|       +-- country: string
|
|-- employee: object (Level 1 - embedded, required)
|   |-- last_name: string
|   |-- first_name: string
|   |-- title: string
|   |-- birth_date: string
|   |-- hire_date: string
|   |-- phone: string
|   |-- notes: string
|   |-- reports_to: string (self-reference)
|   +-- address: object (Level 2)
|       |-- street: string
|       |-- city: string
|       |-- region: string
|       |-- postal_code: string
|       +-- country: string
|
|-- shipper: object (Level 1 - embedded, required)
|   |-- company_name: string
|   +-- phone: string
|
+-- details: array (Level 1 - order line items)
    +-- [each item]:
        |-- unit_price: double
        |-- quantity: int
        |-- discount: double
        +-- product: object (Level 2, required)
            |-- product_name: string
            |-- unit_price: double
            |-- units_in_stock: int
            |-- discontinued: bool
            |-- quantity_per_unit: string
            |-- category: object (Level 3, required)
            |   |-- category_name: string
            |   +-- description: string
            +-- supplier: object (Level 3, required)
                |-- company_name: string
                |-- contact_name: string
                |-- contact_title: string
                |-- phone: string
                |-- fax: string
                +-- address: object (Level 4 - deepest)
                    |-- street: string
                    |-- city: string
                    |-- region: string
                    |-- postal_code: string
                    +-- country: string"""
pdf.code_block(mongo_tree)

# ============================================================
# Page 3: Neo4j
# ============================================================
pdf.add_page()
pdf.section_title("3. Neo4j (Graph) - 7 Nodes, 7 Relationships, 61 Properties")

pdf.set_font("Helvetica", "B", 10)
pdf.cell(0, 6, "Nodes (58 node properties):", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)

nodes = [
    ("categories",  "category_id (PK)", "category_name, description"),
    ("suppliers",   "supplier_id (PK)", "company_name, contact_name, contact_title, phone, fax, street, city, region, postal_code, country"),
    ("shippers",    "shipper_id (PK)", "company_name, phone"),
    ("employees",   "employee_id (PK)", "last_name, first_name, title, birth_date, hire_date, phone, notes, street, city, region, postal_code, country"),
    ("customers",   "customer_id (PK)", "company_name, contact_name, contact_title, phone, fax, street, city, region, postal_code, country"),
    ("products",    "product_id (PK)", "product_name, unit_price, units_in_stock, discontinued, quantity_per_unit"),
    ("orders",      "order_id (PK)", "order_date, required_date, shipped_date, freight, ship_name, ship_address, ship_city, ship_region, ship_postal_code, ship_country"),
]
w = [30, 30, 130]
pdf.table_row(["Node", "Key", "Properties"], w, bold=True)
for n, k, p in nodes:
    pdf.table_row([n, k, p], w)

pdf.ln(4)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(0, 6, "Relationships (3 relationship properties):", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)

rels = [
    ("SUPPLIES",    "suppliers -> products",   "-",           "Per supplier: 0..n; Per product: 1..1"),
    ("PART_OF",     "products -> categories",  "-",           "Per product: 1..1; Per category: 0..n"),
    ("PURCHASED",   "customers -> orders",     "-",           "Per customer: 0..n; Per order: 1..1"),
    ("SOLD",        "employees -> orders",     "-",           "Per employee: 0..n; Per order: 1..1"),
    ("SHIPPED_VIA", "orders -> shippers",      "-",           "Per order: 1..1; Per shipper: 0..n"),
    ("REPORTS_TO",  "employees -> employees",  "-",           "Per employee: 0..1 (nullable)"),
    ("CONTAINS",    "orders -> products",      "unit_price, quantity, discount", "M:N (0..n both sides)"),
]
w2 = [25, 42, 50, 73]
pdf.table_row(["Relationship", "Direction", "Properties", "Cardinality"], w2, bold=True)
for r, d, p, c in rels:
    pdf.table_row([r, d, p, c], w2)

pdf.ln(3)
pdf.info_text("Note: CONTAINS relationship carries order_details properties (unit_price, quantity, discount). "
              "REPORTS_TO is a self-referencing relationship on employees. "
              "1..1 cardinality corresponds to NOT NULL FK in PostgreSQL.")

# ============================================================
# Page 4: Cassandra
# ============================================================
pdf.add_page()
pdf.section_title("4. Cassandra (Wide-Column) - 8 Tables, Query-Driven Design, 69 Fields")

pdf.info_text("Denormalized, query-driven design. No foreign keys - referenced IDs stored as plain fields. "
              "Partition keys determine data distribution; clustering keys determine sort order within partitions.")
pdf.ln(1)

cql = """-- Table 1: categories (simple PK)
CREATE TABLE categories (
    category_id TEXT,
    category_name TEXT, description TEXT,
    PRIMARY KEY (category_id)
);

-- Table 2: suppliers (simple PK, flattened address)
CREATE TABLE suppliers (
    supplier_id TEXT,
    company_name TEXT, contact_name TEXT, contact_title TEXT,
    phone TEXT, fax TEXT,
    street TEXT, city TEXT, region TEXT, postal_code TEXT, country TEXT,
    PRIMARY KEY (supplier_id)
);

-- Table 3: shippers (simple PK)
CREATE TABLE shippers (
    shipper_id TEXT,
    company_name TEXT, phone TEXT,
    PRIMARY KEY (shipper_id)
);

-- Table 4: employees (simple PK, reports_to as plain TEXT)
CREATE TABLE employees (
    employee_id TEXT,
    last_name TEXT, first_name TEXT, title TEXT,
    birth_date TEXT, hire_date TEXT, phone TEXT, notes TEXT,
    street TEXT, city TEXT, region TEXT, postal_code TEXT, country TEXT,
    reports_to TEXT,
    PRIMARY KEY (employee_id)
);

-- Table 5: customers (simple PK, flattened address)
CREATE TABLE customers (
    customer_id TEXT,
    company_name TEXT, contact_name TEXT, contact_title TEXT,
    phone TEXT, fax TEXT,
    street TEXT, city TEXT, region TEXT, postal_code TEXT, country TEXT,
    PRIMARY KEY (customer_id)
);

-- Table 6: products (composite partition: category_id + supplier_id)
CREATE TABLE products (
    category_id TEXT, supplier_id TEXT,
    product_id TEXT,
    product_name TEXT, unit_price DOUBLE, units_in_stock INT,
    discontinued BOOLEAN, quantity_per_unit TEXT,
    PRIMARY KEY ((category_id, supplier_id), product_id)
);

-- Table 7: orders (partition: customer_id, clustering: order_date, order_id)
CREATE TABLE orders (
    customer_id TEXT, order_date TEXT, order_id TEXT,
    required_date TEXT, shipped_date TEXT, freight DOUBLE,
    ship_name TEXT, ship_address TEXT, ship_city TEXT,
    ship_region TEXT, ship_postal_code TEXT, ship_country TEXT,
    employee_id TEXT,   -- logically NOT NULL (FK in PG)
    shipper_id TEXT,    -- logically NOT NULL (FK in PG)
    PRIMARY KEY ((customer_id), order_date, order_id)
);

-- Table 8: order_details (composite partition: order_id + product_id)
CREATE TABLE order_details (
    order_id TEXT, product_id TEXT,
    unit_price DOUBLE, quantity INT, discount DOUBLE,
    PRIMARY KEY ((order_id, product_id))
);"""
pdf.code_block(cql)

pdf.ln(2)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(0, 6, "Key Design Summary:", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)
w3 = [35, 35, 50, 70]
pdf.table_row(["Table", "Partition Key", "Clustering Key", "Query Pattern"], w3, bold=True)
rows = [
    ("categories",     "category_id",  "-",                  "Lookup by category"),
    ("suppliers",      "supplier_id",  "-",                  "Lookup by supplier"),
    ("shippers",       "shipper_id",   "-",                  "Lookup by shipper"),
    ("employees",      "employee_id",  "-",                  "Lookup by employee"),
    ("customers",      "customer_id",  "-",                  "Lookup by customer"),
    ("products",       "(category_id, supplier_id)",  "product_id",  "Products by category+supplier"),
    ("orders",         "customer_id",  "order_date, order_id","Orders by customer+date"),
    ("order_details",  "(order_id, product_id)",     "-",           "Lookup by order+product"),
]
for r in rows:
    pdf.table_row(list(r), w3)

out_path = "tests/Northwind_Schemas_4DB_v3.pdf"
pdf.output(out_path)
print(f"PDF generated: {out_path}")
