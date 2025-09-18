# database.py
import sqlite3
import shutil
import os
from datetime import datetime
from collections import deque

DB_NAME = "materials.db"


def connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    return conn, cursor


def create_tables():
    conn, cursor = connect()

    # Materials table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            identifier TEXT UNIQUE,
            description TEXT,
            price REAL DEFAULT 0
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

    # Manufacturing orders table with client_name and proforma_number
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS manufacturing_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            units REAL NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            client_name TEXT,
            proforma_number TEXT,
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



# ------------------------
# --- Materials CRUD -----
# ------------------------

def generate_unique_identifier(base_identifier, cursor):
    """
    Dado un identificador base, añade sufijos -1, -2, etc. hasta encontrar uno libre.
    """
    if base_identifier is None:
        return None

    new_identifier = str(base_identifier)
    suffix = 1
    # mientras exista en BD, añadir sufijo
    while cursor.execute("SELECT 1 FROM Materials WHERE identifier = ?", (new_identifier,)).fetchone():
        new_identifier = f"{base_identifier}-{suffix}"
        suffix += 1
    return new_identifier


def add_material(name, description="", identifier=None, price=0.0):
    """
    Añade un nuevo material con identificador único.
    """
    conn, cursor = connect()
    try:
        # Si se da un identificador, asegurar que sea único
        final_identifier = None
        if identifier:
            final_identifier = generate_unique_identifier(identifier, cursor)

        # Intento de inserción
        cursor.execute(
            "INSERT INTO Materials (name, description, identifier, price) VALUES (?, ?, ?, ?)",
            (name, description, final_identifier, float(price))
        )
        material_id = cursor.lastrowid

        # Si no se pasó identificador, lo generamos con el propio id
        if not final_identifier:
            final_identifier = str(material_id)
            final_identifier = generate_unique_identifier(final_identifier, cursor)
            cursor.execute(
                "UPDATE Materials SET identifier = ? WHERE id = ?",
                (final_identifier, material_id)
            )

        conn.commit()
        return True

    except Exception as e:
        print("Error en add_material:", e)
        return False
    finally:
        conn.close()




def get_material_by_id(material_id):
    """Return dict-like row or None for given material id."""
    conn, cursor = connect()
    cursor.execute("SELECT id, name, identifier, description, price FROM Materials WHERE id = ?", (material_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_material(material_id, name=None, identifier=None, description=None, price=None):
    """
    Update provided fields for a material.
    If price is updated, propagate price recalculation to products that depend on this material.
    Returns True on success, False on uniqueness error.
    """
    conn, cursor = connect()
    try:
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if identifier is not None:
            updates.append("identifier = ?")
            params.append(identifier)

        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if price is not None:
            updates.append("price = ?")
            params.append(float(price))

        if updates:
            sql = "UPDATE Materials SET " + ", ".join(updates) + " WHERE id = ?"
            params.append(material_id)
            cursor.execute(sql, tuple(params))
            conn.commit()

        # If price changed (price is not None), propagate to dependent products
        if price is not None:
            propagate_price_updates([material_id])

        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# ------------------------
# --- Formulas ----------
# ------------------------
def get_formulas(product_id):
    """
    Returns a list of tuples: (ingredient_id, ingredient_name, quantity, price)
    """
    conn, cursor = connect()
    cursor.execute("""
    SELECT f.ingredient_id as ingredient_id,
           m.name as ingredient_name,
           f.quantity as quantity,
           m.price as price
    FROM Formulas f
    JOIN Materials m ON f.ingredient_id = m.id
    WHERE f.product_id = ?
    ORDER BY m.name
    """, (product_id,))
    rows = cursor.fetchall()
    conn.close()
    return [(r["ingredient_id"], r["ingredient_name"], r["quantity"], r["price"]) for r in rows]



def delete_formula(product_id):
    conn, cursor = connect()
    cursor.execute("DELETE FROM Formulas WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()


def update_formula(product_id, ingredients):
    """
    ingredients: list of (ingredient_id, quantity)
    Replaces existing formula with the new set and recalculates product price and propagates updates upstream.
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

    # After formula update, calculate price for this product and propagate (downstream)
    price = calculate_product_price(product_id)
    # Update product's price in Materials
    conn, cursor = connect()
    cursor.execute("UPDATE Materials SET price = ? WHERE id = ?", (price, product_id))
    conn.commit()
    conn.close()

    # Propagate to any products that depend on this product
    propagate_price_updates([product_id])


# ------------------------
# --- Pricing helpers ----
# ------------------------
def calculate_product_price(product_id):
    """
    Calculate product price as sum of (ingredient.price * quantity) for its formula.
    If ingredient price is NULL or zero it is treated as 0.
    Returns float total.
    """
    total = 0.0
    formula = get_formulas(product_id)
    conn, cursor = connect()
    try:
        for row in formula:
            ing_id = row[0]
            qty = row[2]  # ignore row[1] (name) or any extra fields
            cursor.execute("SELECT price FROM Materials WHERE id = ?", (ing_id,))
            r = cursor.fetchone()
            price = float(r["price"]) if r and r["price"] is not None else 0.0
            total += price * float(qty)
    finally:
        conn.close()
    return total



def get_products_using_ingredient(ingredient_id):
    """
    Return a list of product_ids that have the given ingredient in their formula.
    """
    conn, cursor = connect()
    cursor.execute("SELECT DISTINCT product_id FROM Formulas WHERE ingredient_id = ?", (ingredient_id,))
    rows = cursor.fetchall()
    conn.close()
    return [r["product_id"] for r in rows]


def propagate_price_updates(initial_product_ids):
    """
    Given a list/iterable of product ids whose price changed, recalculate prices for them (if formula exists)
    and propagate updates to any products that include them (BFS), so all upstream products get updated.
    """
    queue = deque(initial_product_ids)
    visited = set()

    conn, cursor = connect()
    try:
        while queue:
            pid = queue.popleft()
            if pid in visited:
                continue
            visited.add(pid)

            # If pid has a formula (is a processed product), recalc its price
            cursor.execute("SELECT COUNT(*) as cnt FROM Formulas WHERE product_id = ?", (pid,))
            has_formula = cursor.fetchone()["cnt"] > 0
            if has_formula:
                new_price = calculate_product_price(pid)
                cursor.execute("UPDATE Materials SET price = ? WHERE id = ?", (new_price, pid))
                conn.commit()

            # Find products that use this pid as an ingredient and enqueue them
            cursor.execute("SELECT DISTINCT product_id FROM Formulas WHERE ingredient_id = ?", (pid,))
            for row in cursor.fetchall():
                up_pid = row["product_id"]
                if up_pid not in visited:
                    queue.append(up_pid)
    finally:
        conn.close()


# ------------------------
# --- Manufacturing Orders
# ------------------------
def create_order(product_id, units, notes="", client_name=None, proforma_number=None):
    """
    Creates a manufacturing order and stores the multiplied ingredient quantities.
    Returns order_id.
    """
    conn, cursor = connect()
    try:
        # Insert the manufacturing order with all optional fields
        cursor.execute(
            """
            INSERT INTO manufacturing_orders
            (product_id, units, notes, client_name, proforma_number)
            VALUES (?, ?, ?, ?, ?)
            """,
            (product_id, units, notes, client_name, proforma_number)
        )
        order_id = cursor.lastrowid

        # Fetch formula (per-unit) and insert multiplied quantities
        formula = get_formulas(product_id)
        for ing_id, _, qty, _price in formula:
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
    Returns list of all orders:
      (order_id, product_display_name, units, date, client_name, proforma_number)
    """
    conn, cursor = connect()
    cursor.execute("""
    SELECT o.order_id,
           COALESCE(m.name, m.identifier, 'Unknown') AS product_display_name,
           o.units,
           o.date,
           o.client_name,
           o.proforma_number
    FROM manufacturing_orders o
    LEFT JOIN Materials m ON o.product_id = m.id
    ORDER BY o.date DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        (r["order_id"], r["product_display_name"], r["units"], r["date"], r["client_name"], r["proforma_number"])
        for r in rows
    ]


def search_orders(query):
    """
    Search orders by client_name OR proforma_number (case-insensitive, partial match).
    Returns same tuple structure as get_orders.
    """
    q = f"%{query}%"
    conn, cursor = connect()
    cursor.execute("""
    SELECT o.order_id,
           COALESCE(m.name, m.identifier, 'Unknown') AS product_display_name,
           o.units,
           o.date,
           o.client_name,
           o.proforma_number
    FROM manufacturing_orders o
    LEFT JOIN Materials m ON o.product_id = m.id
    WHERE (o.client_name LIKE ? OR o.proforma_number LIKE ?)
    ORDER BY o.date DESC
    """, (q, q))
    rows = cursor.fetchall()
    conn.close()
    return [
        (r["order_id"], r["product_display_name"], r["units"], r["date"], r["client_name"], r["proforma_number"])
        for r in rows
    ]


def get_order_ingredients(order_id):
    """
    Returns list of ingredients for an order: (ingredient_name, quantity)
    (kept for backward compatibility)
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


def get_order_details(order_id):
    """
    Returns (product_id, units, ingredients, client_name, proforma_number)
    Where ingredients is list of tuples (ingredient_id, name, qty)
    """
    conn, cursor = connect()
    cursor.execute(
        "SELECT product_id, units, client_name, proforma_number FROM manufacturing_orders WHERE order_id = ?",
        (order_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None, None, [], None, None

    product_id = row["product_id"]
    units = row["units"]
    client_name = row["client_name"]
    proforma_number = row["proforma_number"]

    cursor.execute("""
        SELECT oi.ingredient_id, m.name as ingredient_name, oi.quantity
        FROM order_ingredients oi
        JOIN Materials m ON oi.ingredient_id = m.id
        WHERE oi.order_id = ?
        ORDER BY m.name
    """, (order_id,))
    ingredients = [(r["ingredient_id"], r["ingredient_name"], r["quantity"]) for r in cursor.fetchall()]

    conn.close()
    return product_id, units, ingredients, client_name, proforma_number





def get_order_info(order_id):
    """
    Returns metadata for an order:
      (product_id, units, date, client_name, proforma_number)
    """
    conn, cursor = connect()
    cursor.execute("""
    SELECT product_id, units, date, client_name, proforma_number
    FROM manufacturing_orders
    WHERE order_id = ?
    """, (order_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None, None, None, None, None
    return row["product_id"], row["units"], row["date"], row["client_name"], row["proforma_number"]


def get_next_order_id():
    conn, cursor = connect()
    cursor.execute("SELECT MAX(order_id) + 1 FROM manufacturing_orders")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else 1


# ------------------------
# --- Utilities ----------
# ------------------------
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



def get_materials():
    conn, cursor = connect()
    cursor.execute("SELECT id, name, identifier, price FROM materials ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return rows
