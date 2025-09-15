import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8001))  # Railway usa PORT dinámico, local 8001

class RequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def log_message(self, format, *args):
        print("%s - - %s" % (self.address_string(), format % args))

    def do_GET(self):
        # Limpia %0A, espacios y slash final
        route = urlparse(self.path).path
        route = route.replace("%0A", "").strip().rstrip('/') or '/'
        if route == "/semilla":
            self._set_headers()
            response = {"status": "ok", "msg": "Aquí generamos la semilla"}
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Ruta no encontrada", "route": route}).encode("utf-8"))

    def do_POST(self):
        route = urlparse(self.path).path
        route = route.replace("%0A", "").strip().rstrip('/') or '/'
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        if route == "/token":
            self._set_headers()
            response = {"status": "ok", "msg": "Aquí obtenemos el token", "echo": data}
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif route == "/enviar":
            self._set_headers()
            response = {"status": "ok", "msg": "Aquí enviamos el comprobante", "echo": data}
            self.wfile.write(json.dumps(response).encode("utf-8"))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Ruta no encontrada", "route": route}).encode("utf-8"))

def run():
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Servidor corriendo en http://{HOST}:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()