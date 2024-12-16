import requests
import discord
import random
import string
import asyncio
from discord.ext import commands
from discord import app_commands
import paramiko
import time

WEBHOOK_URL = "Please SUCK your dick"
TOKEN = "not today"
PROXMOX_NODE = "localhost"
SERVER_ID = 1293949144540381185
ALLOWED_ROLES = [1304429499445809203]
TEMPLATE = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
DISK_SIZE = "4G"
BRIDGE = "vmbr0"
CONTAINER_START_SCRIPT = "wget -O ports.sh https://raw.githubusercontent.com/katy-the-kat/realinstallscript/refs/heads/main/installer4space.sh && bash ports.sh"
FILE_PATH = "/home/user/tokens.txt"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

def is_authorized(interaction):
    if interaction.guild.id != SERVER_ID:
        return False
    user_roles = [role.id for role in interaction.user.roles]
    return any(role in ALLOWED_ROLES for role in user_roles)

def generate_token(length=24):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def send_webhook_log(title, description, color=0x3498db):
    embed = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color
        }]
    }
    requests.post(WEBHOOK_URL, json=embed)

def save_vps_details(token, ip, port, password, customer_id):
    port = 22
    entry = f"{token},{ip},{port},{password}\n"
    
    with open(FILE_PATH, "a") as file:
        file.write(entry)

async def create_proxmox_vps(memory, cores, disk, customer_id):
    vps_id = random.randint(1000, 9999)
    random_port = random.randint(10000, 19999)
    vps_name = f"{customer_id}-{random_port}"
    token = generate_token()
    password = generate_token(8)
    memory_mb = memory * 1024
    creation_command = (
        f"pct create {vps_id} {TEMPLATE} --net0 name=eth0,bridge={BRIDGE},firewall=1,ip=dhcp "
        f"--hostname {vps_name} --storage local-lvm --rootfs local-lvm:{disk} --cores {cores} --memory {memory_mb} "
        f"--password {password} --unprivileged 1"
    )
    start_command = f"pct start {vps_id}"
    script_command = f"pct exec {vps_id} -- sh -c 'wget http://32.216.92.224/xe-gen11/tools/raw/branch/main/ports.sh && bash ports.sh'"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(PROXMOX_NODE, username="root")
        for command in [creation_command, start_command]:
            stdin, stdout, stderr = ssh.exec_command(command)
            stderr_output = stderr.read().decode()
            if stderr_output:
                raise Exception(f"Error executing command: {stderr_output}")

        time.sleep(4)
        stdin, stdout, stderr = ssh.exec_command(script_command)
        stderr_output = stderr.read().decode()
        print("Script executed successfully.")
        ip_command = f"pct exec {vps_id} -- ip addr show eth0"
        stdin, stdout, stderr = ssh.exec_command(ip_command)
        ip_output = stdout.read().decode()
        ip_lines = ip_output.splitlines()
        vps_ip = None
        for line in ip_lines:
            if "inet " in line:
                vps_ip = line.split()[1].split('/')[0]
                break
        
        if not vps_ip:
            raise Exception("Unable to retrieve vps IP.")

        save_vps_details(token, vps_ip, 22, password, customer_id)

        return {
            "vps_id": vps_id,
            "token": token,
            "node_ip": PROXMOX_NODE,
            "vps_ip": vps_ip,
            "random_port": random_port,
            "vps_name": vps_name
        }

    finally:
        ssh.close()

@bot.tree.command(name="create-vps", description="Create a Proxmox VPS")
@app_commands.describe(memory="Memory in GB", cores="Number of CPU cores", disk="Disk size (e.g., 4G)", customer="The user to DM")
async def create_vps(interaction: discord.Interaction, memory: int, cores: int, disk: str, customer: discord.Member):
    if not is_authorized(interaction):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Starting vps creation...", ephemeral=True)
    try:
        result = await create_proxmox_vps(memory, cores, disk, customer.id)
        ssh_details = f"""
**Your VPS Instance is Ready!**

ssh ssh@||ssh.is-a.space||
- **Token:** ||`{result['token']}`||
- **VPS ID:** ||`{result['vps_id']}`||
- **SSH Password:** No Password, Just enter token when you're in.

How to use it
- Mobile: Use termius on gplay/appstore
- PC: Use windows terminal

Thank you for choosing KVM-i7, The Best Free Hosting
- is it legit? Neofetch, Send a pic in https://discord.com/channels/1293949144540381185/1305158339298066432
- Is it good? Review us out of 10 in https://discord.com/channels/1293949144540381185/1307723962876170250
- Invite your friends for more upgrades!
        """

        await customer.send(ssh_details)
        send_webhook_log(
            "VPS Created",
            f"**Token:** `{result['token']}`\n**VPS ID:** `{result['vps_id']}`\n**Node IP:** {result['node_ip']}\n**Customer:** <@{customer.id}>",
            color=0x00ff00
        )

        await interaction.followup.send("VPS created and details sent via DM.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is ready. Logged in as {bot.user}")
    activity = discord.Activity(type=discord.ActivityType.watching, name="KVM-i7")
    await bot.change_presence(activity=activity)

bot.run(TOKEN)
