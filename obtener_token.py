from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import httpx

router = APIRouter()

@router.post("/auth/token", summary="Obtener token desde archivo firmado XML")
async def obtener_token_desde_archivo(file: UploadFile = File(...)):
    try:
        # Leer contenido del archivo firmado
        contenido_xml = await file.read()

        # Preparar multipart/form-data
        files = {
            'xml': (file.filename, contenido_xml, 'text/xml')
        }

        # URL oficial DGII TESTECF
        url = "https://ecf.dgii.gov.do/testecf/autenticacion/api/autenticacion/validarsemilla"

        # Enviar solicitud a DGII
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, files=files)
            response.raise_for_status()

            # Devolver respuesta JSON
            return JSONResponse(content=response.json())

    except httpx.HTTPStatusError as http_err:
        raise HTTPException(status_code=response.status_code, detail=f"Error DGII: {http_err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")
