import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import database

database.create_tables()  # ensure DB & tables exist

# ---------- helper state ----------
formula_table = []  # list of dicts: {id, name, qty}

# ---------- root ----------
root = tk.Tk()
root.title("Material Manager")
root.geometry("900x700")

# ---------- frames ----------
top_frame = tk.Frame(root, padx=10, pady=10)
top_frame.pack(fill=tk.X)
mid_frame = tk.Frame(root, padx=10, pady=10)
mid_frame.pack(fill=tk.BOTH, expand=True)
bottom_frame = tk.Frame(root, padx=10, pady=10)
bottom_frame.pack(fill=tk.X)

# ---------- Add Material (top) ----------
tk.Label(top_frame, text="Add Material", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
tk.Label(top_frame, text="Name:").grid(row=1, column=0, sticky="e")
name_entry = tk.Entry(top_frame, width=40)
name_entry.grid(row=1, column=1, sticky="w")

tk.Label(top_frame, text="Description:").grid(row=2, column=0, sticky="e")
desc_entry = tk.Entry(top_frame, width=40)
desc_entry.grid(row=2, column=1, sticky="w")

def add_material_ui():
    name = name_entry.get().strip()
    desc = desc_entry.get().strip()
    if not name:
        messagebox.showerror("Error", "Name is required")
        return
    ok = database.add_material(name, desc)
    if ok:
        messagebox.showinfo("Success", f"Material '{name}' added")
        name_entry.delete(0, tk.END)
        desc_entry.delete(0, tk.END)
        refresh_lists()
    else:
        messagebox.showerror("Error", f"Material '{name}' already exists")

tk.Button(top_frame, text="Add Material", command=add_material_ui).grid(row=1, column=2, rowspan=2, padx=10)

# ---------- Product selection (left side of mid_frame) ----------
prod_frame = tk.LabelFrame(mid_frame, text="Product (select to load/edit its formula)", padx=8, pady=8)
prod_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

tk.Label(prod_frame, text="Search product:").pack(anchor="w")
product_search_var = tk.StringVar()
product_search_entry = tk.Entry(prod_frame, textvariable=product_search_var)
product_search_entry.pack(fill=tk.X)
product_listbox = tk.Listbox(prod_frame, width=40, height=12)
product_scroll = tk.Scrollbar(prod_frame, command=product_listbox.yview)
product_listbox.config(yscrollcommand=product_scroll.set)
product_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
product_scroll.pack(side=tk.LEFT, fill=tk.Y)

def refresh_products(filter_text=""):
    product_listbox.delete(0, tk.END)
    for mid, mname in database.get_materials():
        if filter_text.lower() in mname.lower():
            product_listbox.insert(tk.END, f"{mid} - {mname}")

def on_product_search(event):
    refresh_products(product_search_var.get())

product_search_entry.bind("<KeyRelease>", on_product_search)

def load_existing_formula(event):
    try:
        sel = product_listbox.curselection()
        if not sel:
            return
        selection = product_listbox.get(sel[0])
        product_id = int(selection.split(" - ", 1)[0])
        # fetch formula entries from DB (ingredient_id, name, qty)
        rows = database.get_formulas(product_id)
        global formula_table
        formula_table = [{"id": r[0], "name": r[1], "qty": r[2]} for r in rows]
        update_formula_display()
    except Exception as e:
        print("load_existing_formula error:", e)

product_listbox.bind("<<ListboxSelect>>", load_existing_formula)

# ---------- Ingredient selection (middle of mid_frame) ----------
ing_frame = tk.LabelFrame(mid_frame, text="Ingredients (search + select)", padx=8, pady=8)
ing_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)

tk.Label(ing_frame, text="Search ingredient:").pack(anchor="w")
ingredient_search_var = tk.StringVar()
ingredient_search_entry = tk.Entry(ing_frame, textvariable=ingredient_search_var)
ingredient_search_entry.pack(fill=tk.X)
ingredient_listbox = tk.Listbox(ing_frame, width=40, height=12)
ingredient_scroll = tk.Scrollbar(ing_frame, command=ingredient_listbox.yview)
ingredient_listbox.config(yscrollcommand=ingredient_scroll.set)
ingredient_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
ingredient_scroll.pack(side=tk.LEFT, fill=tk.Y)

def refresh_ingredients(filter_text=""):
    ingredient_listbox.delete(0, tk.END)
    for mid, mname in database.get_materials():
        if filter_text.lower() in mname.lower():
            ingredient_listbox.insert(tk.END, f"{mid} - {mname}")

def on_ingredient_search(event):
    refresh_ingredients(ingredient_search_var.get())

ingredient_search_entry.bind("<KeyRelease>", on_ingredient_search)

# quantity entry and add button (below ingredient list)
qty_frame = tk.Frame(ing_frame)
qty_frame.pack(fill=tk.X, pady=6)
tk.Label(qty_frame, text="Quantity:").pack(side=tk.LEFT)
qty_entry = tk.Entry(qty_frame, width=12)
qty_entry.pack(side=tk.LEFT, padx=6)
qty_entry.insert(0, "0.0")

def add_ingredient_to_formula():
    try:
        sel = ingredient_listbox.curselection()
        if not sel:
            messagebox.showerror("Error", "Select an ingredient first")
            return
        selection = ingredient_listbox.get(sel[0])
        ing_id, ing_name = selection.split(" - ", 1)
        ing_id = int(ing_id)
        qty_str = qty_entry.get().strip()
        qty = float(qty_str)
        # replace if exists
        for entry in formula_table:
            if entry["id"] == ing_id:
                entry["qty"] = qty
                update_formula_display()
                return
        formula_table.append({"id": ing_id, "name": ing_name, "qty": qty})
        update_formula_display()
    except ValueError:
        messagebox.showerror("Error", "Enter a valid numeric quantity")
    except Exception as e:
        messagebox.showerror("Error", f"Add ingredient error: {e}")

tk.Button(ing_frame, text="Add / Update Ingredient", command=add_ingredient_to_formula).pack(pady=4)

# ---------- Formula display (right side of mid_frame) ----------
formula_frame = tk.LabelFrame(mid_frame, text="Current Formula (for selected product)", padx=8, pady=8)
formula_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

columns = ("ingredient", "quantity")
formula_tree = ttk.Treeview(formula_frame, columns=columns, show="headings", height=15)
formula_tree.heading("ingredient", text="Ingredient")
formula_tree.heading("quantity", text="Quantity")
formula_tree.column("ingredient", width=220)
formula_tree.column("quantity", width=80, anchor="center")
formula_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
formula_scroll = tk.Scrollbar(formula_frame, command=formula_tree.yview)
formula_tree.config(yscrollcommand=formula_scroll.set)
formula_scroll.pack(side=tk.LEFT, fill=tk.Y)

def update_formula_display():
    # clear tree
    for item in formula_tree.get_children():
        formula_tree.delete(item)
    # insert rows, use ingredient id as iid so editing/removing is easy
    for entry in formula_table:
        iid = str(entry["id"])
        # if iid already in tree, delete before re-inserting (keeps IID unique)
        if iid in formula_tree.get_children():
            try:
                formula_tree.delete(iid)
            except Exception:
                pass
        formula_tree.insert("", "end", iid=iid, values=(entry["name"], entry["qty"]))

def remove_selected_ingredient():
    sel = formula_tree.selection()
    if not sel:
        return
    for iid in sel:
        iid_int = int(iid)
        # remove from formula_table
        global formula_table
        formula_table = [e for e in formula_table if e["id"] != iid_int]
    update_formula_display()

def edit_selected_quantity():
    sel = formula_tree.selection()
    if not sel:
        messagebox.showerror("Error", "Select an ingredient row to edit")
        return
    iid = sel[0]
    current_qty = None
    for e in formula_table:
        if e["id"] == int(iid):
            current_qty = e["qty"]
            break
    answer = simpledialog.askstring("Edit quantity", f"Enter new quantity for '{e['name']}'", initialvalue=str(current_qty))
    if answer is None:
        return
    try:
        new_qty = float(answer)
        for e in formula_table:
            if e["id"] == int(iid):
                e["qty"] = new_qty
                break
        update_formula_display()
    except ValueError:
        messagebox.showerror("Error", "Enter a valid number")

tk.Button(formula_frame, text="Edit Quantity", command=edit_selected_quantity).pack(pady=4, anchor="w")
tk.Button(formula_frame, text="Remove Selected", command=remove_selected_ingredient).pack(pady=4, anchor="w")

# ---------- Save formula (bottom) ----------
def save_formula():
    try:
        sel = product_listbox.curselection()
        if not sel:
            messagebox.showerror("Error", "Select a product to save its formula")
            return
        selection = product_listbox.get(sel[0])
        product_id = int(selection.split(" - ", 1)[0])
        # build list of tuples (ingredient_id, qty)
        ingredients = [(e["id"], e["qty"]) for e in formula_table]
        database.update_formula(product_id, ingredients)
        messagebox.showinfo("Success", "Formula saved successfully")
        # reload from DB to ensure consistency
        load_existing_formula(None)
    except Exception as e:
        messagebox.showerror("Error", f"Save formula error: {e}")

tk.Button(bottom_frame, text="Save Formula (overwrite existing)", command=save_formula, width=30).pack(pady=8)

# ---------- refresh helper ----------
def refresh_lists():
    pfilter = product_search_var.get() if product_search_var.get() else ""
    if pfilter is None: pfilter = ""
    refresh_products(pfilter)
    if ingredient_search_var.get():
        refresh_ingredients(ingredient_search_var.get())
    else:
        refresh_ingredients("")

# initial population
refresh_lists()

# start UI
root.mainloop()
