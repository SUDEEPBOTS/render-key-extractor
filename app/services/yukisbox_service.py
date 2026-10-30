from datetime import datetime, timezone
import requests

YUKISBOX_UPLOAD_URL = "https://yukisbox.com/upload-text"

class YukisboxService:
    @staticmethod
    def upload_keys(keys_data: list, title: str = None) -> dict:
        if not keys_data:
            return {"success": False, "error": "No keys provided to upload"}

        now_utc = datetime.now(timezone.utc)
        if not title:
            title = f"Render_Keys_Batch_{now_utc.strftime('%Y%m%d_%H%M%S')}"

        lines = [
            f"# Render API Keys - Batch Export ({len(keys_data)} Keys)",
            f"# Generated: {now_utc.isoformat()}",
            f"# Yukisbox Batch Title: {title}",
            "=" * 60,
            ""
        ]

        for idx, k in enumerate(keys_data, 1):
            lines.append(f"### KEY #{idx}")
            lines.append(f"RENDER_API_KEY_{idx}={k.get('api_key')}")
            lines.append(f"RENDER_EMAIL_{idx}={k.get('email') or 'N/A'}")
            if k.get('password'):
                lines.append(f"RENDER_PASSWORD_{idx}={k.get('password')}")
            lines.append(f"RENDER_WORKSPACE_{idx}={k.get('workspace') or 'N/A'}")
            lines.append(f"RENDER_OWNER_ID_{idx}={k.get('owner_id') or 'N/A'}")
            created = k.get("timestamp") or k.get("created_at") or now_utc.isoformat()
            lines.append(f"CREATED_AT_{idx}={created}")
            lines.append("")

        text_content = "\n".join(lines)

        try:
            r = requests.post(
                YUKISBOX_UPLOAD_URL,
                data={
                    "text": text_content,
                    "title": title,
                    "filename": f"{title}.txt"
                },
                timeout=15
            )
            data = r.json()
            if r.status_code == 200 and data.get("success"):
                return {
                    "success": True,
                    "uid": data.get("uid"),
                    "url": data.get("url"),
                    "raw_url": data.get("raw_url"),
                    "filename": data.get("filename"),
                    "total_keys": len(keys_data)
                }
            return {
                "success": False,
                "error": data.get("message", "Upload failed")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
