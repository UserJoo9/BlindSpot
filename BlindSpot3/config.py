# config.py
import os

# --- Paths (الترتيب هنا مهم جداً) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "wifi_db.json")
HANDSHAKES_DIR = os.path.join(SCRIPT_DIR, "handshakes") # 1. تعريف المتغير أولاً
VENDOR_FILE = os.path.join(SCRIPT_DIR, "mac-vendor.txt") # المسار الجديد
VENDOR_CACHE_FILE = os.path.join(SCRIPT_DIR, "vendors_cache.json") # الكاش الجديد (للاونلاين)

# Create handshakes dir if not exists
# 2. استخدام المتغير بعد تعريفه
if not os.path.exists(HANDSHAKES_DIR):
    os.makedirs(HANDSHAKES_DIR)

# --- Colors (ANSI) ---
C_GREEN = "\033[1;32m"
C_RED = "\033[1;31m"
C_YELLOW = "\033[1;33m"
C_CYAN = "\033[1;36m"
C_WHITE = "\033[1;37m"
C_GREY = "\033[1;30m"
C_RESET = "\033[0m"

# --- Project Identity ---
APP_NAME = "BlindSpot"
VERSION = "1.0"
AUTHOR = "David Michael Naim"

# --- ASCII Art Banner ---
BANNER = r"""
oooooooooo.  oooo   o8o                    .o8   .oooooo..o                          .   
`888'   `Y8b `888   `"'                   "888  d8P'    `Y8                        .o8   
 888     888  888  oooo  ooo. .oo.    .oooo888  Y88bo.      oo.ooooo.   .ooooo.  .o888oo 
 888oooo888'  888  `888  `888P"Y88b  d88' `888   `"Y8888o.   888' `88b d88' `88b   888   
 888    `88b  888   888   888   888  888   888       `"Y88b  888   888 888   888   888   
 888    .88P  888   888   888   888  888   888  oo     .d8P  888   888 888   888   888 . 
o888bood8P'  o888o o888o o888o o888o `Y8bod88P" 8""88888P'   888bod8P' `Y8bod8P'   "888" 
                                                             888                         
                                                            o888o                
"""

# --- Colors (ANSI) ---
C_GREEN = "\033[1;32m"
C_RED = "\033[1;31m"
C_YELLOW = "\033[1;33m"
C_CYAN = "\033[1;36m"
C_WHITE = "\033[1;37m"
C_GREY = "\033[1;30m"
C_RESET = "\033[0m"
