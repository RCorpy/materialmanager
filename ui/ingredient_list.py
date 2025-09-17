import tkinter as tk
from tkinter import messagebox
import database


class IngredientListFrame(tk.LabelFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, text="Ingredientes (buscar + seleccionar)", padx=8, pady=8)
        self.controller = controller
        self.selected_ingredient_id = None
        self.selected_ingredient_name = None

        tk.Label(self, text="Buscar Ingrediente:").pack(anchor="w")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X)
        self.search_entry.bind("<KeyRelease>", self.on_search)

        self.listbox = tk.Listbox(self, width=40, height=12)
        scroll = tk.Scrollbar(self, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scroll.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.LEFT, fill=tk.Y)

        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        qty_frame = tk.Frame(self)
        qty_frame.pack(fill=tk.X, pady=6)
        tk.Label(qty_frame, text="Cantidad:").pack(side=tk.LEFT)
        self.qty_entry = tk.Entry(qty_frame, width=12)
        self.qty_entry.pack(side=tk.LEFT, padx=6)
        self.qty_entry.insert(0, "0.0")

        tk.Button(self, text="Añadir / Modificar Ingrediente", command=self.add_ingredient).pack(pady=4)

    def refresh(self):
        filter_text = self.search_var.get() or ""
        self.listbox.delete(0, tk.END)
        for mid, mname, identifier, price in database.get_materials():
            # Show only ingredients that match search text
            if filter_text.lower() in mname.lower():
                display_text = f"{mid} - {mname}"
                self.listbox.insert(tk.END, display_text)


    def on_search(self, event=None):
        self.refresh()

    def on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        selection = self.listbox.get(sel[0])
        ing_id, ing_name = selection.split(" - ", 1)
        self.selected_ingredient_id = int(ing_id)
        self.selected_ingredient_name = ing_name

        # NEW: load this ingredient into the add_material frame
        add_mat_frame = self.controller.frames.get("add_material")
        if add_mat_frame:
            add_mat_frame.load_material(self.selected_ingredient_id)


    def add_ingredient(self):
        if not self.controller.selected_product_id:
            messagebox.showerror("Error", "Selecciona un producto primero")
            return
        if not self.selected_ingredient_id:
            messagebox.showerror("Error", "Selecciona un ingrediente primero")
            return
        try:
            qty = float(self.qty_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Introduce un número valido para la cantidad.")
            return

        # Update if ingredient already exists in formula
        for entry in self.controller.formula_table:
            if entry["id"] == self.selected_ingredient_id:
                entry["qty"] = qty
                self.controller.frames["formula_editor"].update_display()
                return

        # Add new ingredient to formula
        self.controller.formula_table.append({
            "id": self.selected_ingredient_id,
            "name": self.selected_ingredient_name,
            "qty": qty
        })
        self.controller.frames["formula_editor"].update_display()
