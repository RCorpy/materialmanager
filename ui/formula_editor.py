import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


class FormulaEditorFrame(tk.LabelFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, text="Formula", padx=8, pady=8)
        self.controller = controller

        # Title
        self.title_var = tk.StringVar()
        self.title_var.set("Formula (Sin selección)")
        ttk.Label(self, textvariable=self.title_var, font=("Arial", 12, "bold")).pack(pady=5)

        # Treeview
        columns = ("ingredient", "quantity", "cost")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        self.tree.heading("ingredient", text="Ingrediente")
        self.tree.heading("quantity", text="Cantidad")
        self.tree.heading("cost", text="Precio (€)")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)

        # Buttons row
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Eliminar Ingrediente seleccionado", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Editar Cantidad", command=self.edit_quantity).pack(side=tk.LEFT, padx=5)

        # Total quantity label
        self.total_var = tk.StringVar()
        self.total_var.set("Cantidad total: 0.0")
        ttk.Label(self, textvariable=self.total_var, font=("Arial", 10, "bold")).pack(pady=5)

        controller.register("formula_editor", self)

    def set_product_name(self, name):
        if name:
            self.title_var.set(f"Fórmula para: {name}")
        else:
            self.title_var.set("Formula (Sin selección)")

    def update_display(self):
        # Clear old rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Insert updated rows
        total_qty = 0
        total_cost = 0
        for entry in self.controller.formula_table:
            iid = str(entry["id"])
            price = entry.get("price", 0.0)
            cost = entry["qty"] * price
            qty = round(entry["qty"], 3)
            cost = round(entry["qty"] * price, 2)

            self.tree.insert("", "end", iid=iid,
                            values=(entry["name"], f"{qty:.3f}", f"€{cost:.2f}"))
            total_qty += qty

            total_cost += cost

        # Update labels
        self.total_var.set(f"Cantidad total: {total_qty:.3f} | Precio total: €{total_cost:.2f}")


    def remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        ids = [int(iid) for iid in sel]
        self.controller.formula_table = [e for e in self.controller.formula_table if e["id"] not in ids]
        self.update_display()

    def edit_quantity(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Selecciona un ingrediente para editar")
            return
        iid = int(sel[0])
        entry = next((e for e in self.controller.formula_table if e["id"] == iid), None)
        if not entry:
            return
        answer = simpledialog.askstring("Editar cantidad", f"Introduce la nueva cantidad para '{entry['name']}'", initialvalue=str(entry["qty"]))
        if answer is None:
            return
        try:
            entry["qty"] = float(answer)
            self.update_display()
        except ValueError:
            messagebox.showerror("Error", "Introduce un número válido")
