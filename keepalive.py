import json
import os
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import database as db

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")


class _PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/stats":
            self._handle_stats(parsed)
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def _handle_stats(self, parsed):
        token = parse_qs(parsed.query).get("token", [""])[0]
        if not ADMIN_TOKEN or token != ADMIN_TOKEN:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        rows = db.get_events_since(today_start)
        events = [
            {
                "chat_id": chat_id,
                "name": name,
                "sent_at": sent_at,
                "message_type": message_type,
                "text": text,
                "accepted": accepted_at is not None,
                "accepted_at": accepted_at,
            }
            for chat_id, name, sent_at, message_type, text, accepted_at in rows
        ]
        payload = json.dumps(
            {"total_subscribers": db.count_subscribers(), "today_events": events},
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


def start_keepalive_server():
    """Крошечный веб-сервер: держит Render free tier от засыпания и отдаёт /stats для аналитики."""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), _PingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
