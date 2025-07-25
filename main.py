from fastapi import FastAPI
from pydantic import BaseModel
from db import database, comprobantes

import os
from fastapi import Header,HTTPException
from fastapi.security.api_key import APIKeyHeader
from fastapi import Security

import base64
import xml.etree.ElementTree as ET

import xmlschema
import io

import xml.etree.ElementTree as ET
import base64

import hashlib
from fastapi import Path


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

API_KEY=os.getenv("API_KEY")
print(f"🔑 API_KEY cargada: {API_KEY}")


app = FastAPI()

# Conexión a la base de datos al iniciar
@app.on_event("startup")
async def startup():
    await database.connect()

# Desconexión al cerrar la aplicación
@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Modelo de entrada
from pydantic import BaseModel, Field, validator
import re
from datetime import datetime

class Comprobante(BaseModel):
    RNCEmisor: str = Field(..., min_length=9, max_length=11)
    eNCF: str = Field(..., min_length=13, max_length=13)
    FechaEmision: str
    XMLBase64: str = Field(..., min_length=1)

    @validator("RNCEmisor")
    def validar_rnc(cls, v):
        if not v.isdigit():
            raise ValueError("RNCEmisor debe contener solo números")
        if len(v) not in [9, 11]:
            raise ValueError("RNCEmisor debe tener 9 o 11 dígitos")
        return v

    @validator("eNCF")
    def validar_encf(cls, v):
        if not re.match(r"^E\d{12}$", v):
            raise ValueError("eNCF debe comenzar con 'E' seguido de 12 dígitos")
        return v

    @validator("FechaEmision")
    def validar_fecha(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("FechaEmision debe estar en formato YYYY-MM-DD")
        return v

# Ruta raíz para ver si la app está activa
@app.get("/")
def root():
    return {"message": "Servidor activo"}

# Insertar Comprobante envio por POST
@app.post("/recibir-comprobante")
async def recibir_comprobante(
    data: Comprobante,
    x_api_key: str = Security(api_key_header)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")

    # 🔍 Decodificar el XML base64
    try:
        decoded_xml = base64.b64decode(data.XMLBase64).decode("utf-8")
        root = ET.fromstring(decoded_xml)  # valida que esté bien formado
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"XML inválido: {str(e)}")

    from datetime import datetime

    # Extraer valores del XML
    try:
        eNCF_xml = root.findtext(".//IdDoc/eNCF")
        rnc_emisor_xml = root.findtext(".//Emisor/RNCEmisor")
        fecha_emision_xml = root.findtext(".//Emisor/FechaEmision")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer XML: {str(e)}")

    # Validar consistencia con el JSON recibido
    if eNCF_xml != data.eNCF:
        raise HTTPException(status_code=400, detail=f"eNCF en XML ({eNCF_xml}) no coincide con JSON ({data.eNCF})")

    if rnc_emisor_xml != data.RNCEmisor:
        raise HTTPException(status_code=400, detail=f"RNCEmisor en XML ({rnc_emisor_xml}) no coincide con JSON ({data.RNCEmisor})")

    # Validar FechaEmision comparando formatos
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
        
    # Validar contra el esquema XSD oficial de la DGII
    # try:
    #     schema = xmlschema.XMLSchema("schemas/comprobante_31.xsd")
    #     schema.validate(io.StringIO(decoded_xml))  # lanza excepción si el XML no cumple
    # except xmlschema.XMLSchemaException as e:
    #     raise HTTPException(status_code=400, detail=f"XML no válido según XSD: {str(e)}")


    # 🔁 Verificar duplicado
    query = comprobantes.select().where(
        (comprobantes.c.eNCF == data.eNCF) &
        (comprobantes.c.RNCEmisor == data.RNCEmisor)
    )
    existente = await database.fetch_one(query)
    if existente:
        return {
            "mensaje": "❌ Este comprobante ya ha sido registrado.",
            "eNCF": data.eNCF
        }

    # Guardar comprobante
    query = comprobantes.insert().values(
        RNCEmisor=data.RNCEmisor,
        eNCF=data.eNCF,
        FechaEmision=data.FechaEmision,
        XMLBase64=data.XMLBase64
    )
    last_record_id = await database.execute(query)

    return {
        "mensaje": "✅ Comprobante recibido correctamente",
        "id": last_record_id,
        "eNCF": data.eNCF
    }

from typing import List, Optional
from fastapi import Query

@app.get("/comprobantes", response_model=List[Comprobante])
async def listar_comprobantes(
    RNCEmisor: Optional[str] = Query(None),
    eNCF: Optional[str] = Query(None),
    FechaEmision: Optional[str] = Query(None)
):
    query = comprobantes.select()
    
    # Aplicar filtros si se reciben
    if RNCEmisor:
        query = query.where(comprobantes.c.RNCEmisor == RNCEmisor)
    if eNCF:
        query = query.where(comprobantes.c.eNCF == eNCF)
    if FechaEmision:
        query = query.where(comprobantes.c.FechaEmision == FechaEmision)

    resultados = await database.fetch_all(query)
    return resultados

# CON EL SIGUIENTE CODIGO SIMULA EL ENVIO AL COMPROBANTE A LA DGII

@app.post("/enviar-a-dgii/{encf}")
async def enviar_a_dgii(encf: str):
    # Buscar comprobante en la base de datos
    query = comprobantes.select().where(comprobantes.c.eNCF == encf)
    comprobante = await database.fetch_one(query)

    if not comprobante:
        raise HTTPException(status_code=404, detail=f"Comprobante {encf} no encontrado")

    # Decodificar XML original desde base64
    try:
        xml_bytes = base64.b64decode(comprobante["XMLBase64"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al decodificar XML base64: {str(e)}")

    # Calcular hash SHA256 en base64
    sha256_hash = hashlib.sha256(xml_bytes).digest()
    hash_base64 = base64.b64encode(sha256_hash).decode("utf-8")

    # Preparar estructura para envío a DGII (simulada por ahora)
    envio_dgii = {
        "RNCEmisor": comprobante["RNCEmisor"],
        "eNCF": comprobante["eNCF"],
        "FechaEmision": comprobante["FechaEmision"],
        "XMLFirmado": comprobante["XMLBase64"],  # asumimos que aún no está firmado
        "HashXML": hash_base64
    }

    return envio_dgii

# comentario temporal para activar deploy
# comentario temporal para activar deploy2

