from fastapi import FastAPI
from pydantic import BaseModel
from db import database, comprobantes

import os
from fastapi import Header,HTTPException
from fastapi.security.api_key import APIKeyHeader
from fastapi import Security

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

API_KEY=os.getenv("tinecsis_api_key")

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

    # Verificación de duplicado (sin cambios)
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
