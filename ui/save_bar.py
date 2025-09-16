import tkinter as tk
from tkinter import messagebox
import database


class SaveBar(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Button(
            self,
            text="Save Formula (overwrite existing)",
            command=self.save_formula,
            width=30
        ).pack(pady=8)

    def save_formula(self):
        product_id = self.controller.selected_product_id
        if not product_id:
            messagebox.showerror("Error", "Select a product to save its formula")
            return
        ingredients = [(e["id"], e["qty"]) for e in self.controller.formula_table]
        database.update_formula(product_id, ingredients)
        messagebox.showinfo("Success", "Formula saved successfully")
        # Reload to be safe
        rows = database.get_formulas(product_id)
        self.controller.formula_table = [{"id": r[0], "name": r[1], "qty": r[2], "price": r[3]} for r in rows]
        self.controller.frames["formula_editor"].update_display()
