import os

from http.server import BaseHTTPRequestHandler, HTTPServer
import json

PORT = int(os.getenv("PORT", 8001))

class SimpleHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def do_GET(self):
        if self.path == "/semilla":
            self._set_headers()
            response = {
                "status": "ok",
                "msg": "Aquí generamos la semilla"
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
        elif self.path == "/debug":
            self._set_headers()
            response = {
                "CERT_B64_exists": bool(os.getenv("CERT_B64")),
                "CERT_PASS_exists": bool(os.getenv("CERT_PASS")),
                "ECF_AMBIENTE": os.getenv("ECF_AMBIENTE")
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self._set_headers(404)
            response = {
                "error": "Ruta no encontrada",
                "route": self.path
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))

    def do_POST(self):
        if self.path == "/token":
            self._set_headers()
            response = {
                "error": "Error procesando token",
                "detail": "CERT_B64 o CERT_PASS no configurados en Railway"
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self._set_headers(404)
            response = {
                "error": "Ruta no encontrada",
                "route": self.path
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))

def run():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"Servidor corriendo en http://0.0.0.0:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
