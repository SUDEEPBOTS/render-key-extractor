import socket
import time
import requests
from app.config import Config

class TorManager:
    @staticmethod
    def get_direct_ip(timeout: int = 5) -> str:
        try:
            r = requests.get("https://api.ipify.org?format=json", timeout=timeout)
            if r.status_code == 200:
                return r.json().get("ip", "Unknown")
        except Exception as e:
            return f"Error: {e}"
        return "Unknown"

    @staticmethod
    def get_tor_ip(timeout: int = 8) -> str:
        proxies = {
            "http": Config.TOR_SOCKS_PROXY,
            "https": Config.TOR_SOCKS_PROXY
        }
        try:
            r = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=timeout)
            if r.status_code == 200:
                return r.json().get("ip", "Unknown")
        except Exception as e:
            return f"Error: {e}"
        return "Unknown"

    @staticmethod
    def rotate_tor_identity() -> dict:
        """
        Sends SIGNAL NEWNYM to Tor ControlPort to switch to a fresh exit circuit.
        """
        old_ip = TorManager.get_tor_ip(timeout=5)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((Config.TOR_CONTROL_HOST, Config.TOR_CONTROL_PORT))
            s.sendall(b"AUTHENTICATE\r\nSIGNAL NEWNYM\r\nQUIT\r\n")
            response = s.recv(1024).decode()
            s.close()
            
            # Allow Tor a brief pause to build new circuit
            time.sleep(2)
            new_ip = TorManager.get_tor_ip(timeout=6)
            
            success = "250 OK" in response
            return {
                "success": success,
                "old_ip": old_ip,
                "new_ip": new_ip,
                "raw_response": response.strip()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "old_ip": old_ip,
                "new_ip": old_ip
            }

    @staticmethod
    def get_status() -> dict:
        is_port_open = False
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((Config.TOR_CONTROL_HOST, Config.TOR_CONTROL_PORT))
            s.close()
            is_port_open = True
        except Exception:
            is_port_open = False

        tor_ip = TorManager.get_tor_ip(timeout=4) if is_port_open else "Tor offline"
        direct_ip = TorManager.get_direct_ip(timeout=4)

        return {
            "tor_active": is_port_open and not tor_ip.startswith("Error"),
            "tor_ip": tor_ip,
            "direct_ip": direct_ip,
            "socks_proxy": Config.TOR_SOCKS_PROXY,
            "control_port": Config.TOR_CONTROL_PORT
        }
