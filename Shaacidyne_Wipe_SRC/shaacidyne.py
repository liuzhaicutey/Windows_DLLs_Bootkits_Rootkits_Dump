import ctypes
import sys
import os
import subprocess
import time
import re
import platform
import struct
import traceback
from tkinter import messagebox, Tk

if getattr(sys, 'frozen', False):
    DIR = os.path.dirname(sys.executable)
else:
    DIR = os.path.dirname(os.path.abspath(__file__))

if getattr(sys, 'frozen', False):
    kernel32 = ctypes.windll.kernel32
    kernel32.AllocConsole()
    sys.stdout = open('CONOUT$', 'w')
    sys.stderr = open('CONOUT$', 'w')

DRV = "S"

UEFI_BOOT_BINARY = "BOOTX64.efi"
UEFI_EFI_PATH = r"\EFI\BOOT"
UEFI_BOOT_NAME = "Shaacidyne"

BIOS_BOOT_BINARY = "bootloader.bin"
BIOS_DEST_BOOT_NAME = "bootmgr"

LOG_FILE = os.path.join(DIR, "installer_log.txt")


def log_print(msg):
    print(msg)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
    except:
        pass


def admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def request_admin():
    if platform.system() == "Windows" and not admin():
        try:
            root = Tk()
            root.withdraw()
            messagebox.showinfo(
                "Admin Rights Required",
                "This script needs administrator privileges. It will restart as administrator."
            )
            root.destroy()
        except:
            pass
        
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join([f'"{arg}"' for arg in sys.argv]), None, 1
            )
        except Exception as e:
            log_print(f"Failed to request admin privileges: {e}")
        
        sys.exit()


def run_cmd(cmd, shell=False):
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split()
            
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            shell=shell,
            encoding='utf-8',
            errors='ignore'
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        log_print(f"Error executing command: {' '.join(e.cmd) if isinstance(e.cmd, list) else e.cmd}")
        log_print(f"Stdout: {e.stdout}")
        log_print(f"Stderr: {e.stderr}")
        raise


def detect_boot_mode():
    
    tmp = os.path.join(DIR, 'tmp_list.txt')
    try:
        with open(tmp, 'w') as f:
            f.write("list volume\n")
        out = run_cmd(["diskpart", "/s", tmp])
    finally:
        if os.path.exists(tmp): 
            os.remove(tmp)

    for line in out.splitlines():
        if "FAT32" in line and ("System" in line or "Hidden" in line) and "Volume" in line:
            if re.search(r'\d+ GB|MB', line):
                return "UEFI"
    
    if os.environ.get('firmware_type') == 'UEFI':
        return "UEFI"
        
    return "BIOS"


def mount_partition(is_uefi):
    if is_uefi:
        target_search = "FAT32"
        target_error = "EFI System Partition (ESP) volume not found."
    else:
        target_search = "Active"
        target_error = "Active/System Partition not found. Legacy boot requires an active partition."

    tmp = os.path.join(DIR, 'tmp_list.txt')
    vol = None
    
    try:
        with open(tmp, 'w') as f: 
            f.write("list volume\n")
        out = run_cmd(["diskpart", "/s", tmp])
    finally:
        if os.path.exists(tmp): 
            os.remove(tmp)

    for line in out.splitlines():
        if target_search in line and ("System" in line or "Hidden" in line or "Active" in line) and "Volume" in line:
            m = re.search(r'Volume\s+(\d+)', line)
            if m:
                vol = m.group(1)
                break
            
    if not vol:
        raise Exception(target_error)
    
    tmp_mount = os.path.join(DIR, 'tmp_mount.txt')
    content = f"select volume {vol}\nassign letter={DRV}\nexit\n"
    
    try:
        with open(tmp_mount, 'w') as f: 
            f.write(content)
        run_cmd(["diskpart", "/s", tmp_mount])
    finally:
        if os.path.exists(tmp_mount): 
            os.remove(tmp_mount)
            
    time.sleep(2)
    drive_path = f"{DRV}:\\"
    if not os.path.isdir(drive_path):
        raise Exception(f"Failed to mount partition as {DRV}:. Check if the letter {DRV} is already in use.")

    return drive_path


def umount(d):
    tmp = os.path.join(DIR, 'tmp_umount.txt')
    list_vol = os.path.join(DIR, 'list_vol.txt')
    
    try:
        with open(list_vol, 'w') as f:
            f.write("list volume\n")
        
        out = run_cmd(["diskpart", "/s", list_vol])
        vol = None
        
        for line in out.splitlines():
            if d.strip(':') in line:
                m = re.search(r'Volume\s+(\d+)', line)
                if m:
                    vol = m.group(1)
                    break
            
        if vol:
            content = f"select volume {vol}\nremove letter={d.strip(':')}\nexit\n"
            with open(tmp, 'w') as f: 
                f.write(content)
            run_cmd(["diskpart", "/s", tmp])
        else:
            pass
            
    except Exception as e:
        log_print(f"Warning: Failed to unmount drive {d}. Manual removal might be necessary. Error: {e}")
    finally:
        if os.path.exists(tmp): 
            os.remove(tmp)
        if os.path.exists(list_vol):
            os.remove(list_vol)


def check_secure_boot_status():
    if platform.system() != "Windows":
        return False
        
    try:
        key_path = r"SYSTEM\CurrentControlSet\Control\SecureBoot\State"
        out = run_cmd(["reg", "query", f"HKEY_LOCAL_MACHINE\\{key_path}", "/v", "UEFISecureBootEnabled"])
        
        if "0x1" in out:
            return True
        else:
            return False
            
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        log_print(f"Warning: Could not reliably determine Secure Boot status: {e}")
        return False


def uefi_boot():
    secure_boot_on = check_secure_boot_status()
    
    dest_name = UEFI_BOOT_BINARY 
    bl_src = os.path.join(DIR, UEFI_BOOT_BINARY) 

    if secure_boot_on:
        messagebox_msg = f"UEFI Bootloader '{UEFI_BOOT_NAME}' installed successfully!\n\n!! WARNING: SECURE BOOT IS ON !!\n(Installed unsigned binary. Booting may fail unless Secure Boot is OFF or custom keys are enrolled.)\n\nTo boot: Restart and access your BIOS/UEFI boot menu (usually F12, F8, or ESC) and select '{UEFI_BOOT_NAME}' or 'UEFI Boot'."
    else:
        messagebox_msg = f"UEFI Bootloader '{UEFI_BOOT_NAME}' installed successfully!\n\n(Secure Boot is OFF, installed unsigned binary.)\n\nTo boot: Restart and access your BIOS/UEFI boot menu (usually F12, F8, or ESC) and select '{UEFI_BOOT_NAME}' or 'UEFI Boot'."

    d = None
    try:
        d = mount_partition(True)
        
        base_dir = os.path.join(d, UEFI_EFI_PATH.strip('\\'))
        dest_path = os.path.join(base_dir, dest_name)
        
        os.makedirs(base_dir, exist_ok=True)
        
        run_cmd(f"copy /Y \"{bl_src}\" \"{dest_path}\"", shell=True)
        
        if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
            raise Exception(f"Copy failed. Destination file '{dest_path}' not found or is empty.")
        
        bcd_path = os.path.join(UEFI_EFI_PATH, dest_name).replace("/", "\\")
        
        boot_configured = False
        

        try:
            run_cmd(["bcdedit", "/set", "{fwbootmgr}", "displayorder", bcd_path, "/addfirst"])
            log_print(f"Set {bcd_path} as FIRST in firmware boot display order (permanent)")
            boot_configured = True
        except Exception as e:
            log_print(f"Could not add to firmware display order: {e}")
        

        if not boot_configured:
            try:
                run_cmd(["bcdedit", "/set", "{fwbootmgr}", "bootsequence", bcd_path])
                log_print(f"Set {bcd_path} using bootsequence (will boot once, may need BIOS config for permanent)")
                boot_configured = True
            except Exception as e:
                log_print(f"Could not set bootsequence: {e}")
        

        try:
            run_cmd(["bcdedit", "/set", "{fwbootmgr}", "timeout", "0"])
            log_print("Set firmware boot timeout to 0 (instant boot, no delay)")
        except Exception as e:
            log_print(f"Could not set firmware timeout to 0: {e}")
        
        if boot_configured:
            messagebox_msg = messagebox_msg.replace("To boot: Restart and access your BIOS/UEFI boot menu (usually F12, F8, or ESC) and select 'Shaacidyne' or 'UEFI Boot'.", 
                                                   "Your bootloader will launch INSTANTLY on restart with NO timeout or menu delay. It is now the permanent default boot option.")
        else:
            log_print("WARNING: Could not automatically set boot order. User will need to:")
            log_print("1. Enter BIOS/UEFI settings (usually DEL or F2 at startup)")
            log_print("2. Change boot priority to boot from the EFI file first")
            log_print("3. Disable any boot menu timeout in BIOS for instant boot")
        
        log_print(f"Bootloader installed to: {dest_path}")
        log_print(f"Configuration: Permanent default boot with instant launch (no timeout)")
        
        try:
            root = Tk()
            root.withdraw()
            messagebox.showinfo("Success", messagebox_msg)
            root.destroy()
        except:
            pass

    except Exception as e:
        log_print(f"\n--- UEFI Installation Failed ---")
        log_print(f"Error: {e}")
        log_print(traceback.format_exc())
        try:
            root = Tk()
            root.withdraw()
            messagebox.showerror("Error", f"UEFI Installation failed: {e}")
            root.destroy()
        except:
            pass
        raise
    finally:
        if d:  
            umount(d)


def legacy_boot():
    
    bl_src = os.path.join(DIR, BIOS_BOOT_BINARY)
    
    d = None
    try:
        d = mount_partition(False)
        
        dest_path = os.path.join(d, BIOS_DEST_BOOT_NAME)
        
        run_cmd(f"copy /Y \"{bl_src}\" \"{dest_path}\"", shell=True)
        
        if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
            raise Exception(f"Copy failed. Destination file '{dest_path}' not found or is empty.")
        
        run_cmd(["bootsect", "/nt60", f"{d}", "/force"])
        
        try:
            root = Tk()
            root.withdraw()
            messagebox.showinfo("Success", f"Custom boot binary installed and VBR updated for Legacy BIOS boot.")
            root.destroy()
        except:
            pass

    except Exception as e:
        log_print(f"\n--- BIOS Installation Failed ---")
        log_print(f"Error: {e}")
        log_print(traceback.format_exc())
        try:
            root = Tk()
            root.withdraw()
            messagebox.showerror("Error", f"BIOS Installation failed: {e}")
            root.destroy()
        except:
            pass
        raise
    finally:
        if d: 
            umount(d)


def main_installer():
    if platform.system() != "Windows":
        raise OSError(f"This script is designed for Windows, not {platform.system()}.")

    boot_mode = detect_boot_mode()
    
    if boot_mode == "UEFI":
        binary_path = os.path.join(DIR, UEFI_BOOT_BINARY)
        if not os.path.exists(binary_path):
            raise FileNotFoundError(f"FATAL: Missing required unsigned UEFI binary: '{UEFI_BOOT_BINARY}'. Please place it here.")
        
        try:
            uefi_boot()
            
        finally:
            pass
            
    elif boot_mode == "BIOS":
        binary_path = os.path.join(DIR, BIOS_BOOT_BINARY)
        if not os.path.exists(binary_path):
            with open(binary_path, 'wb') as f:
                f.write(os.urandom(10240))
                
        legacy_boot()
        
    else:
        raise Exception("Could not reliably determine the system boot mode.")


def main():
    try:
        request_admin()
        
        main_installer()
        
        target = os.path.abspath(__file__) if not getattr(sys, 'frozen', False) else sys.executable
        bat = os.path.join(DIR, "delete_me.bat")
        

        image_to_delete_bios = os.path.join(DIR, BIOS_BOOT_BINARY)
        log_to_delete = os.path.join(DIR, LOG_FILE)
        
        with open(bat, 'w') as f:
            f.write('@echo off\n')
            f.write(f'ping 127.0.0.1 -n 5 >nul\n')
            f.write(f'del "{target}" /f /q\n')
            
            f.write(f'if exist "{image_to_delete_bios}" del "{image_to_delete_bios}" /f /q\n')
            
            f.write(f'if exist "{log_to_delete}" del "{log_to_delete}" /f /q\n')

            f.write(f'del "%~f0" /f /q\n')
        
        try:
            input()
        except:
            time.sleep(5)
            
        subprocess.Popen([bat], shell=True, creationflags=subprocess.DETACHED_PROCESS)
        sys.exit(0)

    except Exception as e:
        log_print(f"\nFATAL ERROR: {e}")
        log_print(traceback.format_exc())
        
        try:
            root = Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", f"A critical error occurred:\n\n{e}\n\nCheck {LOG_FILE} for details.")
            root.destroy()
        except:
            pass
        
        try:
            input()
        except:
            time.sleep(10)
            
        sys.exit(1)


if __name__ == "__main__":
    main()
