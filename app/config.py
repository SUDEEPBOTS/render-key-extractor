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
    
    # Defaults
    DEFAULT_KEY_NAME = os.getenv("DEFAULT_KEY_NAME", "AutoRenderKey")
    DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "keys.db"))
    
    # Playwright Settings
    BROWSER_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
