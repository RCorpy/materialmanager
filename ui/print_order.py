from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import tempfile
import os
from datetime import datetime
import database

def print_orders(order_ids):
    """Print multiple manufacturing orders, each on its own page (portrait A4)."""
    if not order_ids:
        return

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = tmp_file.name
    tmp_file.close()

    # Portrait A4
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    margin_left = 40
    margin_right = 70
    table_row_height = 22  # slightly taller for bigger font

    for order_id in order_ids:
        product_id, units, ingredients = database.get_order_details(order_id)
        product_name = database.get_material_name(product_id)

        ts = next((t for oid, pname, u, t in database.get_orders() if oid == order_id), "")
        ts_fmt = format_date(ts)

        # -----------------------------
        # Top section: Material & Units
        # -----------------------------
        y = height - 50
        c.setFont("Helvetica-Bold", 24)
        c.drawString(margin_left, y, f"Material: {product_name}")
        c.setFont("Helvetica-Bold", 24)
        c.drawRightString(width - margin_right, y, f"Units: {units}")
        y -= 32

        c.setFont("Helvetica", 16)
        c.drawString(margin_left, y, f"Manufacturing Order: {order_id}")
        c.drawRightString(width - margin_right, y, f"Date: {ts_fmt}")
        y -= 42

        # -----------------------------
        # Table header
        # -----------------------------
        c.setFont("Helvetica-Bold", 20)
        col_id_width = 40
        col_qty_width = 60
        x_id_left = margin_left
        x_id_right = width - margin_right
        x_qty = x_id_right - col_qty_width
        x_ingredient = x_id_left + col_id_width + 10
        ingredient_width = x_qty - x_ingredient - 10

        c.drawString(x_id_left, y, "ID")
        c.drawString(x_ingredient, y, "Ingredient")
        c.drawRightString(x_qty + col_qty_width / 2, y, "Qty")
        c.drawString(x_id_right, y, "ID")
        y -= 18

        # Horizontal line separating headers from rows
        c.line(margin_left, y, width - margin_right, y)
        y -= 25  # more space between header and first row

        # -----------------------------
        # Table rows
        # -----------------------------
        c.setFont("Helvetica", 17)
        table_row_height = 30  # increased spacing
        for i, (ing_id, ing_name, qty) in enumerate(ingredients):
            identifier = next((midf for mid, mname, midf in database.get_materials() if mid == ing_id), "")
            c.drawString(x_id_left, y, str(identifier))
            c.drawString(x_ingredient, y, ing_name)
            c.drawRightString(x_qty + col_qty_width / 2, y, f"{qty:.3f}")
            c.drawString(x_id_right, y, str(identifier))
            y -= table_row_height

            # Add page break if close to bottom
            if y < 50:
                c.showPage()
                y = height - 50


        c.showPage()  # next order

    c.save()
    os.startfile(pdf_path, "open")


def format_date(ts):
    """Return ts as DD-MM-YYYY"""
    if not ts:
        return ""
    candidates = ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f"]
    for fmt in candidates:
        try:
            dt = datetime.strptime(ts, fmt)
            return dt.strftime("%d-%m-%Y")
        except Exception:
            pass
    return str(ts)
