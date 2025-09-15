import tkinter as tk
from tkinter import messagebox
import database


class AddMaterialFrame(tk.LabelFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, text="Add Material", padx=8, pady=8)
        self.controller = controller

        # Name
        tk.Label(self, text="Name:").grid(row=0, column=0, sticky="e")
        self.name_entry = tk.Entry(self, width=30)
        self.name_entry.grid(row=0, column=1, sticky="w")

        # Identifier (optional)
        tk.Label(self, text="Identifier:").grid(row=1, column=0, sticky="e")
        self.id_entry = tk.Entry(self, width=30)
        self.id_entry.grid(row=1, column=1, sticky="w")
        tk.Label(self, text="(optional, will default to ID)").grid(row=1, column=2, sticky="w")

        # Description
        tk.Label(self, text="Description:").grid(row=2, column=0, sticky="e")
        self.desc_entry = tk.Entry(self, width=30)
        self.desc_entry.grid(row=2, column=1, sticky="w")

        # Add button
        tk.Button(self, text="Add Material", command=self.add_material).grid(
            row=0, column=3, rowspan=3, padx=10
        )

    def add_material(self):
        name = self.name_entry.get().strip()
        identifier = self.id_entry.get().strip()
        desc = self.desc_entry.get().strip()

        if not name:
            messagebox.showerror("Error", "Name is required")
            return

        ok = database.add_material(name, description=desc, identifier=identifier or None)
        if ok:
            messagebox.showinfo("Success", f"Material '{name}' added")
            # Clear entries
            self.name_entry.delete(0, tk.END)
            self.id_entry.delete(0, tk.END)
            self.desc_entry.delete(0, tk.END)
            self.controller.refresh_all_lists()
        else:
            messagebox.showerror("Error", f"Material '{name}' already exists")
