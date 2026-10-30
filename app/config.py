import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8090))
    
    # Tor Settings
    TOR_SOCKS_PROXY = os.getenv("TOR_SOCKS_PROXY", "socks5://127.0.0.1:9050")
    TOR_CONTROL_HOST = os.getenv("TOR_CONTROL_HOST", "127.0.0.1")
    TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", 9051))

    # Fresh Residential Proxies Pool
    RESIDENTIAL_PROXIES = [
        {"server": "http://45.38.107.97:6014", "username": "chvijenw", "password": "hbahiq5k56ll"},
        {"server": "http://64.137.96.74:6641", "username": "chvijenw", "password": "hbahiq5k56ll"},
        {"server": "http://198.23.243.226:6361", "username": "chvijenw", "password": "hbahiq5k56ll"},
        {"server": "http://38.154.185.97:6370", "username": "chvijenw", "password": "hbahiq5k56ll"},
        {"server": "http://84.247.60.125:6095", "username": "chvijenw", "password": "hbahiq5k56ll"},
        {"server": "http://191.96.254.138:6185", "username": "chvijenw", "password": "hbahiq5k56ll"},
        {"server": "http://198.46.161.42:5092", "username": "chvijenw", "password": "hbahiq5k56ll"},
        {"server": "http://64.137.10.153:5803", "username": "chvijenw", "password": "hbahiq5k56ll"},
        {"server": "http://104.164.49.38:7693", "username": "chvijenw", "password": "hbahiq5k56ll"},
        {"server": "http://23.26.71.145:5628", "username": "chvijenw", "password": "hbahiq5k56ll"},
    ]
    
    # Defaults
    DEFAULT_KEY_NAME = os.getenv("DEFAULT_KEY_NAME", "AutoRenderKey")
    DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "keys.db"))
    
    # Playwright Settings
    BROWSER_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
