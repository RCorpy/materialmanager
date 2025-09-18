import tkinter as tk
import database


class ProductListFrame(tk.LabelFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, text="Productos (selecciona para cargar/editar la formula)", padx=8, pady=8)
        self.controller = controller
        self.selected_product_id = None
        self.products = []  # [(id, name), ...]

        tk.Label(self, text="Buscar producto:").pack(anchor="w")
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

    def refresh(self):
        filter_text = self.search_var.get() or ""
        self.listbox.delete(0, tk.END)
        self.products = []

        for mid, mname, identifier, price in database.get_materials():
            if filter_text.lower() in mname.lower():
                self.listbox.insert(tk.END, mname)
                self.products.append((mid, mname))

    def on_search(self, event=None):
        self.refresh()

    def on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        index = sel[0]
        product_id, product_name = self.products[index]

        self.controller.selected_product_id = product_id

        # Load its formula from DB
        rows = database.get_formulas(product_id)
        self.controller.formula_table = [
            {"id": r[0], "name": r[1], "qty": r[2], "price": r[3]} for r in rows
        ]

        # Update formula editor display + title
        self.controller.frames["formula_editor"].update_display()
        self.controller.frames["formula_editor"].set_product_name(product_name)

        # Load this product into add_material frame if exists
        add_mat_frame = self.controller.frames.get("add_material")
        if add_mat_frame:
            add_mat_frame.load_material(product_id)
