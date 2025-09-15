import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import requests  # <- NUEVO

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8001))

# Ambiente DGII configurable (por defecto 'certecf').
# Admite: 'testecf', 'certecf' o 'ecf' (producción)
AMBIENTE = os.environ.get("ECF_AMBIENTE", "testecf").strip().lower()
DGII_BASE = "https://ecf.dgii.gov.do"
SEMILLA_URL = f"{DGII_BASE}/{AMBIENTE}/autenticacion/api/autenticacion/semilla"

class RequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def log_message(self, format, *args):
        print("%s - - %s" % (self.address_string(), format % args))

    def do_GET(self):
        route = urlparse(self.path).path
        route = route.replace("%0A", "").strip().rstrip('/') or '/'

        if route == "/semilla":
            try:
                # Llamada real a DGII (GET)
                resp = requests.get(SEMILLA_URL, timeout=30)
                if resp.status_code == 200:
                    # Devolvemos el XML de la semilla como texto
                    self._set_headers(200)
                    self.wfile.write(json.dumps({
                        "status": "ok",
                        "ambiente": AMBIENTE,
                        "semilla_xml": resp.text  # XML que luego firmaremos
                    }).encode("utf-8"))
                else:
                    self._set_headers(resp.status_code)
                    self.wfile.write(json.dumps({
                        "error": "DGII no devolvió 200 en /semilla",
                        "status_code": resp.status_code,
                        "body_preview": resp.text[:500]
                    }).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({
                    "error": "Fallo al llamar /semilla de DGII",
                    "detail": str(e),
                    "url": SEMILLA_URL
                }).encode("utf-8"))
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
            self.wfile.write(json.dumps({
                "status": "ok",
                "msg": "Aquí obtenemos el token (mock, implementaremos real luego)",
                "echo": data
            }).encode("utf-8"))
        elif route == "/enviar":
            self._set_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "msg": "Aquí enviamos el comprobante (mock, implementaremos real luego)",
                "echo": data
            }).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Ruta no encontrada", "route": route}).encode("utf-8"))

def run():
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Servidor corriendo en http://{HOST}:{PORT} (AMBIENTE={AMBIENTE})")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
