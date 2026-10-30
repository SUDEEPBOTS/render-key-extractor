import random
import re
import string
import requests

YUKI_MAIL_BASE = "https://mail.yukisbox.com"

class MailService:
    @staticmethod
    def get_domains(provider: str = "yuki") -> list:
        try:
            r = requests.get(
                f"{YUKI_MAIL_BASE}/api/domains",
                params={"provider": provider},
                timeout=8
            )
            if r.status_code == 200:
                domains = r.json()
                if isinstance(domains, list) and domains:
                    return domains
        except Exception:
            pass
        return ["yukisbox.com", "yukiapi.site"]

    @staticmethod
    def generate_credentials(domain: str = None, provider: str = "yuki") -> dict:
        if not domain:
            avail = MailService.get_domains(provider)
            domain = avail[0] if avail else "yukisbox.com"

        username = "rnd" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        # Generate clean strong password
        pass_chars = string.ascii_letters + string.digits
        random_suffix = "".join(random.choices(pass_chars, k=8))
        password = f"Rnd@{random_suffix}#9"

        try:
            r = requests.post(
                f"{YUKI_MAIL_BASE}/api/account",
                params={"provider": provider},
                json={"username": username, "domain": domain},
                timeout=12
            )
            data = r.json()
            if r.status_code == 200 and data.get("success"):
                address = data.get("address")
                token = data.get("token") or address
                return {
                    "success": True,
                    "email": address,
                    "token": token,
                    "password": password,
                    "domain": domain,
                    "provider": provider,
                    "signup_url": "https://dashboard.render.com/register"
                }
            return {
                "success": False,
                "error": data.get("detail", f"Failed to create mailbox on {provider}")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def check_render_email(token: str, provider: str = "yuki", exclude_ids: str = None) -> dict:
        try:
            r = requests.get(
                f"{YUKI_MAIL_BASE}/api/emails",
                params={"token": token, "provider": provider},
                timeout=10
            )
            if r.status_code != 200:
                return {"found": False, "error": f"HTTP {r.status_code}"}

            emails = r.json()
            if not isinstance(emails, list) or not emails:
                return {"found": False, "count": 0}

            pattern = r'(https?://(?:track\.pstmrk\.it/3[a-z]?/dashboard\.render\.com%2Femail-confirm[^\s"\'<>]+|dashboard\.render\.com/email-confirm[^\s"\'<>]+))'

            excluded_set = set()
            if exclude_ids:
                excluded_set = {str(x).strip() for x in re.split(r'[,;|\s]+', str(exclude_ids)) if str(x).strip()}

            # Iterate through emails to find the one containing the activation link
            for em in emails:
                msg_id = str(em.get("id"))
                if msg_id in excluded_set:
                    continue

                subject = em.get("subject", "")
                
                # Fetch email detail
                detail_res = requests.get(
                    f"{YUKI_MAIL_BASE}/api/email/{msg_id}",
                    params={"token": token, "provider": provider},
                    timeout=10
                )
                if detail_res.status_code == 200:
                    detail = detail_res.json()
                    combined_text = (detail.get("textBody") or "") + " " + (detail.get("htmlBody") or "")
                    matches = re.findall(pattern, combined_text)
                    if matches:
                        import urllib.parse
                        raw_url = matches[0]
                        clean_url = raw_url
                        if "track.pstmrk.it" in raw_url:
                            decoded = urllib.parse.unquote(raw_url)
                            m = re.search(r'token=([a-zA-Z0-9_\-]+)', decoded)
                            if m:
                                clean_url = f"https://dashboard.render.com/email-confirm/?token={m.group(1)}"

                        return {
                            "found": True,
                            "msg_id": msg_id,
                            "subject": subject,
                            "date": em.get("date"),
                            "confirm_url": clean_url
                        }

            return {
                "found": False,
                "count": len(emails),
                "waiting_for_link": True
            }
        except Exception as e:
            return {"found": False, "error": str(e)}
