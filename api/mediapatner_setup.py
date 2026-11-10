"""
Vercel Webhook Setup & Info Endpoint for MEDIAPATNER BOT.
Allows 1-click webhook registration with Telegram Bot API.
"""

from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mediapatner.config import get_settings


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            settings = get_settings()
            token = settings.get_token_plain()

            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            action = query_params.get("action", ["setup"])[0]

            host = self.headers.get("Host") or "cheneoasv.vercel.app"
            webhook_url = f"https://{host}/api/mediapatner-webhook"

            if action == "info":
                tg_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
                with urllib.request.urlopen(tg_url, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                response_data = {"action": "info", "telegram": data}

            elif action == "delete":
                tg_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
                with urllib.request.urlopen(tg_url, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                response_data = {"action": "delete", "telegram": data}

            else:
                # Default: setup webhook
                encoded_url = urllib.parse.quote(webhook_url, safe="")
                tg_url = (
                    f"https://api.telegram.org/bot{token}/setWebhook"
                    f"?url={encoded_url}&allowed_updates=message,callback_query"
                )
                with urllib.request.urlopen(tg_url, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                response_data = {
                    "success": True,
                    "webhook_url": webhook_url,
                    "telegram": data,
                    "message": f"Webhook MEDIAPATNER BOT berhasil disetel ke: {webhook_url}",
                }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, indent=2).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
