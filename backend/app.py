import os
import sqlite3
import secrets
import hashlib
from functools import wraps

from flask import Flask, jsonify, request


# ==========================================
# APP
# ==========================================

app = Flask(__name__)

DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(
        os.path.dirname(__file__),
        "menu.db"
    )
)


# ==========================================
# DATABASE
# ==========================================

def get_db():

    db = sqlite3.connect(DATABASE)

    db.row_factory = sqlite3.Row

    return db


def init_db():

    db = get_db()

    db.executescript("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price INTEGER NOT NULL DEFAULT 0,
            available INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,

            FOREIGN KEY(category_id)
            REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            admin_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(admin_id)
            REFERENCES admins(id)
        );
    """)

    admin = db.execute(
        "SELECT id FROM admins LIMIT 1"
    ).fetchone()

    if admin is None:

        username = os.environ.get(
            "ADMIN_USERNAME",
            "admin"
        )

        password = os.environ.get("ADMIN_PASSWORD")
        if not password:
            raise RuntimeError("ADMIN_PASSWORD environment variable is required")

        password_hash = hash_password(password)

        db.execute(
            """
            INSERT INTO admins
            (username, password_hash)
            VALUES (?, ?)
            """,
            (
                username,
                password_hash
            )
        )


    category_count = db.execute(
        "SELECT COUNT(*) AS count FROM categories"
    ).fetchone()["count"]


    if category_count == 0:

        categories = [
            ("پاستا", 1),
            ("کباب", 2),
            ("پیتزا", 3),
            ("غذاهای اصلی", 4),
            ("نوشیدنی", 5)
        ]

        db.executemany(
            """
            INSERT INTO categories
            (name, sort_order)
            VALUES (?, ?)
            """,
            categories
        )


    db.commit()

    db.close()


# ==========================================
# PASSWORD
# ==========================================

def hash_password(password):

    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# ==========================================
# AUTH
# ==========================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        auth = request.headers.get(
                "Authorization",
                ""
            )

        if not auth.startswith("Bearer "):

            return jsonify({
                "message":
                    "احراز هویت لازم است."
            }), 401


        token = auth.replace(
            "Bearer ",
            "",
            1
        ).strip()


        if not token:

            return jsonify({
                "message":
                    "توکن نامعتبر است."
            }), 401


        db = get_db()

        session = db.execute(
            """
            SELECT id
            FROM sessions
            WHERE token = ?
            """,
            (token,)
        ).fetchone()

        db.close()


        if session is None:

            return jsonify({
                "message":
                    "نشست شما منقضی شده است."
            }), 401


        return function(*args, **kwargs)

    return wrapper


# ==========================================
# CORS
# ==========================================

@app.after_request
def add_cors(response):

    response.headers[
        "Access-Control-Allow-Origin"
    ] = "*"

    response.headers[
        "Access-Control-Allow-Headers"
    ] = (
        "Content-Type, "
        "Authorization"
    )

    response.headers[
        "Access-Control-Allow-Methods"
    ] = (
        "GET, POST, PATCH, "
        "DELETE, OPTIONS"
    )

    return response


# ==========================================
# LOGIN
# ==========================================

@app.post("/api/auth/login")
def login():

    data = request.get_json(
        silent=True
    ) or {}


    username = str(
        data.get("username", "")
    ).strip()


    password = str(
        data.get("password", "")
    )


    if not username or not password:

        return jsonify({
            "message":
                "نام کاربری و رمز عبور لازم است."
        }), 400


    db = get_db()


    admin = db.execute(
        """
        SELECT *
        FROM admins
        WHERE username = ?
        """,
        (username,)
    ).fetchone()


    if admin is None:

        db.close()

        return jsonify({
            "message":
                "نام کاربری یا رمز عبور اشتباه است."
        }), 401


    password_hash = hash_password(password)


    if password_hash != admin["password_hash"]:

        db.close()

        return jsonify({
            "message":
                "نام کاربری یا رمز عبور اشتباه است."
        }), 401


    token = secrets.token_urlsafe(48)


    db.execute(
        """
        INSERT INTO sessions
        (token, admin_id)
        VALUES (?, ?)
        """,
        (
            token,
            admin["id"]
        )
    )


    db.commit()

    db.close()


    return jsonify({
        "success": True,
        "token": token
    })


# ==========================================
# LOGOUT
# ==========================================

@app.post("/api/auth/logout")
@admin_required
def logout():

    auth = request.headers.get(
            "Authorization",
            ""
        )

    token = auth.replace(
        "Bearer ",
        "",
        1
    ).strip()


    db = get_db()

    db.execute(
        """
        DELETE FROM sessions
        WHERE token = ?
        """,
        (token,)
    )

    db.commit()

    db.close()


    return jsonify({
        "success": True
    })


# ==========================================
# PUBLIC MENU
# ==========================================

@app.get("/api/menu")
def public_menu():

    db = get_db()


    categories = db.execute(
        """
        SELECT
            id,
            name,
            sort_order
        FROM categories
        WHERE active = 1
        ORDER BY sort_order, id
        """
    ).fetchall()


    products = db.execute(
        """
        SELECT
            id,
            category_id,
            name,
            description,
            price,
            available,
            sort_order
        FROM products
        WHERE active = 1
        ORDER BY sort_order, id
        """
    ).fetchall()


    db.close()


    return jsonify({

        "categories": [
            dict(row)
            for row in categories
        ],

        "products": [
            {
                **dict(row),
                "available":
                    bool(row["available"])
            }
            for row in products
        ]

    })


# ==========================================
# ADMIN MENU
# ==========================================

@app.get("/api/admin/menu")
@admin_required
def admin_menu():

    db = get_db()


    categories = db.execute(
        """
        SELECT *
        FROM categories
        ORDER BY sort_order, id
        """
    ).fetchall()


    products = db.execute(
        """
        SELECT *
        FROM products
        ORDER BY sort_order, id
        """
    ).fetchall()


    db.close()


    return jsonify({

        "categories": [
            dict(row)
            for row in categories
        ],

        "products": [
            {
                **dict(row),
                "available":
                    bool(row["available"]),
                "active":
                    bool(row["active"])
            }
            for row in products
        ]

    })


# ==========================================
# ADD CATEGORY
# ==========================================

@app.post("/api/admin/categories")
@admin_required
def add_category():

    data = request.get_json(
        silent=True
    ) or {}


    name = str(
        data.get("name", "")
    ).strip()


    if not name:

        return jsonify({
            "message":
                "نام دسته الزامی است."
        }), 400


    db = get_db()


    max_order = db.execute(
        """
        SELECT COALESCE(
            MAX(sort_order),
            0
        ) AS value
        FROM categories
        """
    ).fetchone()["value"]


    cursor = db.execute(
        """
        INSERT INTO categories
        (name, sort_order)
        VALUES (?, ?)
        """,
        (
            name,
            max_order + 1
        )
    )


    db.commit()

    category_id = cursor.lastrowid

    db.close()


    return jsonify({
        "success": True,
        "id": category_id
    }), 201


# ==========================================
# EDIT CATEGORY
# ==========================================

@app.patch("/api/admin/categories/<int:category_id>")
@admin_required
def edit_category(category_id):

    data = request.get_json(
        silent=True
    ) or {}


    name = str(
        data.get("name", "")
    ).strip()


    if not name:

        return jsonify({
            "message":
                "نام دسته الزامی است."
        }), 400


    db = get_db()


    cursor = db.execute(
        """
        UPDATE categories
        SET name = ?
        WHERE id = ?
        """,
        (
            name,
            category_id
        )
    )


    db.commit()

    db.close()


    if cursor.rowcount == 0:

        return jsonify({
            "message":
                "دسته پیدا نشد."
        }), 404


    return jsonify({
        "success": True
    })


# ==========================================
# DELETE CATEGORY
# ==========================================

@app.delete(
    "/api/admin/categories/<int:category_id>"
)
@admin_required
def delete_category(category_id):

    db = get_db()


    product_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM products
        WHERE category_id = ?
        """,
        (category_id,)
    ).fetchone()["count"]


    if product_count > 0:

        db.close()

        return jsonify({
            "message":
                "ابتدا محصولات این دسته را حذف یا منتقل کنید."
        }), 400


    cursor = db.execute(
        """
        DELETE FROM categories
        WHERE id = ?
        """,
        (category_id,)
    )


    db.commit()

    db.close()


    if cursor.rowcount == 0:

        return jsonify({
            "message":
                "دسته پیدا نشد."
        }), 404


    return jsonify({
        "success": True
    })


# ==========================================
# ADD PRODUCT
# ==========================================

@app.post("/api/admin/products")
@admin_required
def add_product():

    data = request.get_json(
        silent=True
    ) or {}


    name = str(
        data.get("name", "")
    ).strip()


    description = str(
        data.get("description", "")
    ).strip()


    try:
        price = int(
            data.get("price", 0)
        )

        category_id = int(
            data.get("category_id")
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "message":
                "اطلاعات محصول نامعتبر است."
        }), 400


    if not name:

        return jsonify({
            "message":
                "نام محصول الزامی است."
        }), 400


    if price < 0:

        return jsonify({
            "message":
                "قیمت نمی‌تواند منفی باشد."
        }), 400


    db = get_db()


    category = db.execute(
        """
        SELECT id
        FROM categories
        WHERE id = ?
        """,
        (category_id,)
    ).fetchone()


    if category is None:

        db.close()

        return jsonify({
            "message":
                "دسته‌بندی پیدا نشد."
        }), 404


    cursor = db.execute(
        """
        INSERT INTO products
        (
            category_id,
            name,
            description,
            price,
            available,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            category_id,
            name,
            description,
            price,
            1,
            1
        )
    )


    db.commit()

    product_id = cursor.lastrowid

    db.close()


    return jsonify({
        "success": True,
        "id": product_id
    }), 201


# ==========================================
# EDIT PRODUCT
# ==========================================

@app.patch(
    "/api/admin/products/<int:product_id>"
)
@admin_required
def edit_product(product_id):

    data = request.get_json(
        silent=True
    ) or {}


    fields = []
    values = []


    if "name" in data:

        name = str(
            data["name"]
        ).strip()

        if not name:

            return jsonify({
                "message":
                    "نام محصول نمی‌تواند خالی باشد."
            }), 400

        fields.append("name = ?")
        values.append(name)


    if "description" in data:

        fields.append(
            "description = ?"
        )

        values.append(
            str(
                data["description"]
            ).strip()
        )


    if "price" in data:

        try:
            price = int(
                data["price"]
            )
        except (
            TypeError,
            ValueError
        ):

            return jsonify({
                "message":
                    "قیمت نامعتبر است."
            }), 400


        if price < 0:

            return jsonify({
                "message":
                    "قیمت نمی‌تواند منفی باشد."
            }), 400


        fields.append(
            "price = ?"
        )

        values.append(price)


    if "category_id" in data:

        try:
            category_id = int(
                data["category_id"]
            )
        except (
            TypeError,
            ValueError
        ):

            return jsonify({
                "message":
                    "دسته‌بندی نامعتبر است."
            }), 400


        fields.append(
            "category_id = ?"
        )

        values.append(category_id)


    if not fields:

        return jsonify({
            "message":
                "هیچ تغییری ارسال نشده."
        }), 400


    values.append(product_id)


    db = get_db()


    cursor = db.execute(
        f"""
        UPDATE products
        SET {", ".join(fields)}
        WHERE id = ?
        """,
        values
    )


    db.commit()

    db.close()


    if cursor.rowcount == 0:

        return jsonify({
            "message":
                "محصول پیدا نشد."
        }), 404


    return jsonify({
        "success": True
    })


# ==========================================
# TOGGLE PRODUCT
# ==========================================

@app.patch(
    "/api/admin/products/<int:product_id>/toggle"
)
@admin_required
def toggle_product(product_id):

    db = get_db()


    product = db.execute(
        """
        SELECT available
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()


    if product is None:

        db.close()

        return jsonify({
            "message":
                "محصول پیدا نشد."
        }), 404


    new_status = 0 if product["available"] else 1


    db.execute(
        """
        UPDATE products
        SET available = ?
        WHERE id = ?
        """,
        (
            new_status,
            product_id
        )
    )


    db.commit()

    db.close()


    return jsonify({
        "success": True,
        "available":
            bool(new_status)
    })


# ==========================================
# DELETE PRODUCT
# ==========================================

@app.delete(
    "/api/admin/products/<int:product_id>"
)
@admin_required
def delete_product(product_id):

    db = get_db()


    cursor = db.execute(
        """
        DELETE FROM products
        WHERE id = ?
        """,
        (product_id,)
    )


    db.commit()

    db.close()


    if cursor.rowcount == 0:

        return jsonify({
            "message":
                "محصول پیدا نشد."
        }), 404


    return jsonify({
        "success": True
    })


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/")
def home():

    return jsonify({
        "status": "online",
        "service": "restaurant-menu-api"
    })


@app.get("/health")
def health():

    return jsonify({
        "status": "ok"
    })


# ==========================================
# START
# ==========================================

init_db()


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
