"""
schema.py — Creates the SQLite database schema for the Detoxer Dashboard.

Run once:
    python schema.py
"""

import sqlite3
import os
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DB_NAME = str(BASE_DIR / "app.db")


def get_connection():
    """Return a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")   # enable FK enforcement
    return conn


# ============================================================
# SCHEMA DEFINITION
# ============================================================
SCHEMA_SQL = """
-- ==========================================================
-- USERS TABLE
-- ==========================================================
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('admin', 'user')),
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);


-- ==========================================================
-- PRODUCTS TABLE
-- ==========================================================
CREATE TABLE IF NOT EXISTS products (
    product_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name        TEXT    NOT NULL,
    category            TEXT    NOT NULL DEFAULT 'General',
    product_description TEXT,
    price               REAL    NOT NULL CHECK (price >= 0),
    stock_quantity      INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    status              TEXT    NOT NULL DEFAULT 'In Stock'
                        CHECK (status IN ('In Stock', 'Low Stock', 'Critical', 'Out of Stock')),
    image_url           TEXT,
    review              TEXT,
    created_at          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_status   ON products(status);


-- ==========================================================
-- ORDERS TABLE (optional, for future use)
-- ==========================================================
CREATE TABLE IF NOT EXISTS orders (
    order_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    product_id   INTEGER NOT NULL,
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    total_price  REAL    NOT NULL CHECK (total_price >= 0),
    order_status TEXT    NOT NULL DEFAULT 'Pending'
                 CHECK (order_status IN ('Pending', 'Shipped', 'Delivered', 'Cancelled')),
    ordered_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)    REFERENCES users(id)       ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_orders_user    ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product_id);


-- ==========================================================
-- TRIGGER: auto-update products.updated_at
-- ==========================================================
CREATE TRIGGER IF NOT EXISTS trg_products_updated_at
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
    UPDATE products
       SET updated_at = CURRENT_TIMESTAMP
     WHERE product_id = OLD.product_id;
END;
"""


# ============================================================
# CREATE SCHEMA
# ============================================================
def create_schema():
    """Execute the full schema SQL."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        print(f"✅ Schema created successfully at: {DB_NAME}")
    except sqlite3.Error as e:
        print(f"❌ Error creating schema: {e}")
        raise
    finally:
        conn.close()


# ============================================================
# INSPECT SCHEMA
# ============================================================
def show_schema():
    """Print all tables, columns, indexes, and triggers."""
    conn = get_connection()
    try:
        print("\n📋 TABLES")
        print("-" * 60)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()

        for t in tables:
            print(f"\n  ▸ {t['name']}")
            cols = conn.execute(f"PRAGMA table_info({t['name']})").fetchall()
            for c in cols:
                pk = " PK" if c["pk"] else ""
                nn = " NOT NULL" if c["notnull"] else ""
                dv = f" DEFAULT {c['dflt_value']}" if c["dflt_value"] is not None else ""
                print(f"      - {c['name']:<20} {c['type']}{pk}{nn}{dv}")

        print("\n📇 INDEXES")
        print("-" * 60)
        indexes = conn.execute(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for i in indexes:
            print(f"  ▸ {i['name']:<30} (on {i['tbl_name']})")

        print("\n⚙️  TRIGGERS")
        print("-" * 60)
        triggers = conn.execute(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()
        for tr in triggers:
            print(f"  ▸ {tr['name']:<30} (on {tr['tbl_name']})")

        print()
    finally:
        conn.close()


# ============================================================
# RESET (DROP + RECREATE)
# ============================================================
def reset_schema():
    """Drop all tables and recreate the schema. ⚠️ Destroys all data."""
    confirm = input("⚠️  This will DELETE all data. Type 'yes' to continue: ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return

    conn = get_connection()
    try:
        conn.executescript("""
            DROP TRIGGER IF EXISTS trg_products_updated_at;
            DROP TABLE IF EXISTS orders;
            DROP TABLE IF EXISTS products;
            DROP TABLE IF EXISTS users;
        """)
        conn.commit()
        conn.close()
        print("🗑️  Old tables dropped.")

        create_schema()
        show_schema()
    except sqlite3.Error as e:
        print(f"❌ Error resetting schema: {e}")
        raise


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print(f"📁 Database path: {DB_NAME}")

    if os.path.exists(DB_NAME):
        print("ℹ️  Database file already exists.")
        choice = input("Do you want to (k)eep it, (r)eset it, or (q)uit? [k/r/q]: ").strip().lower()
        if choice == "r":
            reset_schema()
        elif choice == "q":
            print("Bye.")
        else:
            create_schema()
            show_schema()
    else:
        create_schema()
        show_schema()