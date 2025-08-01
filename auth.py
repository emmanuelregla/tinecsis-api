from fastapi import APIRouter, UploadFile, File, HTTPException
import httpx
from pathlib import Path

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/token/manual", summary="Validar semilla firmada manualmente y obtener token")
async def obtener_token_manual(xml: UploadFile = File(...)):
    # Guardar temporalmente el archivo XML recibido
    archivo_path = Path("semilla_subida.xml")
    try:
        contenido = await xml.read()
        archivo_path.write_bytes(contenido)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar archivo: {e}")

    # Preparar solicitud a DGII
    url = "https://ecf.dgii.gov.do/Testecf/Autenticacion/api/Autenticacion/ValidarSemilla"
    files = {
        "xml": ("semilla_firmada.xml", archivo_path.open("rb"), "text/xml")
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, files=files)
            response.raise_for_status()
            token_response = response.json()

            # Guardar token localmente
            with open("token.txt", "w") as f:
                f.write(token_response["token"])

            return {
                "mensaje": "✅ Token recibido correctamente desde la DGII",
                "token": token_response["token"],
                "expira": token_response.get("expira"),
                "expedido": token_response.get("expedido")
            }

    except httpx.HTTPStatusError as err:
        contenido = err.response.text
        raise HTTPException(status_code=400, detail=f"❌ Error DGII: {contenido}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error inesperado: {e}")

