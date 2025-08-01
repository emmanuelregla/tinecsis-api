
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from db import database, comprobantes
import base64
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
import httpx

from auth import router as auth_router


app = FastAPI()

# 🔐 Seguridad: API Key para autenticación simple
API_KEY = "miclave123456"
api_key_header = APIKeyHeader(name="X-API-Key")

# 🧾 Modelo de entrada para comprobantes
class Comprobante(BaseModel):
    RNCEmisor: str
    eNCF: str
    FechaEmision: str
    XMLBase64: str

# 🚀 Conexión inicial con base de datos
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# 📥 POST: Recibir nuevo comprobante
@app.post("/recibir-comprobante")
async def recibir_comprobante(
    data: Comprobante,
    x_api_key: str = Security(api_key_header)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")

    # ✅ Validar si ya existe
    query = comprobantes.select().where(
        (comprobantes.c.eNCF == data.eNCF) &
        (comprobantes.c.RNCEmisor == data.RNCEmisor)
    )
    comprobante_existente = await database.fetch_one(query)
    if comprobante_existente:
        return {
            "mensaje": "❌ Este comprobante ya ha sido registrado.",
            "eNCF": data.eNCF
        }

    # 🔍 Validar y parsear XML
    try:
        decoded_xml = base64.b64decode(data.XMLBase64).decode("utf-8")
        root = ET.fromstring(decoded_xml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"XML inválido: {str(e)}")

    # 🧪 Extraer datos clave del XML y validar con JSON
    try:
        eNCF_xml = root.findtext(".//IdDoc/eNCF")
        rnc_emisor_xml = root.findtext(".//Emisor/RNCEmisor")
        fecha_emision_xml = root.findtext(".//Emisor/FechaEmision")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer XML: {str(e)}")

    if eNCF_xml != data.eNCF:
        raise HTTPException(status_code=400, detail=f"eNCF en XML ({eNCF_xml}) no coincide con JSON ({data.eNCF})")

    if rnc_emisor_xml != data.RNCEmisor:
        raise HTTPException(status_code=400, detail=f"RNCEmisor en XML ({rnc_emisor_xml}) no coincide con JSON ({data.RNCEmisor})")

    try:
        fecha_json = datetime.strptime(data.FechaEmision, "%Y-%m-%d").date()
        fecha_xml = datetime.strptime(fecha_emision_xml, "%d-%m-%Y").date()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al interpretar FechaEmision: {str(e)}")

    if fecha_json != fecha_xml:
        raise HTTPException(
            status_code=400,
            detail=f"FechaEmision en XML ({fecha_emision_xml}) no coincide con JSON ({data.FechaEmision})"
        )

    # 💾 Insertar en base de datos
    query = comprobantes.insert().values(
        RNCEmisor=data.RNCEmisor,
        eNCF=data.eNCF,
        FechaEmision=data.FechaEmision,
        XMLBase64=data.XMLBase64
    )
    last_id = await database.execute(query)

    return {
        "mensaje": "✅ Comprobante recibido correctamente",
        "eNCF": data.eNCF,
        "id": last_id
    }

# 🔍 GET: Consultar todos los comprobantes
@app.get("/comprobantes")
async def listar_comprobantes():
    query = comprobantes.select()
    return await database.fetch_all(query)

# 📤 PREPARAR: JSON simulado para enviar a la DGII
@app.post("/enviar-a-dgii/{encf}")
async def preparar_envio_dgii(encf: str):
    query = comprobantes.select().where(comprobantes.c.eNCF == encf)
    comprobante = await database.fetch_one(query)

    if not comprobante:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    try:
        xml_bytes = base64.b64decode(comprobante["XMLBase64"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al decodificar XML base64: {str(e)}")

    hash_bytes = hashlib.sha256(xml_bytes).digest()
    hash_base64 = base64.b64encode(hash_bytes).decode("utf-8")

    payload = {
        "RNCEmisor": comprobante["RNCEmisor"],
        "eNCF": comprobante["eNCF"],
        "FechaEmision": comprobante["FechaEmision"],
        "XMLFirmado": comprobante["XMLBase64"],  # Aún no firmado realmente
        "HashXML": hash_base64
    }

    return payload

# 🚀 SIMULACIÓN: Enviar a DGII (simulada con token ficticio)
@app.post("/dgii/enviar/{encf}")
async def enviar_a_dgii(encf: str):
    DGII_URL_SIMULADA = "https://httpbin.org/post"  # URL de prueba funcional
    FAKE_TOKEN = "eyJhbGciOiFakeTokenParaSimulacion1234567890"

    query = comprobantes.select().where(comprobantes.c.eNCF == encf)
    comprobante = await database.fetch_one(query)

    if not comprobante:
        raise HTTPException(status_code=404, detail=f"Comprobante {encf} no encontrado")

    try:
        xml_bytes = base64.b64decode(comprobante["XMLBase64"])
        hash_bytes = hashlib.sha256(xml_bytes).digest()
        hash_base64 = base64.b64encode(hash_bytes).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al preparar XML: {str(e)}")

    payload = {
        "RNCEmisor": comprobante["RNCEmisor"],
        "eNCF": comprobante["eNCF"],
        "FechaEmision": comprobante["FechaEmision"],
        "XMLFirmado": comprobante["XMLBase64"],
        "HashXML": hash_base64
    }

    headers = {
        "Authorization": f"Bearer {FAKE_TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(DGII_URL_SIMULADA, json=payload, headers=headers)
            return {
                "status_code": response.status_code,
                "dgii_response": response.json()
            }
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Error al conectar con la DGII simulada: {str(e)}")


# Endpoint para solicitar semilla oficial de la DGII
from fastapi.responses import Response

@app.get("/dgii/semilla", summary="Solicitar semilla a DGII (testecf)")
async def solicitar_semilla():
    url = "https://ecf.dgii.gov.do/testecf/Autenticacion/Solicitar"
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            return Response(content=response.text, media_type="application/xml")
    except httpx.HTTPStatusError as http_err:
        raise HTTPException(status_code=response.status_code, detail=f"Error HTTP: {http_err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al solicitar semilla: {str(e)}")

app.include_router(auth_router)
#comentario para push
