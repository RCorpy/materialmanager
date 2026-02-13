# sync.py
import json
import paramiko
import database
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SERVER = os.getenv("SYNC_SERVER")
USER = os.getenv("SYNC_USER")
REMOTE_DB = os.getenv("SYNC_DB_PATH")

KEY_PATH = os.path.expanduser(r"~\.ssh\id_ed25519")

REMOTE_GET_LAST = "/home/myuser/sync_server/get_last_order_id.py"
REMOTE_INSERT = "/home/myuser/sync_server/insert_orders.py"

LOCAL_DB = "materials.db"  # Ajusta si tu ruta es distinta


def get_local_max_id():
    conn, cursor = database.connect()
    cursor.execute("SELECT MAX(order_id) FROM manufacturing_orders")
    result = cursor.fetchone()[0]
    conn.close()
    return result or 0


def download_remote_db(ssh):
    sftp = ssh.open_sftp()
    sftp.get(REMOTE_DB, LOCAL_DB)
    sftp.close()



def upload_missing_orders(ssh, server_last_id):
    orders = database.get_orders_after_id(server_last_id)

    print("ORDERS TO SEND:", orders)

    if not orders:
        return "Nada que subir"

    payload = json.dumps({"orders": orders})

    cmd = f"python3 {REMOTE_INSERT}"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdin.write(payload)
    stdin.channel.shutdown_write()

    return stdout.read().decode().strip()


def sync_with_server():

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=SERVER,
        username=USER,
        key_filename=KEY_PATH,
        look_for_keys=False,
        allow_agent=False,
    )

    # 🔹 Obtener último ID del servidor
    stdin, stdout, stderr = ssh.exec_command(f"python3 {REMOTE_GET_LAST}")
    server_last_id = int(stdout.read().decode().strip() or 0)

    # 🔹 Obtener último ID local
    local_last_id = get_local_max_id()

    # 🔥 CASO 1: LOCAL tiene más datos → subir
    if local_last_id > server_last_id:
        result = upload_missing_orders(ssh, server_last_id)

        ssh.close()
        return f"Subido al servidor. {result}"

    # 🔥 CASO 2: SERVIDOR tiene más datos → descargar y reemplazar
    elif server_last_id > local_last_id:
        download_remote_db(ssh)
        ssh.close()
        return "Base local reemplazada desde el servidor."

    # 🔹 CASO 3: iguales
    else:
        ssh.close()
        return "Bases ya sincronizadas."
