import os
import paramiko

KEY_PATH = os.path.expanduser(r"~\.ssh\id_ed25519")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

ssh.connect(
    hostname="95.217.233.118",
    username="myuser",
    key_filename=KEY_PATH,
    look_for_keys=False,
    allow_agent=False,
)

stdin, stdout, stderr = ssh.exec_command("whoami")
print(stdout.read().decode())

ssh.close()
