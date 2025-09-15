import tkinter as tk
from tkinter import ttk, messagebox
import database
from datetime import datetime


class ManufacturingOrderFrame(tk.Toplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.title("Create Manufacturing Order")
        self.geometry("1100x600")

        # --- State ---
        self.selected_product_id = None
        self.selected_product_name = None
        self.formula_table = []  # list of dicts {id, name, qty} (always per-unit)
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
        tk.Label(left_frame, text="Search product (formula):").pack(anchor="w")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(left_frame, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X)
        self.search_entry.bind("<KeyRelease>", self.on_search)

        self.product_listbox = tk.Listbox(left_frame, height=8)
        self.product_listbox.pack(fill=tk.BOTH, expand=False)
        self.product_listbox.bind("<<ListboxSelect>>", self.on_product_select)

        tk.Label(left_frame, text="Formula for selected product:").pack(anchor="w", pady=4)
        columns = ("ingredient", "quantity")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=12)
        self.tree.heading("ingredient", text="Ingredient")
        self.tree.heading("quantity", text="Quantity (full)")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Order info label (shows next order id + product name)
        self.order_info_var = tk.StringVar(value="No product selected")
        tk.Label(left_frame, textvariable=self.order_info_var, font=("Arial", 10, "bold")).pack(anchor="w", pady=2)

        # Units input
        units_frame = tk.Frame(left_frame)
        units_frame.pack(fill=tk.X, pady=4)
        tk.Label(units_frame, text="Units to manufacture:").pack(side=tk.LEFT)
        self.units_entry = tk.Entry(units_frame, width=10)
        self.units_entry.pack(side=tk.LEFT, padx=6)
        self.units_entry.insert(0, "1")
        self.units_entry.bind("<KeyRelease>", lambda e: self.update_tree())

        # Save button
        tk.Button(left_frame, text="Save Manufacturing Order", command=self.save_order).pack(pady=6)

        # -----------------------------
        # RIGHT SIDE: Past Orders
        # -----------------------------
        top_right_frame = tk.Frame(right_frame)
        top_right_frame.pack(fill=tk.X, pady=4)

        tk.Label(top_right_frame, text="From ID:").pack(side=tk.LEFT)
        self.from_id_entry = tk.Entry(top_right_frame, width=6)
        self.from_id_entry.pack(side=tk.LEFT, padx=2)

        tk.Label(top_right_frame, text="To ID:").pack(side=tk.LEFT)
        self.to_id_entry = tk.Entry(top_right_frame, width=6)
        self.to_id_entry.pack(side=tk.LEFT, padx=2)

        tk.Button(top_right_frame, text="Print Orders", command=self.print_orders).pack(side=tk.LEFT, padx=6)

        tk.Label(right_frame, text="Past Manufacturing Orders:").pack(anchor="w")
        self.orders_listbox = tk.Listbox(right_frame, height=25)
        self.orders_listbox.pack(fill=tk.BOTH, expand=True)
        self.orders_listbox.bind("<<ListboxSelect>>", self.on_order_select)

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
        for mid, mname, _ in database.get_materials():
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
        self.formula_table = [{"id": ing_id, "name": name, "qty": qty} for ing_id, name, qty in formula]

        # Show order info (next ID + product)
        next_id = database.get_next_order_id()
        self.order_info_var.set(f"Next Order #{next_id} for {product_name}")

        self.update_tree()

    # -----------------------------
    # Orders
    # -----------------------------
    def refresh_orders(self):
        self.orders_listbox.delete(0, tk.END)
        for oid, pname, units, ts in database.get_orders():
            ts_fmt = self._format_date_for_display(ts)
            self.orders_listbox.insert(tk.END, f"{oid} - {pname} ({units} units) [{ts_fmt}]")


    def on_order_select(self, event=None):
        sel = self.orders_listbox.curselection()
        if not sel:
            return
        selection = self.orders_listbox.get(sel[0])
        order_id, _ = selection.split(" - ", 1)
        self.selected_order_id = int(order_id)

        pid, units, ingredients = database.get_order_details(self.selected_order_id)
        if not pid:
            return

        self.selected_product_id = pid
        self.selected_product_name = database.get_material_name(pid)
        self.units_entry.delete(0, tk.END)
        self.units_entry.insert(0, str(units))

        # Convert back to per-unit
        self.formula_table = [{"id": i[0], "name": i[1], "qty": i[2] / units} for i in ingredients]

        self.order_info_var.set(f"Order #{self.selected_order_id} for {self.selected_product_name}")
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
            self.tree.insert("", "end", values=(entry["name"], entry["qty"] * units))

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

        order_id = database.create_order(self.selected_product_id, units)
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
    # Print orders (future use)
    # -----------------------------
    def print_orders(self):
        from_id = self.from_id_entry.get().strip()
        to_id = self.to_id_entry.get().strip()

        if from_id and to_id:
            messagebox.showinfo("Print Orders", f"Printing orders from {from_id} to {to_id}")
        elif self.selected_order_id:
            messagebox.showinfo("Print Orders", f"Printing order #{self.selected_order_id}")
        else:
            messagebox.showerror("Error", "Select an order or enter a range")
        self.lift()

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
