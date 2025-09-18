import tkinter as tk
from tkinter import messagebox, filedialog
import database
import os
import shutil



class AddMaterialFrame(tk.LabelFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, text="Gestionar Materiales", padx=8, pady=8)
        self.controller = controller
        self.selected_material_id = None

        # --- Variables ---
        self.name_var = tk.StringVar()
        self.identifier_var = tk.StringVar()
        self.desc_var = tk.StringVar()
        self.price_var = tk.StringVar(value="0.00")

        # --- Name ---
        tk.Label(self, text="Nombre:").grid(row=0, column=0, sticky="e")
        self.name_entry = tk.Entry(self, width=30, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="w")

        # --- Identifier (optional) ---
        tk.Label(self, text="Identificador:").grid(row=1, column=0, sticky="e")
        self.id_entry = tk.Entry(self, width=30, textvariable=self.identifier_var)
        self.id_entry.grid(row=1, column=1, sticky="w")

        # --- Description ---
        tk.Label(self, text="Descripción:").grid(row=2, column=0, sticky="e")
        self.desc_entry = tk.Entry(self, width=30, textvariable=self.desc_var)
        self.desc_entry.grid(row=2, column=1, sticky="w")

        # --- Price ---
        tk.Label(self, text="Precio:").grid(row=3, column=0, sticky="e")
        self.price_entry = tk.Entry(self, width=12, textvariable=self.price_var)
        self.price_entry.grid(row=3, column=1, sticky="w")

        # --- Add/Update/Clone Buttons ---
        tk.Button(self, text="Añadir Material", command=self.add_material_only, width=15).grid(
            row=0, column=3, rowspan=2, padx=10, pady=2
        )
        tk.Button(self, text="Modificar", command=self.update_material_only, width=15).grid(
            row=2, column=3, rowspan=2, padx=10, pady=2
        )
        tk.Button(self, text="Clonar Material", command=self.clone_material, width=15).grid(
            row=4, column=3, rowspan=2, padx=10, pady=2
        )

        # --- Backup/Restore Buttons on far right ---
        tk.Button(self, text="Guardar BD", width=15, command=self.backup_database).grid(
            row=0, column=4, rowspan=1, padx=(50,10), pady=(5,2), sticky="n"
        )
        tk.Button(self, text="Recuperar BD", width=15, command=self.restore_database).grid(
            row=1, column=4, rowspan=1, padx=(50,10), pady=(2,5), sticky="n"
        )

        # Push right-most column to expand if window grows
        self.grid_columnconfigure(4, weight=1)






    def load_material(self, material_id):
        material = database.get_material_by_id(material_id)
        if not material:
            return
        self.selected_material_id = material_id
        self.name_var.set(material["name"])
        self.desc_var.set(material["description"] or "")
        self.identifier_var.set(material["identifier"] or "")
        price = material["price"] or 0.0
        self.price_var.set(f"{price:.2f}")

    def add_material_only(self):
        name = self.name_var.get().strip()
        desc = self.desc_var.get().strip()
        identifier = self.identifier_var.get().strip() or None
        try:
            price = float(self.price_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Precio debe ser un numero")
            return

        ok = database.add_material(name, description=desc, identifier=identifier, price=price)
        if not ok:
            messagebox.showerror("Error", "Nombre o identificador ya existe")
            return
        messagebox.showinfo("Added", f"Material '{name}' añadido correctamente")
        self.selected_material_id = None
        self.controller.refresh_all_lists()

    def update_material_only(self):
        if not self.selected_material_id:
            messagebox.showerror("Error", "Selecciona un material para modificar antes")
            return

        name = self.name_var.get().strip()
        desc = self.desc_var.get().strip()
        identifier = self.identifier_var.get().strip() or None
        try:
            price = float(self.price_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Precio debe ser un numero")
            return

        ok = database.update_material(
            self.selected_material_id,
            name=name,
            identifier=identifier,
            description=desc,
            price=price
        )
        if not ok:
            messagebox.showerror("Error", "Nombre o identificador ya existe")
            return
        messagebox.showinfo("Updated", f"Material '{name}' modificado correctamente")
        self.selected_material_id = None
        self.controller.refresh_all_lists()

    def backup_database(self):
        folder = tk.filedialog.askdirectory(title="Selecciona carpeta para guardar copia")
        if not folder:
            return
        try:
            backup_path = database.backup_database(destination_folder=folder)
            messagebox.showinfo("Success", f"Database backed up to:\n{backup_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to backup database:\n{str(e)}")

    def restore_database(self):
        backup_file = filedialog.askopenfilename(
            title="Selecciona base de datos para restaurar",
            filetypes=[("SQLite Database", "*.db")]
        )
        if not backup_file:
            return

        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"Esto reemplazara la base de datos actual con la copia de seguridad:\n{os.path.basename(backup_file)}\nContinuar?"
        )
        if not confirm:
            return

        try:
            shutil.copy2(backup_file, database.DB_NAME)
            messagebox.showinfo("Success", "Database restored successfully!")
            self.controller.refresh_all_lists()  # refresh UI if needed
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore database:\n{e}")


    def clone_material(self):
        if not self.selected_material_id:
            messagebox.showerror("Error", "Selecciona un material para clonar")
            return

        # Obtener material original
        material = database.get_material_by_id(self.selected_material_id)
        if not material:
            messagebox.showerror("Error", "No se encontró el material a clonar")
            return

        # Preparar datos del clon
        new_name = material["name"] + " - Copia"
        new_desc = material["description"] or ""
        new_price = material["price"] or 0.0

        # El identificador lo ponemos None para que no choque con el original
        ok = database.add_material(new_name, description=new_desc, identifier=None, price=new_price)
        if not ok:
            messagebox.showerror("Error", "No se pudo crear el material clonado (nombre o identificador duplicado)")
            return

        # Recuperar el id del material recién insertado
        conn, cursor = database.connect()
        cursor.execute("SELECT id FROM Materials WHERE name = ?", (new_name,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            messagebox.showerror("Error", "Error al recuperar el id del material clonado")
            return
        new_material_id = row[0]

        # Copiar también la fórmula asociada
        formulas = database.get_formulas(self.selected_material_id)
        if formulas:
            conn, cursor = database.connect()
            for row in formulas:
                ing_id = row[0]   # id del ingrediente
                qty = row[2]      # cantidad
                cursor.execute(
                    "INSERT INTO Formulas (product_id, ingredient_id, quantity) VALUES (?, ?, ?)",
                    (new_material_id, ing_id, qty)
                )
            conn.commit()
            conn.close()


        messagebox.showinfo("Clonado", f"Material '{new_name}' creado como copia de '{material['name']}'")
        self.controller.refresh_all_lists()
