import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


class FormulaEditorFrame(tk.LabelFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, text="Formula editor", padx=8, pady=8)
        self.controller = controller

        # Title
        self.title_var = tk.StringVar()
        self.title_var.set("Current formula (no product selected)")
        ttk.Label(self, textvariable=self.title_var, font=("Arial", 12, "bold")).pack(pady=5)

        # Treeview
        columns = ("ingredient", "quantity")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        self.tree.heading("ingredient", text="Ingredient")
        self.tree.heading("quantity", text="Quantity")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)

        # Buttons row
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Remove Selected Ingredient", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Edit Quantity", command=self.edit_quantity).pack(side=tk.LEFT, padx=5)

        # Total quantity label
        self.total_var = tk.StringVar()
        self.total_var.set("Total quantity: 0.0")
        ttk.Label(self, textvariable=self.total_var, font=("Arial", 10, "bold")).pack(pady=5)

        controller.register("formula_editor", self)

    def set_product_name(self, name):
        if name:
            self.title_var.set(f"Current formula for: {name}")
        else:
            self.title_var.set("Current formula (no product selected)")

    def update_display(self):
        # Clear old rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Insert updated rows
        total_qty = 0
        for entry in self.controller.formula_table:
            iid = str(entry["id"])
            self.tree.insert("", "end", iid=iid, values=(entry["name"], entry["qty"]))
            total_qty += entry["qty"]

        # Update total
        self.total_var.set(f"Total quantity: {total_qty}")

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
            messagebox.showerror("Error", "Select an ingredient row to edit")
            return
        iid = int(sel[0])
        entry = next((e for e in self.controller.formula_table if e["id"] == iid), None)
        if not entry:
            return
        answer = simpledialog.askstring("Edit quantity", f"Enter new quantity for '{entry['name']}'", initialvalue=str(entry["qty"]))
        if answer is None:
            return
        try:
            entry["qty"] = float(answer)
            self.update_display()
        except ValueError:
            messagebox.showerror("Error", "Enter a valid number")
