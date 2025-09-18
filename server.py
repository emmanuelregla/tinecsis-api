import os
import json
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from lxml import etree
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization


PORT = int(os.getenv("PORT", 8000))

# Cargar certificado desde variable CERT_B64
def load_cert():
    cert_b64 = os.getenv("CERT_B64")
    cert_pass = os.getenv("CERT_PASS")
    if not cert_b64 or not cert_pass:
        raise ValueError("CERT_B64 o CERT_PASS no configurados")

    cert_bytes = base64.b64decode(cert_b64)
    private_key, cert, _ = pkcs12.load_key_and_certificates(
        cert_bytes, cert_pass.encode()
    )

    # Convertir cert a PEM
    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
    return private_key, cert_pem.decode("utf-8")


class SimpleHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def do_GET(self):
        if self.path == "/semilla":

            fecha = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            valor = base64.b64encode(os.urandom(48)).decode("utf-8")

            semilla_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<SemillaModel xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <valor>{valor}</valor>
  <fecha>{fecha}</fecha>
</SemillaModel>"""

            self._set_headers()
            self.wfile.write(json.dumps({"semilla_xml": semilla_xml}).encode("utf-8"))

        else:
            self._set_headers(404)
            self.wfile.write(
                json.dumps({"error": "Ruta no encontrada", "route": self.path}).encode(
                    "utf-8"
                )
            )

    def do_POST(self):
        if self.path == "/token":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data)
                semilla_xml = payload.get("semilla_xml")

                if not semilla_xml:
                    raise ValueError("Falta semilla_xml en el body")


                private_key, cert_pem = load_cert()

                parser = etree.XMLParser(remove_blank_text=True)
                xml_doc = etree.fromstring(semilla_xml.encode("utf-8"), parser=parser)

                signer = XMLSigner(
                    method=methods.enveloped,
                    signature_algorithm="rsa-sha256",
                    digest_algorithm="sha256",
                    c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
                )

                signed_root = signer.sign(xml_doc, key=private_key, cert=cert_pem)

                # 👉 Forzar namespace por defecto y quitar prefijo ds:
                for elem in signed_root.xpath("//*[namespace-uri()='http://www.w3.org/2000/09/xmldsig#']"):
                    qname = etree.QName(elem)
                    elem.tag = f"{{http://www.w3.org/2000/09/xmldsig#}}{qname.localname}"


                etree.cleanup_namespaces(signed_root)

                # Forzar que la etiqueta raíz de la firma sea <Signature xmlns="...">
                for sig in signed_root.xpath("//ds:Signature", namespaces={"ds": "http://www.w3.org/2000/09/xmldsig#"}):
                    sig.tag = "{http://www.w3.org/2000/09/xmldsig#}Signature"



                signed_xml = etree.tostring(
                    signed_root, pretty_print=True, xml_declaration=True, encoding="utf-8"
                ).decode("utf-8")


                self._set_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "status": "ok",
                            "signed_xml": signed_xml
                        }
                    ).encode("utf-8")
                )

            except Exception as e:
                self._set_headers(500)
                self.wfile.write(
                    json.dumps(
                        {"error": "Error procesando token", "detail": str(e)}
                    ).encode("utf-8")
                )
        else:
            self._set_headers(404)
            self.wfile.write(
                json.dumps({"error": "Ruta no encontrada", "route": self.path}).encode(
                    "utf-8"
                )
            )


def run():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"Servidor corriendo en http://0.0.0.0:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()

