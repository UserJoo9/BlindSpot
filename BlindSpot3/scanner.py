# scanner.py
import time
import subprocess
import threading
from scapy.all import *
from config import *
from utils import get_vendor

class NetworkScanner:
    def __init__(self, interface, db_handler):
        self.interface = interface
        self.db = db_handler
        self.networks = {}
        self.lock = threading.Lock()
        self.stop_sniffing = False

    def channel_hopper(self):
        ch = 1
        while not self.stop_sniffing:
            try:
                # استخدام iw بدلاً من iwconfig لأنه أسرع وأحدث
                # هذا السطر يجبر الكارت على تغيير القناة
                subprocess.run(["iw", "dev", self.interface, "set", "channel", str(ch)], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                ch = ch + 1 if ch < 13 else 1
                time.sleep(0.5)
            except:
                break

    def packet_handler(self, pkt):
        if not pkt.haslayer(Dot11):
            return

        # ==========================================
        # 1. معالجة Beacons (اكتشاف الشبكات الأساسي)
        # ==========================================
        if pkt.type == 0 and pkt.subtype == 8:
            try:
                bssid = pkt[Dot11].addr2
                if not bssid: return
                bssid = bssid.lower()
                
                rssi = -100
                if pkt.haslayer(RadioTap):
                    rssi = pkt[RadioTap].dBm_AntSignal or -100

                try:
                    ssid = pkt[Dot11Elt].info.decode('utf-8', errors='ignore')
                except:
                    ssid = ""

                stats = pkt[Dot11Beacon].network_stats()
                channel = stats.get("channel", 0)
                raw_crypto = stats.get("crypto", {"OPN"})
                crypto_str = ', '.join(raw_crypto) if isinstance(raw_crypto, set) else str(raw_crypto)

                is_hidden = not ssid or ssid.startswith("\x00")
                display_name = ssid
                is_known = False
                has_handshake = False

                vendor_name = get_vendor(bssid)
                
                # فحص قاعدة البيانات
                db_info = self.db.get_info(bssid)
                if db_info:
                    if isinstance(db_info, dict):
                        saved_name = db_info.get('SSID', '')
                        has_handshake = db_info.get('Handshake', False)
                    else:
                        saved_name = db_info
                    
                    if is_hidden and saved_name:
                        display_name = saved_name
                        is_known = True
                    elif saved_name:
                         is_known = True
                else:
                    if is_hidden: display_name = "<HIDDEN>"
                
                with self.lock:
                    if bssid not in self.networks:
                        self.networks[bssid] = {
                            "SSID": display_name,
                            "Channel": channel,
                            "Crypto": crypto_str,
                            "Hidden": is_hidden,
                            "Known": is_known,
                            "RSSI": rssi,
                            "Handshake": has_handshake,
                            "Vendor": vendor_name,
                            "Clients": set()
                        }
                    else:
                        self.networks[bssid]["RSSI"] = rssi
                        # تحديث الاسم إذا تم كشفه لاحقاً
                        if self.networks[bssid]["SSID"] == "<HIDDEN>" and display_name != "<HIDDEN>":
                            self.networks[bssid]["SSID"] = display_name
                            self.networks[bssid]["Known"] = True
            except:
                pass

        # ==========================================
        # 2. الكاشف الذكي (Passive Revealer)
        # يستمع لـ Probe Response (5) و Association Request (0) و Reassociation (2)
        # ==========================================
        elif pkt.type == 0 and pkt.subtype in [0, 2, 5]:
            try:
                # في حالة Probe Response (5): الراوتر (addr3) يرسل الاسم
                # في حالة Association (0/2): العميل يرسل الاسم للراوتر (addr1)
                
                target_bssid = None
                if pkt.subtype == 5: # Probe Response
                    target_bssid = pkt.addr3.lower()
                elif pkt.subtype in [0, 2]: # Assoc / Reassoc Request
                    target_bssid = pkt.addr1.lower() # BSSID هو المستقبل

                if target_bssid and target_bssid in self.networks:
                    # فقط إذا كانت الشبكة لدينا ما زالت مخفية
                    if self.networks[target_bssid]['SSID'] == "<HIDDEN>":
                        if pkt.haslayer(Dot11Elt):
                            try:
                                elt = pkt.getlayer(Dot11Elt)
                                while elt:
                                    if elt.ID == 0: # SSID Parameter
                                        ssid = elt.info.decode('utf-8', errors='ignore')
                                        if ssid and not ssid.startswith("\x00"):
                                            with self.lock:
                                                # تحديث الذاكرة فوراً
                                                self.networks[target_bssid]['SSID'] = ssid
                                                self.networks[target_bssid]['Hidden'] = False
                                                self.networks[target_bssid]['Known'] = True
                                                # حفظ في قاعدة البيانات
                                                self.db.save(target_bssid, ssid)
                                                # لا نحتاج لإكمال اللوب
                                                return
                                    elt = elt.payload
                            except: pass
            except:
                pass

        # ==========================================
        # 3. معالجة Data Frames (إحصاء العملاء)
        # ==========================================
        elif pkt.type == 2:
            try:
                addr1 = pkt.addr1.lower() if pkt.addr1 else None
                addr2 = pkt.addr2.lower() if pkt.addr2 else None
                
                if not addr1 or not addr2: return

                # استبعاد العناوين الوهمية والبرودكاست
                invalid_prefixes = ("33:33", "01:00:5e", "ff:ff")
                if addr1.startswith(invalid_prefixes) or addr2.startswith(invalid_prefixes):
                    return

                with self.lock:
                    if addr2 in self.networks:
                        self.networks[addr2]["Clients"].add(addr1)
                    elif addr1 in self.networks:
                        self.networks[addr1]["Clients"].add(addr2)
            except:
                pass
