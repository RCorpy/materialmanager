import sqlite3

DB_NAME = "materials.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Show orders and their product names (if exist)
print("Before cleanup:")
for row in cursor.execute("""
    SELECT o.order_id, o.product_id, m.id, m.name
    FROM manufacturing_orders o
    LEFT JOIN Materials m ON o.product_id = m.id
"""):
    print(row)

# Delete invalid orders (with missing product)
cursor.execute("""
    DELETE FROM manufacturing_orders
    WHERE product_id NOT IN (SELECT id FROM Materials)
""")
conn.commit()

print("\nAfter cleanup:")
for row in cursor.execute("""
    SELECT o.order_id, o.product_id, m.id, m.name
    FROM manufacturing_orders o
    LEFT JOIN Materials m ON o.product_id = m.id
"""):
    print(row)

conn.close()
