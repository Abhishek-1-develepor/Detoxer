"""
app.py — Flask backend for Detoxer.

Clean version — no seed data. Users register themselves, admins add products.
"""

import os
import sqlite3
import hashlib
from pathlib import Path
from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for
)

import nltk

NLTK_DATA_DIR = os.path.join(os.path.dirname(__file__), "nltk_data")
os.makedirs(NLTK_DATA_DIR, exist_ok=True)

if NLTK_DATA_DIR not in nltk.data.path:
    nltk.data.path.insert(0, NLTK_DATA_DIR)

for pkg in ["punkt", "punkt_tab", "stopwords"]:
    try:
        nltk.data.find(
            f"tokenizers/{pkg}" if pkg.startswith("punkt") else f"corpora/{pkg}"
        )
    except LookupError:
        try:
            nltk.download(pkg, download_dir=NLTK_DATA_DIR, quiet=True)
            print(f"[NLTK] Downloaded {pkg}")
        except Exception as e:
            print(f"[NLTK] Failed to download {pkg}: {e}")

# ============================================================
# ML IMPORT — after NLTK is ready
# ============================================================
from ml.report import build_review_report


# ============================================================
# APP SETUP
# ============================================================
app = Flask(__name__)
app.secret_key = "detoxer-secret-key-2026"

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = str(BASE_DIR / "app.db")


# ============================================================
# DB CONNECTION
# ============================================================
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ============================================================
# SECURITY
# ============================================================
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + dk.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return dk.hex() == hash_hex
    except Exception:
        return False


# ============================================================
# SCHEMA (only create if missing — no seed data)
# ============================================================
def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL CHECK (role IN ('admin', 'user')),
            created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active     INTEGER NOT NULL DEFAULT 1
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name        TEXT    NOT NULL,
            category            TEXT    NOT NULL DEFAULT 'General',
            product_description TEXT,
            price               REAL    NOT NULL CHECK (price >= 0),
            stock_quantity      INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
            status              TEXT    NOT NULL DEFAULT 'In Stock',
            image_url           TEXT,
            review              TEXT,
            created_at          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            review_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER NOT NULL,
            user_id     INTEGER,
            username    TEXT    NOT NULL DEFAULT 'Guest',
            rating      INTEGER NOT NULL DEFAULT 5 CHECK (rating BETWEEN 1 AND 5),
            review_text TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")

    conn.commit()
    conn.close()


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,)
    ).fetchone()
    return bool(row)


# ============================================================
# USER HELPERS
# ============================================================
def create_user(username: str, password: str, role: str = "user"):
    if not username or not password:
        return {"success": False, "message": "Username and password are required"}

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hash_password(password), role)
        )
        conn.commit()
        return {"success": True, "message": f"{role.capitalize()} registered successfully"}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "Username already exists"}
    finally:
        conn.close()


def login_user(username: str, password: str):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND is_active = 1",
        (username,)
    ).fetchone()
    conn.close()

    if not user:
        return {"success": False, "message": "User not found"}
    if not verify_password(password, user["password_hash"]):
        return {"success": False, "message": "Incorrect password"}

    return {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        }
    }


# ============================================================
# PRODUCT HELPERS
# ============================================================
def normalize_product_row(row):
    return {
        "id": row["product_id"],
        "name": row["product_name"],
        "category": row["category"],
        "description": row["product_description"] or "",
        "price": row["price"],
        "stock": row["stock_quantity"],
        "status": row["status"],
        "image_url": row["image_url"] or "",
        "review": row["review"] or "",
    }


def get_products():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM products ORDER BY product_id DESC"
    ).fetchall()
    conn.close()
    return [normalize_product_row(r) for r in rows]


def add_product(data):
    name = str(data.get("product_name", "")).strip()
    if not name:
        return {"success": False, "message": "Product name is required"}

    conn = get_db_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO products
              (product_name, category, product_description, price,
               stock_quantity, status, image_url, review)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                str(data.get("category", "General")).strip() or "General",
                str(data.get("product_description", "")).strip(),
                float(data.get("price", 0) or 0),
                int(data.get("stock_quantity", 0) or 0),
                str(data.get("status", "In Stock")).strip() or "In Stock",
                str(data.get("image_url", "")).strip(),
                str(data.get("review", "")).strip(),
            ),
        )
        conn.commit()
        return {"success": True, "message": "Product added", "id": cur.lastrowid}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def update_product(pid, data):
    mapping = {
        "product_name": "product_name",
        "category": "category",
        "product_description": "product_description",
        "price": "price",
        "stock_quantity": "stock_quantity",
        "status": "status",
        "image_url": "image_url",
        "review": "review",
    }
    fields, values = [], []
    for k, col in mapping.items():
        if k in data and data[k] is not None:
            fields.append(f"{col} = ?")
            values.append(data[k])

    if not fields:
        return {"success": False, "message": "No fields to update"}

    values.append(pid)
    conn = get_db_connection()
    try:
        conn.execute(
            f"UPDATE products SET {', '.join(fields)} WHERE product_id = ?", values
        )
        conn.commit()
        return {"success": True, "message": "Product updated"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def delete_product(pid):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM products WHERE product_id = ?", (pid,))
        conn.commit()
        return {"success": True, "message": "Product deleted"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


# ============================================================
# ROUTES — PAGES
# ============================================================
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dashboard")
@app.route("/dashboard.html")
def dashboard():
    """Admin dashboard — no seeding, just fetch what exists."""
    products = get_products()
    return render_template("dashboard.html", products=products)


@app.route("/products")
@app.route("/products.html")
def user_products():
    """User-facing store page — product grid + review form."""
    products = get_products()
    featured = products[0] if products else None

    conn = get_db_connection()
    if _table_exists(conn, "reviews"):
        reviews = [dict(r) for r in conn.execute(
            "SELECT * FROM reviews ORDER BY created_at DESC LIMIT 20"
        ).fetchall()]
    else:
        reviews = []
    conn.close()

    avg_rating = (
        round(sum(r["rating"] for r in reviews) / len(reviews), 1)
        if reviews else 0
    )

    cart = session.get("cart", {})
    cart_count = sum(cart.values()) if cart else 0

    return render_template(
        "products.html",
        products=products,
        featured=featured,
        reviews=reviews,
        avg_rating=avg_rating,
        cart_count=cart_count,
    )


@app.route("/orders")
def orders():
    return render_template("orders.html", orders=session.get("orders", []))


# ============================================================
# ROUTES — AUTH
# ============================================================
@app.route("/register", methods=["POST"])
def register():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    role     = str(data.get("role", "user")).strip().lower()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400
    if role not in ("user", "admin"):
        return jsonify({"success": False, "message": "Role must be user or admin"}), 400

    result = create_user(username, password, role)
    if not result["success"]:
        return jsonify(result), 409
    return jsonify(result)


@app.route("/login", methods=["POST"])
def login():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    role     = str(data.get("role", "user")).strip().lower()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    result = login_user(username, password)
    if not result["success"]:
        return jsonify(result), 401
    if result["user"]["role"] != role:
        return jsonify({"success": False, "message": "Role does not match"}), 401

    session["user_id"]  = result["user"]["id"]
    session["username"] = result["user"]["username"]
    session["role"]     = result["user"]["role"]

    return jsonify(result)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ============================================================
# ROUTES — CART
# ============================================================
@app.route("/cart/add", methods=["POST"])
def cart_add():
    data = request.get_json(silent=True) or {}
    pid = str(data.get("product_id", "")).strip()
    qty = int(data.get("quantity", 1) or 1)

    if not pid:
        return jsonify({"success": False, "message": "Missing product"}), 400

    cart = session.get("cart", {})
    cart[pid] = cart.get(pid, 0) + qty
    session["cart"] = cart

    return jsonify({"success": True, "cart_count": sum(cart.values())})


@app.route("/cart", methods=["GET"])
def cart_view():
    return jsonify({"success": True, "cart": session.get("cart", {})})


# ============================================================
# ROUTES — ORDERS
# ============================================================
@app.route("/order/create", methods=["POST"])
def order_create():
    data = request.get_json(silent=True) or {}
    try:
        pid = int(data.get("product_id", 0))
        qty = int(data.get("quantity", 1) or 1)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid product or quantity"}), 400

    if qty < 1:
        return jsonify({"success": False, "message": "Quantity must be at least 1"}), 400

    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE product_id = ?", (pid,)
    ).fetchone()

    if not product:
        conn.close()
        return jsonify({"success": False, "message": "Product not found"}), 404

    if product["stock_quantity"] < qty:
        conn.close()
        return jsonify({"success": False, "message": "Not enough stock"}), 400

    new_stock = product["stock_quantity"] - qty
    if new_stock == 0 or new_stock < 10:
        new_status = "Critical"
    elif new_stock < 20:
        new_status = "Low Stock"
    else:
        new_status = "In Stock"

    conn.execute(
        "UPDATE products SET stock_quantity = ?, status = ? WHERE product_id = ?",
        (new_stock, new_status, pid)
    )
    conn.commit()
    conn.close()

    orders = session.get("orders", [])
    orders.append({
        "product_id": pid,
        "name": product["product_name"],
        "quantity": qty,
        "unit_price": product["price"],
        "total": product["price"] * qty,
    })
    session["orders"] = orders

    return jsonify({"success": True, "message": "Order placed"})


# ============================================================
# ROUTES — REVIEWS
# ============================================================
@app.route("/product/<int:pid>/review", methods=["POST"])
def submit_review(pid):
    data = request.form if request.form else (request.get_json(silent=True) or {})
    rating = int(data.get("rating", 5) or 5)
    text   = str(data.get("review_text", "")).strip()

    if not text:
        return jsonify({"success": False, "message": "Review text is required"}), 400

    if rating < 1 or rating > 5:
        rating = 5

    conn = get_db_connection()
    try:
        exists = conn.execute(
            "SELECT 1 FROM products WHERE product_id = ?", (pid,)
        ).fetchone()
        if not exists:
            return jsonify({"success": False, "message": "Product not found"}), 404

        conn.execute(
            """
            INSERT INTO reviews (product_id, user_id, username, rating, review_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (pid, session.get("user_id"), session.get("username", "Guest"), rating, text)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Review submitted"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/product/<int:pid>/reviews", methods=["GET"])
def product_reviews(pid):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM reviews WHERE product_id = ? ORDER BY created_at DESC",
        (pid,)
    ).fetchall()
    conn.close()
    return jsonify({"success": True, "reviews": [dict(r) for r in rows]})


# ============================================================
# ROUTES — ADMIN ML REVIEW ANALYSIS
# ============================================================
@app.route("/admin/product/<int:pid>/reviews")
def admin_product_reviews(pid):
    """ML analysis report for a single product's reviews."""
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE product_id = ?", (pid,)
    ).fetchone()
    if not product:
        conn.close()
        return "Product not found", 404

    reviews = [dict(r) for r in conn.execute(
        "SELECT * FROM reviews WHERE product_id = ? ORDER BY created_at DESC",
        (pid,)
    ).fetchall()]
    conn.close()

    report = build_review_report(reviews)

    return render_template(
        "admin_ml_reviews.html",
        product=dict(product),
        report=report,
    )


# ============================================================
# ROUTES — API (admin product CRUD)
# ============================================================
@app.route("/api/products", methods=["GET"])
def api_list_products():
    return jsonify(get_products())


@app.route("/api/products", methods=["POST"])
def api_create_product():
    data = request.get_json(silent=True) or {}
    result = add_product(data)
    return jsonify(result), (201 if result["success"] else 400)


@app.route("/api/products/<int:pid>", methods=["PUT"])
def api_update_product(pid):
    data = request.get_json(silent=True) or {}
    result = update_product(pid, data)
    return jsonify(result), (200 if result["success"] else 400)


@app.route("/api/products/<int:pid>", methods=["DELETE"])
def api_delete_product(pid):
    result = delete_product(pid)
    return jsonify(result), (200 if result["success"] else 400)


# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    init_db()   # only creates tables, no seeding

    print("\n=== REGISTERED ROUTES ===")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
        print(f"  {str(rule):<45} → {rule.endpoint}")
    print("=========================\n")

    app.run(debug=True, port=5000)