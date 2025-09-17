import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import requests
import base64
import re
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8001))

# Ambiente DGII configurable (default testecf)
AMBIENTE = os.environ.get("ECF_AMBIENTE", "testecf").strip().lower()
DGII_BASE = "https://ecf.dgii.gov.do"
SEMILLA_URL = f"{DGII_BASE}/{AMBIENTE}/autenticacion/api/autenticacion/semilla"
VALIDAR_URL = f"{DGII_BASE}/{AMBIENTE}/autenticacion/api/autenticacion/validarsemilla"

class RequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def log_message(self, format, *args):
        print("%s - - %s" % (self.address_string(), format % args))

    def do_GET(self):
        route = urlparse(self.path).path.replace("%0A", "").strip().rstrip('/') or '/'

        if route == "/semilla":
            try:
                resp = requests.get(SEMILLA_URL, timeout=30)
                if resp.status_code == 200:
                    self._set_headers(200)
                    self.wfile.write(json.dumps({
                        "status": "ok",
                        "ambiente": AMBIENTE,
                        "semilla_xml": resp.text
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
        route = urlparse(self.path).path.replace("%0A", "").strip().rstrip('/') or '/'
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        if route == "/token":
            try:
                semilla_xml = data.get("semilla_xml")
                if not semilla_xml:
                    raise Exception("Debe enviar semilla_xml")

                # Extraer valor de <valor>...</valor> dentro de <SemillaModel>
                match = re.search(r"<valor>(.+)</valor>", semilla_xml)
                if not match:
                    raise Exception("No se encontró <valor> en XML de SemillaModel")
                semilla_valor = match.group(1).encode("utf-8")

                # Decodificar certificado desde variable de entorno
                cert_b64 = os.environ.get("CERT_B64")
                cert_pass = os.environ.get("CERT_PASS", "").encode("utf-8")
                if not cert_b64 or not cert_pass:
                    raise Exception("CERT_B64 o CERT_PASS no configurados en Railway")

                cert_bytes = base64.b64decode(cert_b64)
                private_key, cert, add_certs = pkcs12.load_key_and_certificates(
                    cert_bytes, cert_pass, backend=default_backend()
                )

                # Firmar la semilla con SHA256 + PKCS#1 v1.5
                signature = private_key.sign(
                    semilla_valor,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                signature_b64 = base64.b64encode(signature).decode("utf-8")

                # XML firmado para DGII
                firmado_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<ValidarSemilla>
  <Semilla>{semilla_valor.decode("utf-8")}</Semilla>
  <Firma>{signature_b64}</Firma>
</ValidarSemilla>"""

                # Enviar a DGII /validarsemilla
                headers = {"Content-Type": "application/xml"}
                resp = requests.post(VALIDAR_URL, data=firmado_xml, headers=headers, timeout=30)

                if resp.status_code == 200:
                    self._set_headers()
                    self.wfile.write(json.dumps({
                        "status": "ok",
                        "token_response": resp.text
                    }).encode("utf-8"))
                else:
                    self._set_headers(resp.status_code)
                    self.wfile.write(json.dumps({
                        "error": "DGII no devolvió 200 en /validarsemilla",
                        "status_code": resp.status_code,
                        "body_preview": resp.text[:500]
                    }).encode("utf-8"))

            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({
                    "error": "Error procesando token",
                    "detail": str(e)
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
    