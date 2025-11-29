# utils.py
import os
import sys
import subprocess
import time
from datetime import datetime
from config import *

# محاولة استيراد قاعدة بيانات الماكات
try:
    from vendors import lookup_vendor
except ImportError:
    def lookup_vendor(mac): return "Unknown"

def get_vendor(mac):
    return lookup_vendor(mac)

def get_current_time_12h():
    return datetime.now().strftime("%I:%M %p")

def check_root():
    if os.geteuid() != 0:
        print(f"{C_RED}[-] This script must be run as root (sudo).{C_RESET}")
        sys.exit(1)

def check_interface_exists(interface):
    # التحقق من الأسماء المحتملة (الأصلي أو المضاف له mon)
    possible_names = [interface, interface + "mon", "wlan0mon", "mon0"]
    for name in possible_names:
        if os.path.exists(f"/sys/class/net/{name}"):
            return name
    
    print(f"{C_RED}[-] Error: Interface '{interface}' not found.{C_RESET}")
    sys.exit(1)

def enable_monitor_mode(interface):
    print(f"\n{C_YELLOW}[*] Preparing Interface...{C_RESET}")

    # 1. قتل العمليات التي قد تعيق عمل الكارت (ضروري جداً)
    os.system("airmon-ng check kill > /dev/null 2>&1")
    os.system("pkill -9 wpa_supplicant > /dev/null 2>&1")
    os.system("pkill -9 dhclient > /dev/null 2>&1")
    os.system("pkill -9 NetworkManager > /dev/null 2>&1")
    os.system("service NetworkManager stop > /dev/null 2>&1")
    
    # فك الحظر عن الكارت
    os.system("rfkill unblock wifi > /dev/null 2>&1")
    os.system("rfkill unblock all > /dev/null 2>&1")
    
    time.sleep(0.5)

    # 2. الفحص الذكي: هل الكارت في وضع Monitor بالفعل؟
    # نتحقق من الاسم الأصلي والأسماء المحتملة
    check_list = [interface, interface + "mon", "wlan0mon"]
    
    for iface in check_list:
        if os.path.exists(f"/sys/class/net/{iface}"):
            try:
                # قراءة الوضع الحالي
                iw_out = subprocess.getoutput(f"iwconfig {iface}")
                if "Mode:Monitor" in iw_out:
                    print(f"{C_GREEN}[+] Interface '{iface}' is ALREADY in Monitor Mode.{C_RESET}")
                    # التأكد من أنه مرفوع ويعمل
                    os.system(f"ip link set {iface} up")
                    # ضبطه على قناة افتراضية لتنشيطه
                    os.system(f"iwconfig {iface} channel 1")
                    return iface
            except:
                pass

    print(f"{C_CYAN}[*] Setting Monitor Mode on {interface}...{C_RESET}")

    # 3. إذا لم يكن مفعل، نقوم بتفعيله يدوياً (الطريقة الآمنة)
    try:
        os.system(f"ip link set {interface} down")
        time.sleep(0.3)
        os.system(f"iwconfig {interface} mode monitor")
        time.sleep(0.3)
        os.system(f"ip link set {interface} up")
        
        # التحقق
        if "Mode:Monitor" in subprocess.getoutput(f"iwconfig {interface}"):
            print(f"{C_GREEN}[+] Monitor Mode Enabled on: {interface}{C_RESET}")
            return interface
    except:
        pass

    # 4. الحل الأخير: استخدام airmon-ng
    print(f"{C_YELLOW}[!] Manual method failed, trying airmon-ng...{C_RESET}")
    os.system(f"airmon-ng start {interface} > /dev/null 2>&1")
    
    # البحث عن الاسم الجديد
    if os.path.exists(f"/sys/class/net/{interface}mon"):
        print(f"{C_GREEN}[+] Monitor Mode Enabled on: {interface}mon{C_RESET}")
        return interface + "mon"
    
    return interface

def restore_managed_mode(interface):
    # هذه الدالة موجودة لكن لن يتم استدعاؤها تلقائياً بناءً على طلبك
    # لكي لا يعلق الكارت عند الخروج
    print(f"\n{C_YELLOW}[*] Info: Interface left in Monitor Mode.{C_RESET}")
    # إذا أردت استعادة الوضع يدوياً في المستقبل، يمكنك إلغاء تعليق الأسطر التالية:
    # os.system(f"airmon-ng stop {interface} > /dev/null 2>&1")
    # os.system("service NetworkManager start")

def verify_password_aircrack(pcap_file, bssid, password):
    if not os.path.exists(pcap_file): return False
    temp_pass_file = "temp_pass.txt"
    with open(temp_pass_file, 'w') as f: f.write(password)
    try:
        cmd = ["aircrack-ng", "-w", temp_pass_file, "-b", bssid, pcap_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(temp_pass_file): os.remove(temp_pass_file)
        return "KEY FOUND!" in result.stdout
    except:
        if os.path.exists(temp_pass_file): os.remove(temp_pass_file)
        return False