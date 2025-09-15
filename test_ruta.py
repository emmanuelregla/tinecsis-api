from pathlib import Path

cert_path = Path(r"/Users/emmanuelregla/Library/Mobile Documents/com~apple~CloudDocs/Facturacion Electronica/Certificado2/Certificado Digital/13050716_identity.p12")

if cert_path.exists():
    print("✅ Archivo encontrado")
else:
    print("❌ Archivo no encontrado")