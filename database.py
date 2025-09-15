import sqlite3
import shutil
import os
from datetime import datetime

DB_NAME = "materials.db"


def connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    return conn, cursor


def create_tables():
    conn, cursor = connect()

    # Materials table with optional identifier
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        material_identifier TEXT UNIQUE,
        description TEXT
    );
    """)

    # Formulas table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Formulas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        ingredient_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        FOREIGN KEY (product_id) REFERENCES Materials(id),
        FOREIGN KEY (ingredient_id) REFERENCES Materials(id)
    );
    """)

    # Manufacturing orders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS manufacturing_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        units REAL NOT NULL,
        date TEXT DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY(product_id) REFERENCES Materials(id)
    );
    """)

    # Order ingredients table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        ingredient_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES manufacturing_orders(order_id),
        FOREIGN KEY(ingredient_id) REFERENCES Materials(id)
    );
    """)

    conn.commit()
    conn.close()


# --- Materials ---
def add_material(name, description="", identifier=None):
    conn, cursor = connect()
    try:
        cursor.execute(
            "INSERT INTO Materials (name, description, material_identifier) VALUES (?, ?, ?)",
            (name, description, identifier)
        )
        material_id = cursor.lastrowid
        if not identifier:
            # default to material_id if no identifier provided
            cursor.execute(
                "UPDATE Materials SET material_identifier = ? WHERE id = ?",
                (str(material_id), material_id)
            )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_materials():
    conn, cursor = connect()
    cursor.execute("SELECT id, name, material_identifier FROM Materials ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [(r["id"], r["name"], r["material_identifier"]) for r in rows]


# --- Formulas ---
def get_formulas(product_id):
    """
    Returns a list of tuples: (ingredient_id, ingredient_name, quantity)
    """
    conn, cursor = connect()
    cursor.execute("""
    SELECT f.ingredient_id as ingredient_id,
           m.name as ingredient_name,
           f.quantity as quantity
    FROM Formulas f
    JOIN Materials m ON f.ingredient_id = m.id
    WHERE f.product_id = ?
    ORDER BY m.name
    """, (product_id,))
    rows = cursor.fetchall()
    conn.close()
    return [(r["ingredient_id"], r["ingredient_name"], r["quantity"]) for r in rows]


def delete_formula(product_id):
    conn, cursor = connect()
    cursor.execute("DELETE FROM Formulas WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()


def update_formula(product_id, ingredients):
    """
    ingredients: list of (ingredient_id, quantity)
    This replaces existing formula with the new set in a transaction.
    """
    conn, cursor = connect()
    try:
        cursor.execute("BEGIN")
        cursor.execute("DELETE FROM Formulas WHERE product_id = ?", (product_id,))
        if ingredients:
            cursor.executemany(
                "INSERT INTO Formulas (product_id, ingredient_id, quantity) VALUES (?, ?, ?)",
                [(product_id, ing_id, qty) for ing_id, qty in ingredients]
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Manufacturing Orders ---
def create_order(product_id, units, notes=""):
    """
    Creates a manufacturing order, multiplies formula quantities by units
    """
    conn, cursor = connect()
    try:
        # Insert order
        cursor.execute(
            "INSERT INTO manufacturing_orders (product_id, units, notes) VALUES (?, ?, ?)",
            (product_id, units, notes)
        )
        order_id = cursor.lastrowid

        # Fetch formula
        formula = get_formulas(product_id)
        for ing_id, _, qty in formula:
            total_qty = qty * units
            cursor.execute(
                "INSERT INTO order_ingredients (order_id, ingredient_id, quantity) VALUES (?, ?, ?)",
                (order_id, ing_id, total_qty)
            )

        conn.commit()
        return order_id
    finally:
        conn.close()


def get_orders():
    """
    Returns list of all orders: (order_id, product_display_name, units, date)
    """
    conn, cursor = connect()
    cursor.execute("""
    SELECT o.order_id,
           COALESCE(m.name, m.material_identifier, 'Unknown') AS product_display_name,
           o.units,
           o.date
    FROM manufacturing_orders o
    LEFT JOIN Materials m ON o.product_id = m.id
    ORDER BY o.date DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [(r["order_id"], r["product_display_name"], r["units"], r["date"]) for r in rows]




def get_order_ingredients(order_id):
    """
    Returns list of ingredients for an order: (ingredient_name, quantity)
    """
    conn, cursor = connect()
    cursor.execute("""
    SELECT m.name as ingredient_name, oi.quantity
    FROM order_ingredients oi
    JOIN Materials m ON oi.ingredient_id = m.id
    WHERE oi.order_id = ?
    """, (order_id,))
    rows = cursor.fetchall()
    conn.close()
    return [(r["ingredient_name"], r["quantity"]) for r in rows]



# --- Helpers for ManufacturingOrderFrame ---

def get_material_name(product_id):
    """Return the name of a material given its ID."""
    conn, cursor = connect()
    cursor.execute("SELECT name FROM Materials WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    return row["name"] if row else None


def get_order_details(order_id):
    """
    Returns: product_id, units, list of ingredients [(ingredient_id, name, qty)]
    """
    conn, cursor = connect()
    # Get product_id and units
    cursor.execute(
        "SELECT product_id, units FROM manufacturing_orders WHERE order_id = ?",
        (order_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None, None, []

    product_id, units = row["product_id"], row["units"]

    # Get ingredients
    cursor.execute("""
        SELECT oi.ingredient_id, m.name as ingredient_name, oi.quantity
        FROM order_ingredients oi
        JOIN Materials m ON oi.ingredient_id = m.id
        WHERE oi.order_id = ?
        ORDER BY m.name
    """, (order_id,))
    ingredients = [(r["ingredient_id"], r["ingredient_name"], r["quantity"]) for r in cursor.fetchall()]

    conn.close()
    return product_id, units, ingredients

def get_next_order_id():
    conn, cursor = connect()
    cursor.execute("SELECT MAX(order_id) + 1 FROM manufacturing_orders")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else 1

def backup_database(destination_folder=None):
    """
    Creates a backup of the current database.
    If destination_folder is None, saves it in the current directory with timestamp.
    Returns the path of the backup file.
    """
    if not os.path.exists(DB_NAME):
        raise FileNotFoundError(f"{DB_NAME} does not exist.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"materials_backup_{timestamp}.db"

    if destination_folder:
        os.makedirs(destination_folder, exist_ok=True)
        backup_path = os.path.join(destination_folder, backup_name)
    else:
        backup_path = backup_name

    shutil.copy2(DB_NAME, backup_path)
    return backup_path