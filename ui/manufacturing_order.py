import tkinter as tk
from tkinter import ttk, messagebox
import database
from datetime import datetime
from ui.print_order import print_orders  # note the plural

class ManufacturingOrderFrame(tk.Toplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.title("Crear Hoja de Fabricación")
        
        # Make fullscreen / maximized
        self.state('zoomed')  # maximized on Windows

        # --- State ---
        self.selected_product_id = None
        self.selected_product_name = None
        self.formula_table = []  # per-unit
        self.selected_order_id = None

        # --- Main layout ---
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # -----------------------------
        # LEFT SIDE: Product + Formula
        # -----------------------------
        tk.Label(left_frame, text="Buscar producto (formula):").pack(anchor="w")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(left_frame, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X)
        self.search_entry.bind("<KeyRelease>", self.on_search)

        self.product_listbox = tk.Listbox(left_frame, height=8)
        self.product_listbox.pack(fill=tk.BOTH, expand=False)
        self.product_listbox.bind("<<ListboxSelect>>", self.on_product_select)

        tk.Label(left_frame, text="Formula del producto seleccionado:").pack(anchor="w", pady=4)
        columns = ("ingredient", "quantity")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=12)
        self.tree.heading("ingredient", text="Componente")
        self.tree.heading("quantity", text="Cantidad")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Order info label (shows next order id + product name)
        self.order_info_var = tk.StringVar(value="Ningun producto seleccionado")
        tk.Label(left_frame, textvariable=self.order_info_var, font=("Arial", 10, "bold")).pack(anchor="w", pady=2)

        # Invoice number
        inv_frame = tk.Frame(left_frame)
        inv_frame.pack(fill=tk.X, pady=4)
        tk.Label(inv_frame, text="Numero de proforma:").pack(side=tk.LEFT)
        self.invoice_entry = tk.Entry(inv_frame, width=15)
        self.invoice_entry.pack(side=tk.LEFT, padx=6)

        # Customer name
        cust_frame = tk.Frame(left_frame)
        cust_frame.pack(fill=tk.X, pady=4)
        tk.Label(cust_frame, text="Cliente:").pack(side=tk.LEFT)
        self.customer_entry = tk.Entry(cust_frame, width=25)
        self.customer_entry.pack(side=tk.LEFT, padx=6)

        # Units input
        units_frame = tk.Frame(left_frame)
        units_frame.pack(fill=tk.X, pady=4)
        tk.Label(units_frame, text="Kgs a fabricar:").pack(side=tk.LEFT)
        self.units_entry = tk.Entry(units_frame, width=10)
        self.units_entry.pack(side=tk.LEFT, padx=6)
        self.units_entry.insert(0, "1")
        self.units_entry.bind("<KeyRelease>", lambda e: self.update_tree())

        # Save button
        tk.Button(left_frame, text="Guardar orden de fabricación", command=self.save_order).pack(pady=6)

        # -----------------------------
        # RIGHT SIDE: Past Orders + Print Controls
        # -----------------------------

        top_right_frame = tk.Frame(right_frame)
        top_right_frame.pack(fill=tk.X, pady=4)

        tk.Label(top_right_frame, text="Desde:").pack(side=tk.LEFT)
        self.from_id_entry = tk.Entry(top_right_frame, width=6)
        self.from_id_entry.pack(side=tk.LEFT, padx=2)

        tk.Label(top_right_frame, text="Hasta:").pack(side=tk.LEFT)
        self.to_id_entry = tk.Entry(top_right_frame, width=6)
        self.to_id_entry.pack(side=tk.LEFT, padx=2)

        tk.Button(top_right_frame, text="Imprimir", command=self.print_orders_range).pack(pady=4)

        # --- NEW: Search bar for orders ---
        search_order_frame = tk.Frame(right_frame)
        search_order_frame.pack(fill=tk.X, pady=4)
        tk.Label(search_order_frame, text="Buscar:").pack(side=tk.LEFT)
        self.order_search_var = tk.StringVar()
        self.order_search_entry = tk.Entry(search_order_frame, textvariable=self.order_search_var)
        self.order_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.order_search_entry.bind("<KeyRelease>", self.on_order_search)

        tk.Label(right_frame, text="Ordenes de fabricación:").pack(anchor="w")
        columns = ("id", "product", "units", "customer", "invoice", "date")
        self.orders_tree = ttk.Treeview(
            right_frame, columns=columns, show="headings", height=25
        )
        self.orders_tree.heading("id", text="ID")
        self.orders_tree.heading("product", text="Producto")
        self.orders_tree.heading("units", text="Kgs")
        self.orders_tree.heading("customer", text="Cliente")
        self.orders_tree.heading("invoice", text="Proforma")
        self.orders_tree.heading("date", text="Fecha")

        # Ajustar tamaños de columnas (puedes tunearlos)
        self.orders_tree.column("id", width=30, anchor="center")
        self.orders_tree.column("product", width=310, anchor="w")
        self.orders_tree.column("units", width=40, anchor="center")
        self.orders_tree.column("customer", width=100, anchor="w")
        self.orders_tree.column("invoice", width=50, anchor="center")
        self.orders_tree.column("date", width=70, anchor="center")

        self.orders_tree.pack(fill=tk.BOTH, expand=True)
        self.orders_tree.bind("<<TreeviewSelect>>", self.on_order_select)

        # -----------------------------
        # Initial data
        # -----------------------------
        self.refresh_products()
        self.refresh_orders()

    # -----------------------------
    # Product search / list
    # -----------------------------
    def refresh_products(self):
        filter_text = self.search_var.get().lower() if self.search_var.get() else ""
        self.product_listbox.delete(0, tk.END)

        # Only products that have a formula
        conn, cursor = database.connect()
        cursor.execute("""
            SELECT DISTINCT m.id, m.name, m.identifier, m.price
            FROM Materials m
            JOIN Formulas f ON m.id = f.product_id
            ORDER BY m.name
        """)
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            mid, mname, identifier, price = row
            if filter_text in mname.lower():
                self.product_listbox.insert(tk.END, f"{mid} - {mname}")


    def on_search(self, event=None):
        self.refresh_products()

    def on_product_select(self, event=None):
        sel = self.product_listbox.curselection()
        if not sel:
            return
        selection = self.product_listbox.get(sel[0])
        product_id, product_name = selection.split(" - ", 1)

        self.selected_product_id = int(product_id)
        self.selected_product_name = product_name

        # Load per-unit formula
        formula = database.get_formulas(self.selected_product_id)
        self.formula_table = [{"id": ing_id, "name": name, "qty": qty} for ing_id, name, qty, _ in formula]

        # Show order info (next ID + product)
        next_id = database.get_next_order_id()
        self.order_info_var.set(f"Next Order #{next_id} for {product_name}")

        self.update_tree()

    # -----------------------------
    # Orders
    # -----------------------------
    def refresh_orders(self):
        orders = database.get_orders()
        self.populate_orders_listbox(orders)


    def on_order_search(self, event=None):
        """Filter orders by invoice number or client name"""
        query = self.order_search_var.get().strip()
        if query:
            orders = database.search_orders(query)
        else:
            orders = database.get_orders()
        self.populate_orders_listbox(orders)

    def populate_orders_listbox(self, orders):
        # Ahora trabajamos con self.orders_tree
        for row in self.orders_tree.get_children():
            self.orders_tree.delete(row)

        for oid, pname, units, ts, customer_name, invoice_number in orders:
            ts_fmt = self._format_date_for_display(ts)
            self.orders_tree.insert(
                "", "end",
                iid=str(oid),
                values=(oid, pname, f"{units:.2f}", customer_name or "-", invoice_number or "-", ts_fmt)
            )


    def on_order_select(self, event=None):
        sel = self.orders_tree.selection()
        if not sel:
            return
        self.selected_order_id = int(sel[0])

        pid, units, ingredients, *_ = database.get_order_details(self.selected_order_id)
        if not pid:
            return

        self.selected_product_id = pid
        self.selected_product_name = database.get_material_by_id(pid)["name"]
        self.units_entry.delete(0, tk.END)
        self.units_entry.insert(0, str(units))

        # Convert back to per-unit
        self.formula_table = [{"id": i[0], "name": i[1], "qty": i[2] / units} for i in ingredients]

        self.order_info_var.set(f"Order #{self.selected_order_id}")
        self.update_tree()


    # -----------------------------
    # Update tree
    # -----------------------------
    def update_tree(self):
        try:
            units = float(self.units_entry.get())
        except ValueError:
            units = 0
        for item in self.tree.get_children():
            self.tree.delete(item)
        for entry in self.formula_table:
            value = round(entry["qty"] * units, 3)        # redondear a 3 decimales
            self.tree.insert("", "end", values=(entry["name"], f"{value:.3f}"))

    # -----------------------------
    # Save order
    # -----------------------------
    def save_order(self):
        if not self.selected_product_id:
            messagebox.showerror("Error", "Select a product first")
            return

        try:
            units = float(self.units_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid number of units")
            return

        invoice = self.invoice_entry.get().strip()
        customer = self.customer_entry.get().strip()
        order_id = database.create_order(
            self.selected_product_id,
            units,
            proforma_number=invoice,
            client_name=customer
        )
        messagebox.showinfo("Success", f"Order {order_id} saved for {self.selected_product_name}")

        # Refresh orders & keep window on top
        self.refresh_orders()
        self.lift()
        self.focus_force()

        # Update next order label
        next_id = database.get_next_order_id()
        if self.selected_product_name:
            self.order_info_var.set(f"Next Order #{next_id} for {self.selected_product_name}")
        else:
            self.order_info_var.set(f"Next Order #{next_id}")

    # -----------------------------
    # Print multiple orders
    # -----------------------------
    def print_orders_range(self):
        from_text = self.from_id_entry.get().strip()
        to_text = self.to_id_entry.get().strip()

        if from_text and to_text:
            try:
                from_id = int(from_text)
                to_id = int(to_text)
                if from_id > to_id:
                    messagebox.showerror("Error", "'From ID' cannot be greater than 'To ID'")
                    return
                order_ids = list(range(from_id, to_id + 1))
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers for From and To")
                return
        elif from_text:
            try:
                order_ids = [int(from_text)]
            except ValueError:
                messagebox.showerror("Error", "Enter a valid numeric ID")
                return
        elif to_text:
            try:
                order_ids = [int(to_text)]
            except ValueError:
                messagebox.showerror("Error", "Enter a valid numeric ID")
                return
        else:  # Both empty
            if self.selected_order_id:
                order_ids = [self.selected_order_id]
            else:
                orders = database.get_orders()
                if not orders:
                    messagebox.showinfo("Info", "No orders available")
                    return
                last_order_id = orders[0][0]  # assuming descending by date
                order_ids = [last_order_id]

        from ui.print_order import print_orders
        print_orders(order_ids)


    # -----------------------------
    # Date formatting helper
    # -----------------------------

    def _format_date_for_display(self, ts):
        """Return ts as DD-MM-YYYY if possible, otherwise sensible fallback."""
        if not ts:
            return ""
        # Try common formats (with and without microseconds, with 'T', etc.)
        candidates = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in candidates:
            try:
                dt = datetime.strptime(ts, fmt)
                return dt.strftime("%d-%m-%Y")
            except Exception:
                pass
        # Try fromisoformat as a last attempt (handles some variants)
        try:
            dt = datetime.fromisoformat(ts)
            return dt.date().strftime("%d-%m-%Y")
        except Exception:
            pass
        # Fallback: return just the date part if there is a space
        if isinstance(ts, str) and " " in ts:
            return ts.split(" ")[0].replace("-", "/")  # still make it readable
        return str(ts)
