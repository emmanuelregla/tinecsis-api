import os
import json
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import requests
from lxml import etree
from signxml import XMLSigner, methods



PORT = int(os.getenv("PORT", 8000))

AMBIENTE = os.getenv("ECF_AMBIENTE", "testecf").strip().lower()
DGII_BASE = "https://ecf.dgii.gov.do"
SEMILLA_URL = f"{DGII_BASE}/{AMBIENTE}/autenticacion/api/autenticacion/semilla"
VALIDAR_URL = f"{DGII_BASE}/{AMBIENTE}/autenticacion/api/autenticacion/validarsemilla"
XMLSIG_NS = "http://www.w3.org/2000/09/xmldsig#"

def load_pem_key_cert():
    key_b64 = os.getenv("PRIVATE_KEY_B64")
    cert_b64 = os.getenv("CERT_B64")
    if not key_b64 or not cert_b64:
        raise ValueError("Faltan PRIVATE_KEY_B64 o CERT_B64")

    # Decodificar a string plano UTF-8
    key_pem = base64.b64decode(key_b64).decode("utf-8").strip()
    cert_pem = base64.b64decode(cert_b64).decode("utf-8").strip()
    return key_pem, cert_pem

def strip_ds_prefix_to_default(sig_root):
    sig_elems = sig_root.xpath("//*[local-name()='Signature' and namespace-uri()=$ns]", ns={"ns": XMLSIG_NS})
    if not sig_elems:
        return sig_root
    sig = sig_elems[0]

    # Crear Signature sin prefijo (namespace por defecto)
    new_sig = etree.Element(f"{{{XMLSIG_NS}}}Signature", nsmap={None: XMLSIG_NS})
    for child in list(sig):
        new_sig.append(child)

    parent = sig.getparent()
    parent.replace(sig, new_sig)

    for elem in new_sig.xpath(".//*[namespace-uri()=$ns]", ns={"ns": XMLSIG_NS}):
        qn = etree.QName(elem)
        elem.tag = f"{{{XMLSIG_NS}}}{qn.localname}"

    etree.cleanup_namespaces(sig_root)
    return sig_root

class Handler(BaseHTTPRequestHandler):
    def _json(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_GET(self):
        route = urlparse(self.path).path.rstrip("/") or "/"
        if route == "/semilla":
            try:
                r = requests.get(SEMILLA_URL, timeout=30)
                if r.status_code == 200:
                    self._json(200)
                    self.wfile.write(json.dumps({
                        "status": "ok",
                        "ambiente": AMBIENTE,
                        "semilla_xml": r.text
                    }).encode("utf-8"))
                else:
                    self._json(r.status_code)
                    self.wfile.write(json.dumps({
                        "error": "DGII no devolvió 200 en /semilla",
                        "status_code": r.status_code,
                        "body_preview": r.text[:500]
                    }).encode("utf-8"))
            except Exception as e:
                self._json(500)
                self.wfile.write(json.dumps({
                    "error": "Fallo al llamar /semilla",
                    "detail": str(e),
                    "url": SEMILLA_URL
                }).encode("utf-8"))
        else:
            self._json(404)
            self.wfile.write(json.dumps({"error":"Ruta no encontrada","route":route}).encode("utf-8"))

    def do_POST(self):
        route = urlparse(self.path).path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length>0 else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        if route == "/token":
            try:
                semilla_xml = data.get("semilla_xml")
                if not semilla_xml:
                    raise ValueError("Debe enviar semilla_xml (XML de DGII)")

                parser = etree.XMLParser(remove_blank_text=True)
                xml_doc = etree.fromstring(semilla_xml.encode("utf-8"), parser=parser)

                key_pem, cert_pem = load_pem_key_cert()
                signer = XMLSigner(
                    method=methods.enveloped,
                    signature_algorithm="rsa-sha256",
                    digest_algorithm="sha256",
                    c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
                )

                signed_root = signer.sign(xml_doc, key=key_pem, cert=cert_pem)
                signed_root = strip_ds_prefix_to_default(signed_root)

                firmado_xml = etree.tostring(
                    signed_root, pretty_print=False, encoding="utf-8", xml_declaration=True
                ).decode("utf-8")

                headers = {"Content-Type": "application/xml"}
                resp = requests.post(VALIDAR_URL, data=firmado_xml.encode("utf-8"), headers=headers, timeout=30)

                if resp.status_code == 200:
                    self._json(200)
                    self.wfile.write(json.dumps({
                        "status": "ok",
                        "token_response": resp.text
                    }).encode("utf-8"))
                else:
                    self._json(resp.status_code)
                    self.wfile.write(json.dumps({
                        "error": "DGII no devolvió 200 en /validarsemilla",
                        "status_code": resp.status_code,
                        "body_preview": resp.text[:500],
                        "firmado_preview": firmado_xml[:300] + ("..." if len(firmado_xml)>300 else "")
                    }).encode("utf-8"))

            except Exception as e:
                self._json(500)
                self.wfile.write(json.dumps({
                    "error": "Error procesando token",
                    "detail": str(e)
                }).encode("utf-8"))
        else:
            self._json(404)
            self.wfile.write(json.dumps({"error":"Ruta no encontrada","route":route}).encode("utf-8"))

def run():
    httpd = HTTPServer(("", PORT), Handler)
    print(f"Servidor corriendo en http://0.0.0.0:{PORT} AMBIENTE={AMBIENTE}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
