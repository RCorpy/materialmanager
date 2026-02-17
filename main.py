from ui.app import run_app
from sync import sync_on_startup

if __name__ == "__main__":
    try:
        print(sync_on_startup())
    except Exception as e:
        print("Error en la sincronización inicial",e)

    run_app()
