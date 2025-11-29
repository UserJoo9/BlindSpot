# database.py
import json
import os
from config import DB_FILE, C_RED, C_RESET

class DatabaseHandler:
    def __init__(self):
        self.known_networks = {}
        self.load()

    def load(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r') as f:
                    self.known_networks = json.load(f)
            except:
                self.known_networks = {}

    def save(self, bssid, ssid):
        bssid_key = bssid.lower()
        if bssid_key in self.known_networks:
            if isinstance(self.known_networks[bssid_key], dict):
                self.known_networks[bssid_key]['SSID'] = ssid
            else:
                self.known_networks[bssid_key] = {"SSID": ssid, "Handshake": False, "HSTime": "", "HSFile": ""}
        else:
            self.known_networks[bssid_key] = {"SSID": ssid, "Handshake": False, "HSTime": "", "HSFile": ""}
            
        self._write_to_file()

    def update_handshake(self, bssid, captured=True, time_str="", filename=""):
        bssid_key = bssid.lower()
        if bssid_key in self.known_networks:
            if not isinstance(self.known_networks[bssid_key], dict):
                current_ssid = self.known_networks[bssid_key]
                self.known_networks[bssid_key] = {"SSID": current_ssid}
            
            self.known_networks[bssid_key]['Handshake'] = captured
            self.known_networks[bssid_key]['HSTime'] = time_str
            if filename:
                self.known_networks[bssid_key]['HSFile'] = filename # تخزين مسار الملف
            
            self._write_to_file()

    def _write_to_file(self):
        try:
            with open(DB_FILE, 'w') as f:
                json.dump(self.known_networks, f, indent=4)
        except Exception as e:
            print(f"{C_RED}[-] DB Save Error: {e}{C_RESET}")
            
    def get_info(self, bssid):
        return self.known_networks.get(bssid.lower(), None)
