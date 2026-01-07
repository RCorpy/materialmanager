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

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    margin_left = 40
    margin_right = 70

    for order_id in order_ids:
        product_id, units, ingredients, client_name, proforma_number = database.get_order_details(order_id)
        product = database.get_material_by_id(product_id)
        product_name = product["name"] if product else "ERROR"
        is_kit = "KIT" in product_name.upper()

        ts = next((t for oid, pname, u, t, cl, pf in database.get_orders() if oid == order_id), "")
        ts_fmt = format_date(ts)

        # ============================
        # CASO 1: PRODUCTO NORMAL
        # ============================
        if not is_kit:
            y = height - 50

            # --- Cabecera ---
            c.setFont("Helvetica-Bold", 21)
            c.drawString(margin_left, y, f"Orden de fabricación: {order_id}")
            y -= 28

            c.setFont("Helvetica", 13)
            c.drawString(margin_left, y, f"Cliente: {client_name or '-'}")
            c.drawRightString(width - margin_right, y, f"Fecha: {ts_fmt}")
            y -= 18

            c.drawString(margin_left, y, f"Proforma: {proforma_number or '-'}")
            y -= 30

            # --- Producto principal ---
            c.setFont("Helvetica-Bold", 15)
            c.line(margin_left, y, width - margin_right, y)
            y -= 22
            c.drawString(margin_left, y, product_name)
            c.drawRightString(width - margin_right, y, f"Kgs: {units}")
            y -= 22
            c.line(margin_left, y, width - margin_right, y)
            y -= 25

            # --- Cabecera tabla ---
            c.setFont("Helvetica-Bold", 14)
            x_descr_left = margin_left
            x_qty = width - margin_right - 75
            x_code_right = width - margin_right

            c.drawString(x_descr_left, y, "Descripcion")
            c.drawRightString(x_qty, y, "Kg")
            c.drawRightString(x_code_right, y, "Codigo")
            y -= 16
            c.line(margin_left, y, width - margin_right, y)
            y -= 22

            # --- Filas tabla ---
            c.setFont("Helvetica", 14)
            table_row_height = 24

            for ing_id, ing_name, qty in ingredients:
                identifier = next(
                    (midf for mid, mname, midf, price in database.get_materials() if mid == ing_id),
                    ""
                )
                c.drawString(x_descr_left, y, ing_name)
                c.drawRightString(x_qty, y, f"{qty:.3f}")
                c.drawRightString(x_code_right, y, str(identifier))
                y -= table_row_height

                if y < 60:
                    c.showPage()
                    y = height - 50

            c.showPage()

        # ============================
        # CASO 2: KIT
        # ============================
        else:
            for comp_id, comp_name, comp_qty in ingredients:
                y = height - 50

                # --- Cabecera ---
                c.setFont("Helvetica-Bold", 21)
                c.drawString(margin_left, y, f"Orden de fabricación: {order_id}")
                y -= 28

                c.setFont("Helvetica", 13)
                c.drawString(margin_left, y, f"Cliente: {client_name or '-'}")
                c.drawRightString(width - margin_right, y, f"Fecha: {ts_fmt}")
                y -= 18

                c.drawString(margin_left, y, f"Proforma: {proforma_number or '-'}")
                y -= 30

                # --- Producto (componente del KIT) ---
                c.setFont("Helvetica-Bold", 15)
                c.line(margin_left, y, width - margin_right, y)
                y -= 22
                c.drawString(margin_left, y, f"{comp_name}")
                c.drawRightString(width - margin_right, y, f"Kgs: {comp_qty:.3f}")
                y -= 22
                c.line(margin_left, y, width - margin_right, y)
                y -= 25

                # --- Cabecera tabla ---
                c.setFont("Helvetica-Bold", 14)
                x_descr_left = margin_left
                x_qty = width - margin_right - 75
                x_code_right = width - margin_right

                c.drawString(x_descr_left, y, "Descripcion")
                c.drawRightString(x_qty, y, "Kg")
                c.drawRightString(x_code_right, y, "Codigo")
                y -= 16
                c.line(margin_left, y, width - margin_right, y)
                y -= 22

                # --- Fórmula REAL del componente ---
                component_formula = database.get_formulas(comp_id)
                c.setFont("Helvetica", 14)
                table_row_height = 24

                for ing_id, ing_name, qty, _ in component_formula:
                    total_qty = qty * comp_qty
                    identifier = next(
                        (midf for mid, mname, midf, price in database.get_materials() if mid == ing_id),
                        ""
                    )
                    c.drawString(x_descr_left, y, ing_name)
                    c.drawRightString(x_qty, y, f"{total_qty:.3f}")
                    c.drawRightString(x_code_right, y, str(identifier))

                    y -= table_row_height

                    if y < 60:
                        c.showPage()
                        y = height - 50

                c.showPage()

    c.save()
    os.startfile(pdf_path, "open")


def format_date(ts):
    """Return ts as DD-MM-YYYY"""
    if not ts:
        return ""
    candidates = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    for fmt in candidates:
        try:
            dt = datetime.strptime(ts, fmt)
            return dt.strftime("%d-%m-%Y")
        except Exception:
            pass
    return str(ts)
