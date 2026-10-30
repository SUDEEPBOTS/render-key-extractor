import os
import re
import shutil
import tempfile
import time
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

from app.config import Config
from app.services.tor_manager import TorManager
from app.services.db import save_key_record

class RenderExtractor:
    @staticmethod
    def extract_from_link(
        confirm_url: str,
        key_name: str = None,
        use_tor: bool = False,
        rotate_before: bool = False
    ) -> dict:
        if not key_name:
            key_name = f"Key-{int(time.time())}"

        # Rotate Tor circuit if requested
        if use_tor and rotate_before:
            TorManager.rotate_tor_identity()

        # Determine IP being used
        ip_used = TorManager.get_tor_ip() if use_tor else TorManager.get_direct_ip()

        profile_dir = tempfile.mkdtemp(prefix="render_sess_")
        
        try:
            with sync_playwright() as p:
                launch_kwargs = {
                    "user_data_dir": profile_dir,
                    "headless": True,
                    "user_agent": Config.BROWSER_USER_AGENT,
                    "viewport": {"width": 1280, "height": 900},
                    "args": [
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--no-first-run",
                        "--disable-extensions"
                    ]
                }
                
                if use_tor:
                    launch_kwargs["proxy"] = {"server": Config.TOR_SOCKS_PROXY}

                context = p.chromium.launch_persistent_context(**launch_kwargs)
                page = context.pages[0] if context.pages else context.new_page()

                # Step 1: Navigate to confirmation link
                try:
                    page.goto(confirm_url, wait_until="domcontentloaded", timeout=40000)
                except Exception as e:
                    context.close()
                    error_msg = f"Failed to load confirmation URL: {str(e)}"
                    save_key_record(
                        status="FAILED",
                        key_name=key_name,
                        used_tor=use_tor,
                        ip_used=ip_used,
                        error=error_msg
                    )
                    return {"success": False, "error": error_msg, "ip_used": ip_used}

                time.sleep(4)

                # Check if confirmation link was already expired/invalid
                page_text = page.inner_text("body")
                if "Invalid or expired activation link" in page_text:
                    context.close()
                    error_msg = "Confirmation link is invalid or already expired."
                    save_key_record(
                        status="FAILED",
                        key_name=key_name,
                        used_tor=use_tor,
                        ip_used=ip_used,
                        error=error_msg
                    )
                    return {"success": False, "error": error_msg, "ip_used": ip_used}

                # Step 2: Navigate to Account Settings
                page.goto("https://dashboard.render.com/u/settings", wait_until="domcontentloaded", timeout=25000)
                time.sleep(4)

                # Check if authenticated or redirected to login
                content = page.content()
                if "Sign In to Render" in content or "/login" in page.url:
                    context.close()
                    error_msg = "Not authenticated. The confirmation link did not log in."
                    save_key_record(
                        status="FAILED",
                        key_name=key_name,
                        used_tor=use_tor,
                        ip_used=ip_used,
                        error=error_msg
                    )
                    return {"success": False, "error": error_msg, "ip_used": ip_used}

                # Step 3: Click 'Create API key'
                btn = page.locator("button:has-text('Create API key'), button:has-text('Create API Key')").first
                if btn.count() == 0:
                    context.close()
                    error_msg = "Could not find 'Create API key' button in settings."
                    save_key_record(
                        status="FAILED",
                        key_name=key_name,
                        used_tor=use_tor,
                        ip_used=ip_used,
                        error=error_msg
                    )
                    return {"success": False, "error": error_msg, "ip_used": ip_used}

                btn.scroll_into_view_if_needed()
                btn.click()
                time.sleep(2)

                # Step 4: Fill key name in dialog
                name_input = page.locator("input[placeholder='name']").first
                if name_input.count() > 0:
                    name_input.fill(key_name)
                else:
                    non_readonly = page.locator("input:not([readonly])").first
                    if non_readonly.count() > 0:
                        non_readonly.fill(key_name)

                time.sleep(1)

                # Step 5: Submit dialog
                submit_btn = page.locator("button:has-text('Create API Key')").last
                submit_btn.click()
                time.sleep(5)

                # Step 6: Extract generated key
                page_html = page.content()
                body_text = page.inner_text("body")
                all_keys = re.findall(r'rnd_[a-zA-Z0-9]+', page_html + " " + body_text)
                valid_keys = [k for k in all_keys if len(k) >= 25]

                if not valid_keys:
                    context.close()
                    error_msg = "API key was not found after modal submission."
                    save_key_record(
                        status="FAILED",
                        key_name=key_name,
                        used_tor=use_tor,
                        ip_used=ip_used,
                        error=error_msg
                    )
                    return {"success": False, "error": error_msg, "ip_used": ip_used}

                api_key = max(valid_keys, key=len)
                context.close()

                # Step 7: Verify key via Render REST API
                verify_proxies = None
                if use_tor:
                    verify_proxies = {
                        "http": Config.TOR_SOCKS_PROXY,
                        "https": Config.TOR_SOCKS_PROXY
                    }

                email = None
                workspace = None
                owner_id = None
                verified = False

                try:
                    res = requests.get(
                        "https://api.render.com/v1/owners",
                        headers={"Authorization": f"Bearer {api_key}"},
                        proxies=verify_proxies,
                        timeout=12
                    )
                    if res.status_code == 200:
                        verified = True
                        owners = res.json()
                        if owners and len(owners) > 0:
                            owner_info = owners[0].get("owner", {})
                            email = owner_info.get("email")
                            workspace = owner_info.get("name")
                            owner_id = owner_info.get("id")
                except Exception as e:
                    print(f"Verification warning: {e}")

                # Save record to database
                save_key_record(
                    status="SUCCESS",
                    api_key=api_key,
                    email=email,
                    workspace=workspace,
                    owner_id=owner_id,
                    key_name=key_name,
                    used_tor=use_tor,
                    ip_used=ip_used
                )

                return {
                    "success": True,
                    "api_key": api_key,
                    "email": email,
                    "workspace": workspace,
                    "owner_id": owner_id,
                    "verified": verified,
                    "used_tor": use_tor,
                    "ip_used": ip_used,
                    "key_name": key_name
                }
        finally:
            shutil.rmtree(profile_dir, ignore_errors=True)
