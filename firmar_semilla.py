from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64
import xml.etree.ElementTree as ET

# === Configuración ===
RUTA_CERTIFICADO = "13050716_identity.p12"
PASSWORD_CERTIFICADO = b"E162031"  # 👈 Reemplaza por tu clave real
RUTA_SEMILLA = "semilla.xml"
RUTA_SALIDA = "firmado.xml"

# === Cargar certificado ===
with open(RUTA_CERTIFICADO, "rb") as f:
    p12_data = f.read()

private_key, cert, _ = pkcs12.load_key_and_certificates(
    p12_data, PASSWORD_CERTIFICADO, backend=default_backend()
)

# === Leer la semilla ===
tree = ET.parse(RUTA_SEMILLA)
root = tree.getroot()
semilla_text = root.text.strip().encode("utf-8")

# === Firmar la semilla ===
firma = private_key.sign(
    semilla_text,
    padding.PKCS1v15(),
    hashes.SHA1()
)
firma_b64 = base64.b64encode(firma).decode("utf-8")

# === Construir XML firmado ===
signed_root = ET.Element("Semilla")
signed_root.text = root.text.strip()
firma_element = ET.SubElement(signed_root, "Firma")
firma_element.text = firma_b64

# === Guardar firmado.xml ===
tree = ET.ElementTree(signed_root)
tree.write(RUTA_SALIDA, encoding="utf-8", xml_declaration=True)

print("✅ Semilla firmada correctamente en:", RUTA_SALIDA)
