import json
import subprocess
import paramiko
import database

SERVER = "95.217.233.118"
USER = "myuser"
PORT = 22

REMOTE_GET_LAST = "/home/myuser/sync_server/get_last_order_id.py"
REMOTE_INSERT = "/home/myuser/sync_server/insert_orders.py"


def sync_with_server():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, port=PORT, username=USER)

    # 1️⃣ Obtener último order_id del servidor
    stdin, stdout, stderr = ssh.exec_command(f"python3 {REMOTE_GET_LAST}")
    last_id = int(stdout.read().decode().strip() or 0)

    # 2️⃣ Obtener órdenes locales posteriores
    orders = database.get_orders_after_id(last_id)


    if not orders:
        ssh.close()
        return "Nada que sincronizar"

    payload = json.dumps({"orders": orders})

    # 3️⃣ Enviar órdenes
    cmd = f"python3 {REMOTE_INSERT}"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdin.write(payload)
    stdin.channel.shutdown_write()

    result = stdout.read().decode().strip()
    ssh.close()
    return result
