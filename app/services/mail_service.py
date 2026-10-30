import random
import re
import string
import requests

YUKI_MAIL_BASE = "https://mail.yukisbox.com"

class MailService:
    @staticmethod
    def generate_credentials(domain: str = "yukisbox.com") -> dict:
        username = "rnd" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        # Generate clean strong password
        pass_chars = string.ascii_letters + string.digits
        random_suffix = "".join(random.choices(pass_chars, k=8))
        password = f"Rnd@{random_suffix}#9"

        try:
            r = requests.post(
                f"{YUKI_MAIL_BASE}/api/account",
                json={"username": username, "domain": domain},
                timeout=10
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
                    "signup_url": "https://dashboard.render.com/register"
                }
            return {
                "success": False,
                "error": data.get("detail", "Failed to create mailbox on mail.yukisbox.com")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def check_render_email(token: str) -> dict:
        try:
            r = requests.get(
                f"{YUKI_MAIL_BASE}/api/emails",
                params={"token": token},
                timeout=10
            )
            if r.status_code != 200:
                return {"found": False, "error": f"HTTP {r.status_code}"}

            emails = r.json()
            if not isinstance(emails, list) or not emails:
                return {"found": False, "count": 0}

            pattern = r'(https?://(?:track\.pstmrk\.it/3[a-z]?/dashboard\.render\.com%2Femail-confirm[^\s"\'<>]+|dashboard\.render\.com/email-confirm[^\s"\'<>]+))'

            # Iterate through emails to find the one containing the activation link
            for em in emails:
                msg_id = em.get("id")
                subject = em.get("subject", "")
                
                # Fetch email detail
                detail_res = requests.get(
                    f"{YUKI_MAIL_BASE}/api/email/{msg_id}",
                    params={"token": token},
                    timeout=10
                )
                if detail_res.status_code == 200:
                    detail = detail_res.json()
                    combined_text = (detail.get("textBody") or "") + " " + (detail.get("htmlBody") or "")
                    matches = re.findall(pattern, combined_text)
                    if matches:
                        return {
                            "found": True,
                            "msg_id": msg_id,
                            "subject": subject,
                            "date": em.get("date"),
                            "confirm_url": matches[0]
                        }

            return {
                "found": False,
                "count": len(emails),
                "waiting_for_link": True
            }
        except Exception as e:
            return {"found": False, "error": str(e)}
