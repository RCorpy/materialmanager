import tkinter as tk
import database
from .add_material import AddMaterialFrame
from .product_list import ProductListFrame
from .ingredient_list import IngredientListFrame
from .formula_editor import FormulaEditorFrame
from .save_bar import SaveBar


class Controller:
    def __init__(self, root):
        self.root = root
        self.formula_table = []  # list of dicts {id, name, qty}
        self.selected_product_id = None
        self.frames = {}

    def register(self, name, frame):
        self.frames[name] = frame

    def refresh_all_lists(self):
        self.frames["products"].refresh()
        self.frames["ingredients"].refresh()


def run_app():
    database.create_tables()
    root = tk.Tk()
    root.title("Material Manager")
    root.geometry("900x700")

    controller = Controller(root)

    # Top frame (Add material)
    add_material = AddMaterialFrame(root, controller)
    add_material.pack(fill=tk.X, padx=10, pady=5)
    controller.register("add_material", add_material)

    # Middle section
    mid = tk.Frame(root)
    mid.pack(fill=tk.BOTH, expand=True)

    product_list = ProductListFrame(mid, controller)
    product_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    controller.register("products", product_list)

    ingredient_list = IngredientListFrame(mid, controller)
    ingredient_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    controller.register("ingredients", ingredient_list)

    formula_editor = FormulaEditorFrame(mid, controller)
    formula_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
    controller.register("formula_editor", formula_editor)


    # Bottom bar
    save_bar = SaveBar(root, controller)
    save_bar.pack(fill=tk.X, padx=10, pady=5)
    controller.register("save_bar", save_bar)

    # Initial refresh
    controller.refresh_all_lists()

    root.mainloop()
