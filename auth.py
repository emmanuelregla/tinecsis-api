from fastapi import APIRouter, UploadFile, File, HTTPException
import tempfile
import requests

router = APIRouter()

@router.post("/auth/token/local", summary="Subir firmado.xml y obtener token con requests")
async def obtener_token_local(file: UploadFile = File(...)):
    # Validar extensión
    if not file.filename.endswith(".xml"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .xml")

    # Guardar archivo temporal
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
            contenido = await file.read()
            tmp.write(contenido)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo temporal: {str(e)}")

    # Enviar archivo con requests
    try:
        with open(tmp_path, "rb") as f:
            files = {"file": (file.filename, f, "application/xml")}
            response = requests.post(
                "https://ecf.dgii.gov.do/testecf/Autenticacion/token",
                files=files,
                timeout=10,
                verify=False  # ⚠️ Solo en testecf
            )
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error al conectar: {str(e)}")

    # Verificar respuesta
    if response.status_code == 200:
        return {
            "mensaje": "✅ Token obtenido correctamente",
            "token": response.text
        }
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Error al obtener token: {response.text}"
        )
