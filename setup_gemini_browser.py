"""One-shot loopback form to keep the API key out of chat and command arguments."""
import json
import secrets
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import run_task_bot as bot
import gemini_provider as gemini

nonce = secrets.token_urlsafe(24)
origin = 'http://127.0.0.1:47839'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path != '/' + nonce:
            self.send_error(404)
            return
        body = ('<html><title>Configurazione Gemini locale</title><h1>Salva Gemini sul PC</h1>'
                '<p>Chiave cifrata con Windows DPAPI. Limite stimato: 1 USD/giorno. Nessuna fatturazione attivata.</p>'
                '<form method="post"><label>Chiave API <input name="key" type="password" autocomplete="off"></label>'
                '<button>Salva configurazione locale</button></form></html>').encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != '/' + nonce or self.headers.get('Origin') != origin:
            self.send_error(403)
            return
        size = int(self.headers.get('Content-Length', 0))
        if not 0 < size < 4096:
            self.send_error(400)
            return
        key = parse_qs(self.rfile.read(size).decode()).get('key', [''])[0].strip()
        if not re.fullmatch(r'[A-Za-z0-9_.-]{30,200}', key):
            self.send_error(400, 'Chiave non valida')
            return
        bot.STATE.mkdir(parents=True, exist_ok=True)
        (bot.STATE / 'gemini-key.bin').write_bytes(bot.protect_session(key.encode()))
        settings = {'provider': 'gemini', 'model': gemini.DEFAULT_MODEL, 'daily_usd': 1}
        temporary = bot.STATE / 'ai-provider.tmp'
        temporary.write_text(json.dumps(settings), encoding='utf-8')
        temporary.replace(bot.STATE / 'ai-provider.json')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b'<h1>Configurazione salvata e chiave cifrata sul PC.</h1>')
        threading.Thread(target=self.server.shutdown, daemon=True).start()


if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 47839), Handler)
    server.timeout = 300
    print(origin + '/' + nonce, flush=True)
    timer = threading.Timer(300, server.shutdown)
    timer.daemon = True
    timer.start()
    try:
        server.serve_forever()
    finally:
        timer.cancel()
        server.server_close()
