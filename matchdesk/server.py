"""Single-process local HTTP server with isolated browser sessions."""
import json
import secrets
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from urllib.parse import parse_qs, urlparse
from .engine import Session

WEB = Path(__file__).resolve().parent.parent / 'web'
SESSIONS = {}
LOCK = RLock()
MAX_SESSIONS = 100

class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, mime='application/json', cookie=None):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        if cookie: self.send_header('Set-Cookie', f'matchdesk={cookie}; HttpOnly; SameSite=Strict; Path=/')
        self.end_headers()
        self.wfile.write(raw)

    def session(self):
        jar = cookies.SimpleCookie()
        try: jar.load(self.headers.get('Cookie', ''))
        except cookies.CookieError: pass
        key = jar['matchdesk'].value if 'matchdesk' in jar else ''
        if key not in SESSIONS:
            if len(SESSIONS) >= MAX_SESSIONS: raise ValueError('Session limit reached; restart local server')
            key = secrets.token_urlsafe(24)
            SESSIONS[key] = Session()
        return key, SESSIONS[key]

    def do_GET(self):
        route = urlparse(self.path)
        if route.path == '/api/health': return self.respond(200, {'status':'ok', 'ai_connected':False})
        if route.path == '/': return self.respond(200, (WEB/'index.html').read_bytes(), 'text/html; charset=utf-8')
        if route.path != '/api/state': return self.respond(404, {'error':'Not found'})
        try:
            q = parse_qs(route.query)
            clock = int(q.get('clock',['0'])[0])
            if not 0 <= clock <= 10000: raise ValueError('Invalid clock')
            audience = q.get('audience',['analyst'])[0]
            if audience not in ('analyst','casual'): raise ValueError('Invalid audience')
            with LOCK:
                key, session = self.session()
                self.respond(200, session.snapshot(clock,audience), cookie=key)
        except ValueError as ex: self.respond(400, {'error':str(ex)})

    def do_POST(self):
        if urlparse(self.path).path != '/api/correct': return self.respond(404, {'error':'Not found'})
        # Browser writes must originate from this host; no permissive CORS.
        origin = self.headers.get('Origin')
        if origin and origin not in ('http://'+self.headers.get('Host',''), 'https://'+self.headers.get('Host','')):
            return self.respond(403, {'error':'Origin rejected'})
        try:
            size = int(self.headers.get('Content-Length','0'))
            if not 0 < size <= 4096: raise ValueError('Invalid body size')
            body = json.loads(self.rfile.read(size))
            with LOCK:
                key, session = self.session()
                session.correct_shot(body['event_id'])
                self.respond(200, {'corrected':body['event_id']}, cookie=key)
        except (ValueError, KeyError, TypeError) as ex: self.respond(400, {'error':str(ex)})

def main():
    import os
    host = os.environ.get('HOST','127.0.0.1')
    port = int(os.environ.get('PORT','8000'))
    print(f'The Match Desk: http://{host}:{port}', flush=True)
    ThreadingHTTPServer((host,port), Handler).serve_forever()

if __name__ == '__main__': main()
