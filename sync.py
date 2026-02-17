import paramiko
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SERVER = os.getenv("SYNC_SERVER")
USERNAME = os.getenv("SYNC_USER")
LOCAL_DB = os.getenv("LOCAL_DB_PATH")
REMOTE_DB = os.getenv("SYNC_DB_PATH")

KEY_PATH = os.path.expanduser(r"~\.ssh\id_ed25519")


def _connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        SERVER,
        port=22,
        username=USERNAME,
        key_filename=KEY_PATH,
    )
    return ssh


def sync_on_startup():
    """
    Solo descarga si el servidor es más reciente.
    Nunca sube automáticamente.
    """
    print("SHOULD BE SYNCING ON STARTUP")
    ssh = _connect()
    sftp = ssh.open_sftp()

    if not os.path.exists(LOCAL_DB):
        # Si no existe local, descargar directamente
        sftp.get(REMOTE_DB, LOCAL_DB)
        sftp.close()
        ssh.close()
        return "Base descargada (no existía local)."

    local_mtime = os.path.getmtime(LOCAL_DB)
    remote_mtime = sftp.stat(REMOTE_DB).st_mtime

    if remote_mtime > local_mtime:
        sftp.get(REMOTE_DB, LOCAL_DB)
        result = "Base actualizada desde el servidor."
    else:
        result = "Base local ya actualizada."

    sftp.close()
    ssh.close()
    return result


def sync_with_server():
    """
    Sincronización manual completa.
    Sube o baja según cuál sea más reciente.
    """
    ssh = _connect()
    sftp = ssh.open_sftp()

    local_mtime = os.path.getmtime(LOCAL_DB)
    remote_mtime = sftp.stat(REMOTE_DB).st_mtime

    # 🔥 Local más reciente → SUBIR
    if local_mtime > remote_mtime:
        # Backup remoto antes de sobrescribir
        ssh.exec_command("python3 /home/myuser/sync_server/backup.py")
        sftp.put(LOCAL_DB, REMOTE_DB)
        result = "Base de datos subida al servidor."

    # 🔥 Servidor más reciente → DESCARGAR
    elif remote_mtime > local_mtime:
        sftp.get(REMOTE_DB, LOCAL_DB)
        result = "Base de datos actualizada desde el servidor."

    else:
        result = "Bases ya sincronizadas."

    sftp.close()
    ssh.close()
    return result