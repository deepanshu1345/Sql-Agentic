"""
Enterprise Demo Database Seeder

Creates a realistic enterprise commerce database with:
- 20+ related tables
- 100+ columns
- PK/FK relationships
- Thousands of demo records
- Complex relationships suitable for NL -> SQL testing
- pgvector schema indexing using LocalVectorSchemaStore

Requirements:
    pip install psycopg2-binary

Environment:
    DATABASE_URL=postgresql://postgres:postgres@localhost:5433/demo_db

Run:
    python seed_enterprise_database.py
"""

import os
import random
from datetime import datetime, timedelta
from decimal import Decimal

import psycopg2
from psycopg2.extras import execute_batch

from src.vector_store import LocalVectorSchemaStore


# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/analytics_db")

SEED = 42
random.seed(SEED)

NUM_CUSTOMERS = 500
NUM_EMPLOYEES = 50
NUM_PRODUCTS = 300
NUM_ORDERS = 1500
NUM_ORDER_ITEMS = 4000
NUM_PAYMENTS = 1500
NUM_SHIPMENTS = 1200
NUM_REVIEWS = 1000
NUM_SUPPORT_TICKETS = 400
NUM_INVENTORY_RECORDS = 600
NUM_SUBSCRIPTIONS = 300
NUM_PROMOTIONS = 50
NUM_COUPONS = 300
NUM_ADDRESSES = 800


# ============================================================
# DATABASE CONNECTION
# ============================================================

def ensure_database_exists():
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    try:
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5433/postgres")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'analytics_db';")
        if not cur.fetchone():
            print("Creating database 'analytics_db'...")
            cur.execute('CREATE DATABASE analytics_db;')
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database check: {e}")

def get_connection():
    ensure_database_exists()
    return psycopg2.connect(DATABASE_URL)


# ============================================================
# SCHEMA DEFINITIONS
# ============================================================

SCHEMAS = {

"organizations": """
CREATE TABLE organizations (
    organization_id SERIAL PRIMARY KEY,
    organization_name VARCHAR(150) NOT NULL,
    industry VARCHAR(100),
    company_size VARCHAR(50),
    country VARCHAR(100),
    website VARCHAR(255),
    tax_identifier VARCHAR(100),
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"departments": """
CREATE TABLE departments (
    department_id SERIAL PRIMARY KEY,
    organization_id INT NOT NULL REFERENCES organizations(organization_id),
    department_name VARCHAR(100) NOT NULL,
    department_code VARCHAR(30) UNIQUE NOT NULL,
    cost_center VARCHAR(50),
    manager_employee_id INT,
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"employees": """
CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    organization_id INT NOT NULL REFERENCES organizations(organization_id),
    department_id INT REFERENCES departments(department_id),
    manager_id INT REFERENCES employees(employee_id),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(30),
    job_title VARCHAR(100),
    employment_type VARCHAR(30),
    salary NUMERIC(12,2),
    hire_date DATE,
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"customers": """
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    organization_id INT REFERENCES organizations(organization_id),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(30),
    date_of_birth DATE,
    gender VARCHAR(30),
    customer_tier VARCHAR(30) DEFAULT 'standard',
    loyalty_points INT DEFAULT 0,
    lifetime_value NUMERIC(14,2) DEFAULT 0,
    acquisition_channel VARCHAR(50),
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);
""",

"addresses": """
CREATE TABLE addresses (
    address_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id),
    address_type VARCHAR(30),
    address_line_1 VARCHAR(200),
    address_line_2 VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"categories": """
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    parent_category_id INT REFERENCES categories(category_id),
    category_name VARCHAR(100) NOT NULL,
    category_code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"brands": """
CREATE TABLE brands (
    brand_id SERIAL PRIMARY KEY,
    brand_name VARCHAR(100) NOT NULL,
    description TEXT,
    country_of_origin VARCHAR(100),
    website VARCHAR(255),
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"products": """
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    category_id INT NOT NULL REFERENCES categories(category_id),
    brand_id INT NOT NULL REFERENCES brands(brand_id),
    sku VARCHAR(100) UNIQUE NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    description TEXT,
    unit_price NUMERIC(12,2) NOT NULL,
    cost_price NUMERIC(12,2),
    tax_rate NUMERIC(5,2),
    weight_kg NUMERIC(8,3),
    status VARCHAR(30) DEFAULT 'active',
    launch_date DATE,
    discontinued_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"product_variants": """
CREATE TABLE product_variants (
    variant_id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(product_id),
    variant_sku VARCHAR(100) UNIQUE NOT NULL,
    color VARCHAR(50),
    size VARCHAR(50),
    material VARCHAR(100),
    additional_price NUMERIC(10,2) DEFAULT 0,
    stock_tracking BOOLEAN DEFAULT TRUE,
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"warehouses": """
CREATE TABLE warehouses (
    warehouse_id SERIAL PRIMARY KEY,
    organization_id INT NOT NULL REFERENCES organizations(organization_id),
    warehouse_name VARCHAR(150) NOT NULL,
    warehouse_code VARCHAR(50) UNIQUE NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    capacity_units INT,
    manager_employee_id INT REFERENCES employees(employee_id),
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"inventory": """
CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    warehouse_id INT NOT NULL REFERENCES warehouses(warehouse_id),
    product_id INT NOT NULL REFERENCES products(product_id),
    variant_id INT REFERENCES product_variants(variant_id),
    quantity_on_hand INT DEFAULT 0,
    quantity_reserved INT DEFAULT 0,
    reorder_level INT DEFAULT 10,
    reorder_quantity INT DEFAULT 50,
    last_restocked_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"promotions": """
CREATE TABLE promotions (
    promotion_id SERIAL PRIMARY KEY,
    promotion_name VARCHAR(150) NOT NULL,
    promotion_code VARCHAR(50) UNIQUE,
    discount_type VARCHAR(30),
    discount_value NUMERIC(10,2),
    minimum_order_value NUMERIC(12,2),
    maximum_discount NUMERIC(12,2),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    usage_limit INT,
    usage_count INT DEFAULT 0,
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"coupons": """
CREATE TABLE coupons (
    coupon_id SERIAL PRIMARY KEY,
    promotion_id INT NOT NULL REFERENCES promotions(promotion_id),
    customer_id INT REFERENCES customers(customer_id),
    coupon_code VARCHAR(80) UNIQUE NOT NULL,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    redeemed_at TIMESTAMP,
    status VARCHAR(30) DEFAULT 'available'
);
""",

"orders": """
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id),
    promotion_id INT REFERENCES promotions(promotion_id),
    shipping_address_id INT REFERENCES addresses(address_id),
    billing_address_id INT REFERENCES addresses(address_id),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    order_date TIMESTAMP NOT NULL,
    subtotal NUMERIC(14,2) NOT NULL,
    discount_amount NUMERIC(14,2) DEFAULT 0,
    tax_amount NUMERIC(14,2) DEFAULT 0,
    shipping_amount NUMERIC(14,2) DEFAULT 0,
    total_amount NUMERIC(14,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    payment_status VARCHAR(30),
    fulfillment_status VARCHAR(30),
    order_status VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"order_items": """
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(order_id),
    product_id INT NOT NULL REFERENCES products(product_id),
    variant_id INT REFERENCES product_variants(variant_id),
    quantity INT NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL,
    discount_amount NUMERIC(12,2) DEFAULT 0,
    tax_amount NUMERIC(12,2) DEFAULT 0,
    line_total NUMERIC(14,2) NOT NULL
);
""",

"payments": """
CREATE TABLE payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(order_id),
    customer_id INT NOT NULL REFERENCES customers(customer_id),
    transaction_reference VARCHAR(100) UNIQUE NOT NULL,
    payment_method VARCHAR(50),
    payment_provider VARCHAR(50),
    amount NUMERIC(14,2),
    currency VARCHAR(10),
    payment_status VARCHAR(30),
    failure_reason TEXT,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"refunds": """
CREATE TABLE refunds (
    refund_id SERIAL PRIMARY KEY,
    payment_id INT NOT NULL REFERENCES payments(payment_id),
    order_id INT NOT NULL REFERENCES orders(order_id),
    refund_reference VARCHAR(100) UNIQUE NOT NULL,
    refund_amount NUMERIC(14,2),
    reason VARCHAR(200),
    refund_status VARCHAR(30),
    requested_at TIMESTAMP,
    processed_at TIMESTAMP
);
""",

"shipments": """
CREATE TABLE shipments (
    shipment_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(order_id),
    warehouse_id INT NOT NULL REFERENCES warehouses(warehouse_id),
    tracking_number VARCHAR(100) UNIQUE,
    carrier VARCHAR(50),
    shipping_method VARCHAR(50),
    shipped_at TIMESTAMP,
    estimated_delivery_date DATE,
    delivered_at TIMESTAMP,
    shipment_status VARCHAR(30),
    shipping_cost NUMERIC(10,2)
);
""",

"reviews": """
CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id),
    product_id INT NOT NULL REFERENCES products(product_id),
    order_id INT REFERENCES orders(order_id),
    rating INT CHECK (rating BETWEEN 1 AND 5),
    review_title VARCHAR(200),
    review_text TEXT,
    verified_purchase BOOLEAN DEFAULT FALSE,
    helpful_votes INT DEFAULT 0,
    status VARCHAR(30) DEFAULT 'published',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",

"support_tickets": """
CREATE TABLE support_tickets (
    ticket_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id),
    assigned_employee_id INT REFERENCES employees(employee_id),
    order_id INT REFERENCES orders(order_id),
    category VARCHAR(100),
    priority VARCHAR(30),
    subject VARCHAR(250),
    description TEXT,
    status VARCHAR(30),
    resolution TEXT,
    opened_at TIMESTAMP,
    resolved_at TIMESTAMP,
    satisfaction_score INT
);
""",

"subscriptions": """
CREATE TABLE subscriptions (
    subscription_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id),
    product_id INT REFERENCES products(product_id),
    plan_name VARCHAR(100),
    billing_frequency VARCHAR(30),
    quantity INT DEFAULT 1,
    price NUMERIC(12,2),
    start_date DATE,
    next_billing_date DATE,
    cancellation_date DATE,
    status VARCHAR(30),
    auto_renew BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
}


# ============================================================
# DATA GENERATION HELPERS
# ============================================================

FIRST_NAMES = [
    "John", "David", "Michael", "Robert", "Daniel",
    "James", "William", "Thomas", "Matthew", "Andrew",
    "Amit", "Rahul", "Arjun", "Rohan", "Vikram",
    "Priya", "Ananya", "Sneha", "Neha", "Pooja"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones",
    "Miller", "Davis", "Wilson", "Taylor", "Anderson",
    "Sharma", "Patel", "Verma", "Mehta", "Joshi",
    "Deshmukh", "Kulkarni", "Singh", "Gupta", "Khan"
]

CITIES = [
    ("New York", "New York", "USA"),
    ("San Francisco", "California", "USA"),
    ("Chicago", "Illinois", "USA"),
    ("Austin", "Texas", "USA"),
    ("Seattle", "Washington", "USA"),
    ("London", "England", "UK"),
    ("Mumbai", "Maharashtra", "India"),
    ("Pune", "Maharashtra", "India"),
    ("Bangalore", "Karnataka", "India"),
    ("Delhi", "Delhi", "India"),
]

PRODUCT_CATEGORIES = [
    "Electronics",
    "Laptops",
    "Mobile Phones",
    "Accessories",
    "Home Appliances",
    "Furniture",
    "Office Supplies",
    "Gaming",
    "Wearables",
    "Networking"
]

BRANDS = [
    "NovaTech",
    "Apex",
    "Vertex",
    "Quantum",
    "Orion",
    "NexGen",
    "BluePeak",
    "TechCore",
    "Zenith",
    "PrimeWorks"
]

PAYMENT_METHODS = [
    "credit_card",
    "debit_card",
    "paypal",
    "bank_transfer",
    "upi"
]

CARRIERS = [
    "FedEx",
    "UPS",
    "DHL",
    "USPS",
    "BlueDart"
]


def random_name():
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


def random_date(start_year=2022, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return start + timedelta(
        seconds=random.randint(0, int((end - start).total_seconds()))
    )


def random_decimal(min_value, max_value):
    return Decimal(
        str(round(random.uniform(min_value, max_value), 2))
    )


def insert_many(cursor, query, rows):
    execute_batch(cursor, query, rows, page_size=500)


# ============================================================
# SEED ORGANIZATIONS
# ============================================================

def seed_organizations(cur):
    rows = []

    for i in range(10):
        rows.append((
            f"Enterprise Organization {i + 1}",
            random.choice([
                "Technology",
                "Healthcare",
                "Finance",
                "Retail",
                "Manufacturing"
            ]),
            random.choice([
                "Startup",
                "Mid-Market",
                "Enterprise"
            ]),
            random.choice(["USA", "India", "UK", "Germany"]),
            f"https://company{i + 1}.example.com",
            f"TAX-{100000 + i}",
        ))

    insert_many(
        cur,
        """
        INSERT INTO organizations
        (organization_name, industry, company_size, country,
         website, tax_identifier)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED DEPARTMENTS
# ============================================================

def seed_departments(cur):
    rows = []

    departments = [
        ("Engineering", "ENG"),
        ("Sales", "SALES"),
        ("Marketing", "MKT"),
        ("Finance", "FIN"),
        ("Operations", "OPS"),
        ("Customer Success", "CS"),
        ("Human Resources", "HR"),
        ("IT", "IT"),
    ]

    for org_id in range(1, 11):
        for name, code in departments:
            rows.append((
                org_id,
                name,
                f"{code}-{org_id}",
                f"CC-{org_id}-{code}"
            ))

    insert_many(
        cur,
        """
        INSERT INTO departments
        (organization_id, department_name, department_code, cost_center)
        VALUES (%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED EMPLOYEES
# ============================================================

def seed_employees(cur):
    rows = []

    for i in range(NUM_EMPLOYEES):
        first, last = random_name()

        organization_id = random.randint(1, 10)
        department_id = ((organization_id - 1) * 8) + random.randint(1, 8)

        rows.append((
            organization_id,
            department_id,
            None,
            first,
            last,
            f"{first.lower()}.{last.lower()}.{i}@enterprise.example.com",
            f"+1-555-{1000 + i}",
            random.choice([
                "Software Engineer",
                "Senior Software Engineer",
                "Product Manager",
                "Sales Manager",
                "Data Analyst",
                "DevOps Engineer",
                "Support Specialist",
                "Finance Analyst"
            ]),
            random.choice([
                "full_time",
                "full_time",
                "contractor"
            ]),
            random_decimal(40000, 180000),
            random_date(2018, 2026).date(),
        ))

    insert_many(
        cur,
        """
        INSERT INTO employees
        (organization_id, department_id, manager_id,
         first_name, last_name, email, phone, job_title,
         employment_type, salary, hire_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED CUSTOMERS
# ============================================================

def seed_customers(cur):
    rows = []

    for i in range(NUM_CUSTOMERS):
        first, last = random_name()

        rows.append((
            random.randint(1, 10),
            first,
            last,
            f"customer{i + 1}@example.com",
            f"+1-555-{random.randint(1000000, 9999999)}",
            random_date(1970, 2005).date(),
            random.choice(["male", "female", "other"]),
            random.choice(["standard", "silver", "gold", "platinum"]),
            random.randint(0, 10000),
            random_decimal(100, 50000),
            random.choice([
                "organic",
                "google",
                "facebook",
                "referral",
                "email",
                "partner"
            ]),
        ))

    insert_many(
        cur,
        """
        INSERT INTO customers
        (organization_id, first_name, last_name, email, phone,
         date_of_birth, gender, customer_tier, loyalty_points,
         lifetime_value, acquisition_channel)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED ADDRESSES
# ============================================================

def seed_addresses(cur):
    rows = []

    for i in range(NUM_ADDRESSES):
        customer_id = random.randint(1, NUM_CUSTOMERS)
        city, state, country = random.choice(CITIES)

        rows.append((
            customer_id,
            random.choice(["billing", "shipping", "home", "work"]),
            f"{random.randint(1, 9999)} Main Street",
            random.choice([
                None,
                f"Apartment {random.randint(1, 500)}",
                f"Suite {random.randint(100, 999)}"
            ]),
            city,
            state,
            str(random.randint(10000, 99999)),
            country,
            random.choice([True, False])
        ))

    insert_many(
        cur,
        """
        INSERT INTO addresses
        (customer_id, address_type, address_line_1, address_line_2,
         city, state, postal_code, country, is_default)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED CATEGORIES
# ============================================================

def seed_categories(cur):
    rows = []

    for i, category in enumerate(PRODUCT_CATEGORIES):
        rows.append((
            None,
            category,
            f"CAT-{i + 1:03d}",
            f"Category containing {category.lower()} products."
        ))

    insert_many(
        cur,
        """
        INSERT INTO categories
        (parent_category_id, category_name, category_code, description)
        VALUES (%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED BRANDS
# ============================================================

def seed_brands(cur):
    rows = []

    for brand in BRANDS:
        rows.append((
            brand,
            f"{brand} manufactures enterprise-grade technology products.",
            random.choice(["USA", "India", "Germany", "Japan"]),
            f"https://{brand.lower()}.example.com"
        ))

    insert_many(
        cur,
        """
        INSERT INTO brands
        (brand_name, description, country_of_origin, website)
        VALUES (%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED PRODUCTS
# ============================================================

def seed_products(cur):
    rows = []

    for i in range(NUM_PRODUCTS):
        category_id = random.randint(1, len(PRODUCT_CATEGORIES))
        brand_id = random.randint(1, len(BRANDS))

        price = random_decimal(20, 5000)

        rows.append((
            category_id,
            brand_id,
            f"SKU-{i + 1:06d}",
            f"{random.choice(BRANDS)} {random.choice(PRODUCT_CATEGORIES)} {i + 1}",
            "Enterprise product designed for business and consumer workloads.",
            price,
            round(price * Decimal("0.65"), 2),
            Decimal(str(random.choice([5, 8, 12, 18, 20]))),
            Decimal(str(round(random.uniform(0.1, 20), 3))),
            random_date(2022, 2026).date()
        ))

    insert_many(
        cur,
        """
        INSERT INTO products
        (category_id, brand_id, sku, product_name, description,
         unit_price, cost_price, tax_rate, weight_kg, launch_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED PRODUCT VARIANTS
# ============================================================

def seed_product_variants(cur):
    rows = []

    for i in range(600):
        product_id = random.randint(1, NUM_PRODUCTS)

        rows.append((
            product_id,
            f"VAR-{i + 1:07d}",
            random.choice(["Black", "White", "Silver", "Blue", "Red"]),
            random.choice(["Small", "Medium", "Large", "XL", None]),
            random.choice([
                "Aluminum",
                "Plastic",
                "Steel",
                "Carbon Fiber",
                "Composite"
            ]),
            random_decimal(0, 250)
        ))

    insert_many(
        cur,
        """
        INSERT INTO product_variants
        (product_id, variant_sku, color, size, material, additional_price)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED WAREHOUSES
# ============================================================

def seed_warehouses(cur):
    rows = []

    for i in range(12):
        city, state, country = random.choice(CITIES)

        rows.append((
            random.randint(1, 10),
            f"Warehouse {i + 1}",
            f"WH-{i + 1:03d}",
            city,
            state,
            country,
            random.randint(10000, 100000)
        ))

    insert_many(
        cur,
        """
        INSERT INTO warehouses
        (organization_id, warehouse_name, warehouse_code,
         city, state, country, capacity_units)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED INVENTORY
# ============================================================

def seed_inventory(cur):
    rows = []

    for i in range(NUM_INVENTORY_RECORDS):
        rows.append((
            random.randint(1, 12),
            random.randint(1, NUM_PRODUCTS),
            random.randint(1, 600),
            random.randint(0, 1000),
            random.randint(0, 100),
            random.randint(10, 100),
            random.randint(50, 500),
            random_date(2025, 2026)
        ))

    insert_many(
        cur,
        """
        INSERT INTO inventory
        (warehouse_id, product_id, variant_id,
         quantity_on_hand, quantity_reserved,
         reorder_level, reorder_quantity, last_restocked_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED PROMOTIONS
# ============================================================

def seed_promotions(cur):
    rows = []

    for i in range(NUM_PROMOTIONS):
        rows.append((
            f"Promotion {i + 1}",
            f"PROMO{i + 1:04d}",
            random.choice(["percentage", "fixed"]),
            random_decimal(5, 30),
            random_decimal(50, 500),
            random_decimal(20, 200),
            random.randint(100, 10000),
            random.randint(0, 500)
        ))

    insert_many(
        cur,
        """
        INSERT INTO promotions
        (promotion_name, promotion_code, discount_type,
         discount_value, minimum_order_value,
         maximum_discount, usage_limit, usage_count)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED ORDERS
# ============================================================

def seed_orders(cur):
    rows = []

    for i in range(NUM_ORDERS):
        customer_id = random.randint(1, NUM_CUSTOMERS)

        subtotal = random_decimal(20, 5000)
        discount = random_decimal(0, min(float(subtotal * Decimal("0.2")), 500))
        tax = (subtotal - discount) * Decimal("0.08")
        shipping = random_decimal(0, 100)

        total = subtotal - discount + tax + shipping

        rows.append((
            customer_id,
            random.randint(1, NUM_PROMOTIONS) if random.random() < 0.3 else None,
            random.randint(1, NUM_ADDRESSES),
            random.randint(1, NUM_ADDRESSES),
            f"ORD-{i + 1:08d}",
            random_date(2024, 2026),
            subtotal,
            discount,
            tax,
            shipping,
            total,
            random.choice(["USD", "USD", "EUR", "INR"]),
            random.choice(["paid", "paid", "pending", "failed"]),
            random.choice(["processing", "shipped", "delivered"]),
            random.choice(["completed", "completed", "cancelled"])
        ))

    insert_many(
        cur,
        """
        INSERT INTO orders
        (customer_id, promotion_id, shipping_address_id,
         billing_address_id, order_number, order_date,
         subtotal, discount_amount, tax_amount, shipping_amount,
         total_amount, currency, payment_status,
         fulfillment_status, order_status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED ORDER ITEMS
# ============================================================

def seed_order_items(cur):
    rows = []

    for i in range(NUM_ORDER_ITEMS):
        quantity = random.randint(1, 5)
        unit_price = random_decimal(10, 2000)
        discount = random_decimal(0, 100)
        tax = (unit_price * quantity) * Decimal("0.08")
        line_total = (
            unit_price * quantity
            - discount
            + tax
        )

        rows.append((
            random.randint(1, NUM_ORDERS),
            random.randint(1, NUM_PRODUCTS),
            random.randint(1, 600),
            quantity,
            unit_price,
            discount,
            tax,
            line_total
        ))

    insert_many(
        cur,
        """
        INSERT INTO order_items
        (order_id, product_id, variant_id, quantity,
         unit_price, discount_amount, tax_amount, line_total)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED PAYMENTS
# ============================================================

def seed_payments(cur):
    rows = []

    for i in range(NUM_PAYMENTS):
        order_id = i + 1

        rows.append((
            order_id,
            random.randint(1, NUM_CUSTOMERS),
            f"TXN-{i + 1:010d}",
            random.choice(PAYMENT_METHODS),
            random.choice([
                "Stripe",
                "PayPal",
                "Adyen",
                "Razorpay"
            ]),
            random_decimal(20, 5000),
            random.choice(["USD", "EUR", "INR"]),
            random.choice(["successful", "successful", "successful", "failed"]),
            None,
            random_date(2024, 2026)
        ))

    insert_many(
        cur,
        """
        INSERT INTO payments
        (order_id, customer_id, transaction_reference,
         payment_method, payment_provider, amount,
         currency, payment_status, failure_reason, processed_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED SHIPMENTS
# ============================================================

def seed_shipments(cur):
    rows = []

    for i in range(NUM_SHIPMENTS):
        shipped = random_date(2024, 2026)

        rows.append((
            random.randint(1, NUM_ORDERS),
            random.randint(1, 12),
            f"TRK-{i + 1:012d}",
            random.choice(CARRIERS),
            random.choice([
                "standard",
                "express",
                "overnight",
                "international"
            ]),
            shipped,
            (shipped + timedelta(days=random.randint(1, 10))).date(),
            None,
            random.choice([
                "processing",
                "in_transit",
                "delivered",
                "delayed"
            ]),
            random_decimal(5, 150)
        ))

    insert_many(
        cur,
        """
        INSERT INTO shipments
        (order_id, warehouse_id, tracking_number, carrier,
         shipping_method, shipped_at, estimated_delivery_date,
         delivered_at, shipment_status, shipping_cost)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED REVIEWS
# ============================================================

def seed_reviews(cur):
    rows = []

    for i in range(NUM_REVIEWS):
        rows.append((
            random.randint(1, NUM_CUSTOMERS),
            random.randint(1, NUM_PRODUCTS),
            random.randint(1, NUM_ORDERS),
            random.randint(1, 5),
            random.choice([
                "Great product",
                "Excellent quality",
                "Good value",
                "Could be better",
                "Not satisfied"
            ]),
            random.choice([
                "Very good product for the price.",
                "Quality exceeded my expectations.",
                "Delivery was fast and product works well.",
                "Product was acceptable but could be improved.",
                "The product did not meet my expectations."
            ]),
            random.choice([True, True, False]),
            random.randint(0, 500)
        ))

    insert_many(
        cur,
        """
        INSERT INTO reviews
        (customer_id, product_id, order_id, rating,
         review_title, review_text, verified_purchase,
         helpful_votes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED SUPPORT TICKETS
# ============================================================

def seed_support_tickets(cur):
    rows = []

    for i in range(NUM_SUPPORT_TICKETS):
        opened = random_date(2024, 2026)

        rows.append((
            random.randint(1, NUM_CUSTOMERS),
            random.randint(1, NUM_EMPLOYEES),
            random.randint(1, NUM_ORDERS) if random.random() < 0.7 else None,
            random.choice([
                "Payment",
                "Shipping",
                "Product",
                "Refund",
                "Account",
                "Technical"
            ]),
            random.choice(["low", "medium", "high", "critical"]),
            random.choice([
                "Payment failed",
                "Order delayed",
                "Product damaged",
                "Refund requested",
                "Cannot login",
                "Wrong product received"
            ]),
            "Customer reported an issue requiring investigation.",
            random.choice([
                "open",
                "in_progress",
                "resolved",
                "closed"
            ]),
            None,
            opened,
            None,
            random.randint(1, 5) if random.random() < 0.5 else None
        ))

    insert_many(
        cur,
        """
        INSERT INTO support_tickets
        (customer_id, assigned_employee_id, order_id,
         category, priority, subject, description,
         status, resolution, opened_at,
         resolved_at, satisfaction_score)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# SEED SUBSCRIPTIONS
# ============================================================

def seed_subscriptions(cur):
    rows = []

    for i in range(NUM_SUBSCRIPTIONS):
        start_date = random_date(2023, 2026).date()

        rows.append((
            random.randint(1, NUM_CUSTOMERS),
            random.randint(1, NUM_PRODUCTS),
            random.choice([
                "Basic",
                "Professional",
                "Business",
                "Enterprise"
            ]),
            random.choice([
                "monthly",
                "quarterly",
                "annual"
            ]),
            random.randint(1, 5),
            random_decimal(20, 1000),
            start_date,
            start_date + timedelta(days=random.randint(20, 365)),
            None,
            random.choice([
                "active",
                "active",
                "paused",
                "cancelled"
            ])
        ))

    insert_many(
        cur,
        """
        INSERT INTO subscriptions
        (customer_id, product_id, plan_name,
         billing_frequency, quantity, price,
         start_date, next_billing_date,
         cancellation_date, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        rows
    )


# ============================================================
# INDEX SCHEMAS INTO PGVECTOR
# ============================================================

def index_schemas():
    print("\n🧠 Indexing schemas into pgvector...")

    store = LocalVectorSchemaStore()

    descriptions = {
        "organizations":
            "Stores enterprise organizations, industries, company sizes, countries and corporate metadata.",

        "departments":
            "Stores organizational departments, department codes, cost centers and department hierarchy.",

        "employees":
            "Stores employees, job titles, departments, managers, salaries, employment types and hiring information.",

        "customers":
            "Stores customer profiles, demographic information, loyalty points, customer tiers, lifetime value and acquisition channels.",

        "addresses":
            "Stores customer billing, shipping, home and work addresses.",

        "categories":
            "Stores hierarchical product categories and category metadata.",

        "brands":
            "Stores product brands, country of origin, websites and brand descriptions.",

        "products":
            "Stores product catalog information including SKUs, categories, brands, prices, costs, taxes, weights and lifecycle dates.",

        "product_variants":
            "Stores product variants including SKU, color, size, material and additional pricing.",

        "warehouses":
            "Stores warehouse locations, capacities, managers and organizational ownership.",

        "inventory":
            "Stores warehouse inventory levels, reserved quantities, reorder thresholds and restocking information.",

        "promotions":
            "Stores promotional campaigns, discount rules, minimum order values, usage limits and promotion periods.",

        "coupons":
            "Stores customer-specific and promotional coupon codes, expiration dates and redemption status.",

        "orders":
            "Stores customer orders, totals, taxes, and order statuses. IMPORTANT: Filter order completion using 'order_status' (e.g. order_status = 'completed'). Do NOT use fulfillment_status or payment_status for order completion.",

        "order_items":
            "Stores individual products purchased within orders including quantities, pricing, discounts, taxes and line totals.",

        "payments":
            "Stores payment transactions, payment methods, payment providers, amounts, currencies and payment statuses.",

        "refunds":
            "Stores refund transactions, refund amounts, refund reasons and refund processing status.",

        "shipments":
            "Stores shipment tracking, warehouses, carriers, shipping methods, delivery dates and shipment status.",

        "reviews":
            "Stores customer product reviews, ratings, review text, verified purchases and helpful votes.",

        "support_tickets":
            "Stores customer support issues related to customers and orders, including priority, category, assigned employees and resolution status.",

        "subscriptions":
            "Stores recurring customer subscriptions, subscription plans, billing frequency, prices, renewal dates and cancellation status."
    }

    for table_name, ddl in SCHEMAS.items():
        print(f"   → Indexing {table_name}")

        store.index_table_schema(
            table_name=table_name,
            schema_ddl=ddl,
            description=descriptions[table_name]
        )


# ============================================================
# DATABASE SETUP
# ============================================================

def create_tables(cur):
    print("\n🏗️ Creating enterprise schema...")

    # Order matters because of foreign keys.
    creation_order = [
        "organizations",
        "categories",
        "brands",
        "customers",
        "departments",
        "employees",
        "addresses",
        "products",
        "product_variants",
        "warehouses",
        "inventory",
        "promotions",
        "coupons",
        "orders",
        "order_items",
        "payments",
        "refunds",
        "shipments",
        "reviews",
        "support_tickets",
        "subscriptions"
    ]

    for table in creation_order:
        print(f"   → Creating {table}")
        cur.execute(SCHEMAS[table])


def update_managers(cur):
    cur.execute("""
        UPDATE departments
        SET manager_employee_id = (
            SELECT employee_id
            FROM employees
            WHERE employees.department_id = departments.department_id
            ORDER BY employee_id
            LIMIT 1
        );
    """)

    cur.execute("""
        UPDATE warehouses
        SET manager_employee_id = (
            SELECT employee_id
            FROM employees
            ORDER BY RANDOM()
            LIMIT 1
        );
    """)

# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("🚀 ENTERPRISE DEMO DATABASE SEEDER")
    print("=" * 70)

    print(f"\nDatabase: {DATABASE_URL}")
    print(f"Random seed: {SEED}")

    conn = get_connection()

    try:
        conn.autocommit = False
        cur = conn.cursor()

        # ----------------------------------------------------
        # Clean existing schema
        # ----------------------------------------------------

        print("\n🧹 Removing existing demo tables...")

        cur.execute("""
            DROP TABLE IF EXISTS
                refunds,
                subscriptions,
                support_tickets,
                reviews,
                shipments,
                payments,
                order_items,
                orders,
                coupons,
                promotions,
                inventory,
                warehouses,
                product_variants,
                products,
                brands,
                categories,
                addresses,
                employees,
                departments,
                customers,
                organizations
            CASCADE;
        """)

        # ----------------------------------------------------
        # Create schema
        # ----------------------------------------------------

        create_tables(cur)

        # ----------------------------------------------------
        # Seed data
        # ----------------------------------------------------

        print("\n🌱 Seeding data...")

        print("   → Organizations")
        seed_organizations(cur)

        print("   → Departments")
        seed_departments(cur)

        print("   → Employees")
        seed_employees(cur)

        print("   → Managers")
        update_managers(cur)

        print("   → Customers")
        seed_customers(cur)

        print("   → Addresses")
        seed_addresses(cur)

        print("   → Categories")
        seed_categories(cur)

        print("   → Brands")
        seed_brands(cur)

        print("   → Products")
        seed_products(cur)

        print("   → Product variants")
        seed_product_variants(cur)

        print("   → Warehouses")
        seed_warehouses(cur)

        print("   → Inventory")
        seed_inventory(cur)

        print("   → Promotions")
        seed_promotions(cur)

        print("   → Orders")
        seed_orders(cur)

        print("   → Order items")
        seed_order_items(cur)

        print("   → Payments")
        seed_payments(cur)

        print("   → Shipments")
        seed_shipments(cur)

        print("   → Reviews")
        seed_reviews(cur)

        print("   → Support tickets")
        seed_support_tickets(cur)

        print("   → Subscriptions")
        seed_subscriptions(cur)

        conn.commit()

        print("\n✅ Database seeded successfully!")

    except Exception as exc:
        conn.rollback()

        print("\n❌ Database seeding failed:")
        print(exc)

        raise

    finally:
        cur.close()
        conn.close()

    # --------------------------------------------------------
    # Vector indexing
    # --------------------------------------------------------

    index_schemas()

    print("\n" + "=" * 70)
    print("🎉 ENTERPRISE DATABASE READY")
    print("=" * 70)

    print("""
Tables:
    organizations
    departments
    employees
    customers
    addresses
    categories
    brands
    products
    product_variants
    warehouses
    inventory
    promotions
    coupons
    orders
    order_items
    payments
    refunds
    shipments
    reviews
    support_tickets
    subscriptions

Approximate records:
    Organizations       10
    Departments         80
    Employees           50
    Customers           500
    Addresses           800
    Categories          10
    Brands              10
    Products            300
    Product variants    600
    Warehouses          12
    Inventory           600
    Promotions          50
    Orders              1500
    Order items         4000
    Payments            1500
    Shipments           1200
    Reviews             1000
    Support tickets     400
    Subscriptions       300

Total: ~13,000+ demo records
""")

    print("🧠 Vector schema indexing completed.")
    print("You can now test natural-language → SQL queries.")


if __name__ == "__main__":
    main()