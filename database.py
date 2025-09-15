import sqlite3

DB_NAME = "materials.db"

def connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    return conn, cursor

def create_tables():
    conn, cursor = connect()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
    );
    """)
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
    conn.commit()
    conn.close()

# --- Materials ---
def add_material(name, description=""):
    conn, cursor = connect()
    try:
        cursor.execute("INSERT INTO Materials (name, description) VALUES (?, ?)", (name, description))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_materials():
    conn, cursor = connect()
    cursor.execute("SELECT id, name FROM Materials ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [(r["id"], r["name"]) for r in rows]

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
