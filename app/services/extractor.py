import os
import re
import shutil
import tempfile
import time
import urllib.parse
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

from app.config import Config
from app.services.tor_manager import TorManager
from app.services.db import save_key_record

def normalize_confirm_url(url: str) -> str:
    """
    Extracts the direct dashboard.render.com email confirmation URL from any Postmark tracking link.
    """
    url = url.strip()
    if "track.pstmrk.it" in url:
        decoded = urllib.parse.unquote(url)
        m = re.search(r'token=([a-zA-Z0-9_\-]+)', decoded)
        if m:
            return f"https://dashboard.render.com/email-confirm/?token={m.group(1)}"
    return url

class RenderExtractor:
    @staticmethod
    def extract_from_link(
        confirm_url: str,
        key_name: str = None,
        use_tor: bool = False,
        rotate_before: bool = False,
        proxy_mode: str = "residential"
    ) -> dict:
        if not key_name:
            key_name = f"Key-{int(time.time())}"

        clean_url = normalize_confirm_url(confirm_url)

        # Determine proxy configuration and IP
        proxy_config = None
        verify_proxies = None
        ip_used = "unknown"
        is_tor = (proxy_mode == "tor" or use_tor)

        if proxy_mode == "residential" and not use_tor:
            import random
            selected_proxy = random.choice(Config.RESIDENTIAL_PROXIES)
            proxy_config = {
                "server": selected_proxy["server"],
                "username": selected_proxy["username"],
                "password": selected_proxy["password"]
            }
            raw_host = selected_proxy["server"].replace("http://", "").split(":")[0]
            ip_used = raw_host
            cred_str = f"{selected_proxy['username']}:{selected_proxy['password']}@"
            clean_host = selected_proxy["server"].replace("http://", "")
            verify_proxies = {
                "http": f"http://{cred_str}{clean_host}",
                "https": f"http://{cred_str}{clean_host}"
            }
        elif is_tor:
            if rotate_before:
                TorManager.rotate_tor_identity()
            proxy_config = {"server": Config.TOR_SOCKS_PROXY}
            ip_used = TorManager.get_tor_ip()
            verify_proxies = {
                "http": Config.TOR_SOCKS_PROXY,
                "https": Config.TOR_SOCKS_PROXY
            }
        else:
            ip_used = TorManager.get_direct_ip()
            proxy_config = None
            verify_proxies = None

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
                        "--no-zygote",
                        "--single-process",
                        "--renderer-process-limit=1",
                        "--js-flags=--max-old-space-size=64",
                        "--disable-software-rasterizer",
                        "--mute-audio",
                        "--disable-background-networking",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-breakpad",
                        "--disable-component-update",
                        "--disable-sync",
                        "--no-first-run",
                        "--disable-extensions"
                    ]
                }
                
                if proxy_config:
                    launch_kwargs["proxy"] = proxy_config

                context = p.chromium.launch_persistent_context(**launch_kwargs)
                page = context.pages[0] if context.pages else context.new_page()

                # Block heavy external trackers and media to stay strictly within 512MB memory limit
                def route_filter(route):
                    url = route.request.url.lower()
                    blocked = ['intercom', 'hsadspixel', 'datadoghq', 'sentry', 'hotjar', 'posthog']
                    if any(d in url for d in blocked):
                        return route.abort()
                    if route.request.resource_type in ['image', 'media', 'font']:
                        return route.abort()
                    return route.continue_()

                page.route("**/*", route_filter)

                # Step 1: Navigate to confirmation link
                try:
                    page.goto(clean_url, wait_until="domcontentloaded", timeout=45000)
                except Exception as e:
                    context.close()
                    error_msg = f"Failed to load confirmation URL: {str(e)}"
                    save_key_record(
                        status="FAILED",
                        key_name=key_name,
                        used_tor=is_tor,
                        ip_used=ip_used,
                        error=error_msg
                    )
                    return {"success": False, "error": error_msg, "ip_used": ip_used}

                # Step 1.1: Polling loop to wait for confirmation to finish & auth in localStorage (up to 30s)
                is_authenticated = False
                poll_start = time.time()
                while time.time() - poll_start < 30:
                    try:
                        body_text = page.inner_text("body")
                    except Exception:
                        body_text = ""

                    # Check if confirmation link was already expired/invalid
                    if "Invalid or expired activation link" in body_text:
                        context.close()
                        error_msg = "Activation link is already expired or consumed. Do not click the email link manually; let the tool handle it."
                        save_key_record(
                            status="FAILED",
                            key_name=key_name,
                            used_tor=is_tor,
                            ip_used=ip_used,
                            error=error_msg
                        )
                        return {"success": False, "error": error_msg, "ip_used": ip_used}

                    # Check if authenticated via localStorage
                    try:
                        has_auth = page.evaluate("() => Boolean(localStorage.getItem('render-auth'))")
                    except Exception:
                        has_auth = False

                    # Check for onboarding / confirmation success indicators
                    if (
                        has_auth
                        or "Email confirmed!" in body_text
                        or "Create a new workspace" in body_text
                        or "/onboarding" in page.url
                        or "/u/" in page.url
                    ):
                        # If "Skip Survey" link or button is visible, click it to finish onboarding
                        skip_btn = page.locator("button:has-text('Skip Survey'), a:has-text('Skip Survey'), span:has-text('Skip Survey')").first
                        if skip_btn.count() > 0 and skip_btn.is_visible():
                            try:
                                skip_btn.click()
                                time.sleep(2)
                            except Exception:
                                pass
                        is_authenticated = True
                        break

                    time.sleep(1.5)

                if not is_authenticated:
                    try:
                        body_text = page.inner_text("body")
                    except Exception:
                        body_text = ""
                    if "Invalid or expired activation link" in body_text:
                        context.close()
                        error_msg = "Activation link is already expired or consumed. Do not click the email link manually; let the tool handle it."
                        save_key_record(
                            status="FAILED",
                            key_name=key_name,
                            used_tor=is_tor,
                            ip_used=ip_used,
                            error=error_msg
                        )
                        return {"success": False, "error": error_msg, "ip_used": ip_used}

                # Settle time for session storage
                time.sleep(2)

                # Step 2: Navigate to Account Settings
                try:
                    page.goto("https://dashboard.render.com/u/settings", wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    context.close()
                    error_msg = f"Failed to load settings page: {str(e)}"
                    save_key_record(
                        status="FAILED",
                        key_name=key_name,
                        used_tor=is_tor,
                        ip_used=ip_used,
                        error=error_msg
                    )
                    return {"success": False, "error": error_msg, "ip_used": ip_used}

                # Step 2.1: Wait for settings page authentication or redirect to login (up to 25s)
                create_btn = page.locator("button:has-text('Create API key'), button:has-text('Create API Key')").first
                settings_ready = False
                wait_settings_start = time.time()

                while time.time() - wait_settings_start < 25:
                    curr_url = page.url
                    try:
                        curr_body = page.inner_text("body")
                    except Exception:
                        curr_body = ""

                    if "/login" in curr_url or "Sign In to Render" in curr_body:
                        context.close()
                        error_msg = "Not authenticated. The confirmation link did not log in."
                        save_key_record(
                            status="FAILED",
                            key_name=key_name,
                            used_tor=is_tor,
                            ip_used=ip_used,
                            error=error_msg
                        )
                        return {"success": False, "error": error_msg, "ip_used": ip_used}

                    if create_btn.count() > 0 and create_btn.is_visible():
                        settings_ready = True
                        break

                    time.sleep(1.5)

                if not settings_ready:
                    context.close()
                    error_msg = "Could not find 'Create API key' button in settings."
                    save_key_record(
                        status="FAILED",
                        key_name=key_name,
                        used_tor=is_tor,
                        ip_used=ip_used,
                        error=error_msg
                    )
                    return {"success": False, "error": error_msg, "ip_used": ip_used}

                # Step 3: Click 'Create API key'
                create_btn.scroll_into_view_if_needed()
                create_btn.click()
                time.sleep(2)

                # Step 4: Fill key name in dialog
                name_input = page.locator("input[placeholder='name']").first
                if name_input.count() > 0:
                    name_input.wait_for(state="visible", timeout=10000)
                    name_input.fill(key_name)
                else:
                    non_readonly = page.locator("input:not([readonly])").first
                    if non_readonly.count() > 0:
                        non_readonly.wait_for(state="visible", timeout=10000)
                        non_readonly.fill(key_name)

                time.sleep(1)

                # Step 5: Submit dialog
                submit_btn = page.locator("button:has-text('Create API Key')").last
                submit_btn.wait_for(state="visible", timeout=10000)
                submit_btn.click()

                # Step 6: Extract generated key (wait up to 15s)
                api_key = None
                extract_start = time.time()
                while time.time() - extract_start < 15:
                    page_html = page.content()
                    body_text = page.inner_text("body")
                    all_keys = re.findall(r'rnd_[a-zA-Z0-9]{25,}', page_html + " " + body_text)
                    if all_keys:
                        api_key = max(all_keys, key=len)
                        break
                    time.sleep(1)

                if not api_key:
                    context.close()
                    error_msg = "API key was not found after modal submission."
                    save_key_record(
                        status="FAILED",
                        key_name=key_name,
                        used_tor=is_tor,
                        ip_used=ip_used,
                        error=error_msg
                    )
                    return {"success": False, "error": error_msg, "ip_used": ip_used}

                context.close()

                # Step 7: Verify key via Render REST API
                email = None
                workspace = None
                owner_id = None
                verified = False

                try:
                    res = requests.get(
                        "https://api.render.com/v1/owners",
                        headers={"Authorization": f"Bearer {api_key}"},
                        proxies=verify_proxies,
                        timeout=15
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
                    used_tor=is_tor,
                    ip_used=ip_used
                )

                return {
                    "success": True,
                    "api_key": api_key,
                    "email": email,
                    "workspace": workspace,
                    "owner_id": owner_id,
                    "verified": verified,
                    "used_tor": is_tor,
                    "ip_used": ip_used,
                    "key_name": key_name
                }
        finally:
            shutil.rmtree(profile_dir, ignore_errors=True)
            import gc
            gc.collect()
