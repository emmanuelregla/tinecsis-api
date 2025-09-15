import base64
import subprocess
import xml.etree.ElementTree as ET
import httpx
from pathlib import Path

# 📁 Rutas a los archivos PEM generados previamente desde tu .p12
cert_path = Path("cert.pem")
key_path = Path("key.pem")

# Paso 1: Solicitar semilla desde DGII (REST)
def solicitar_semilla_desde_dgii():
    url = "https://ecf.dgii.gov.do/Testecf/Autenticacion/api/Autenticacion/Semilla"
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        xml_data = response.text
        root = ET.fromstring(xml_data)
        valor = root.findtext(".//valor")
        print("\n✅ Semilla obtenida correctamente:")
        print(valor)
        return valor
    except Exception as e:
        print(f"\n❌ Error al obtener la semilla: {e}")
        return None

# Paso 2: Firmar la semilla usando OpenSSL para generar PKCS#7
def firmar_semilla_pkcs7_openssl(semilla: str, cert_path: Path, key_path: Path) -> str:
    try:
        input_file = "semilla.txt"
        output_file = "semilla_firmada.p7s"

        with open(input_file, "w") as f:
            f.write(semilla)

        subprocess.run([
            "openssl", "smime", "-sign",
            "-in", input_file,
            "-signer", str(cert_path),
            "-inkey", str(key_path),
            "-outform", "DER",
            "-binary",
            "-nodetach", "-noattr",
            "-out", output_file
        ], check=True)

        with open(output_file, "rb") as f:
            firmado_der = f.read()
            firmado_b64 = base64.b64encode(firmado_der).decode("utf-8")

        print("\n✅ Semilla firmada correctamente (PKCS#7)")
        return firmado_b64

    except Exception as e:
        print(f"\n❌ Error al firmar la semilla con OpenSSL: {e}")
        return None

# Paso 3: Guardar la firma en un XML y enviarla como archivo (multipart/form-data)
def obtener_token_desde_dgii(semilla_firmada_b64: str):
    try:
        xml_path = Path("semilla_firmada.xml")
        xml_path.write_text(
    f"""<ValidarSemillaRequest xmlns="https://DGII.Gob.Do/WSAutenticacion">
  <valor>{semilla_firmada_b64}</valor>
</ValidarSemillaRequest>""",
    encoding="utf-8"
)

        url = "https://ecf.dgii.gov.do/Testecf/Autenticacion/api/Autenticacion/ValidarSemilla"
        files = {
            "xml": ("semilla_firmada.xml", xml_path.open("rb"), "text/xml")
        }

        print("\n📤 Enviando archivo firmado a DGII...")
        response = httpx.post(url, files=files, timeout=30)
        response.raise_for_status()
        data = response.json()
        print("\n✅ Token recibido de DGII:")
        print(data)
        return data

    except httpx.HTTPStatusError as http_err:
        print(f"\n❌ Error HTTP al obtener token: {http_err}")
        print(f"🧾 Respuesta DGII: {http_err.response.text}")
    except Exception as e:
        print(f"\n❌ Error al obtener token: {e}")

# Ejecutar flujo completo
if __name__ == "__main__":
    semilla = solicitar_semilla_desde_dgii()
    if not semilla:
        exit(1)

    semilla_firmada = firmar_semilla_pkcs7_openssl(semilla, cert_path, key_path)
    if not semilla_firmada:
        exit(1)

    obtener_token_desde_dgii(semilla_firmada)

    