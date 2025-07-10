from fastapi import FastAPI
from pydantic import BaseModel
from db import database, comprobantes

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
class Comprobante(BaseModel):
    RNCEmisor: str
    eNCF: str
    FechaEmision: str
    XMLBase64: str

# Ruta raíz para ver si la app está activa
@app.get("/")
def root():
    return {"message": "Servidor activo"}

@app.post("/recibir-comprobante")
async def recibir_comprobante(data: Comprobante):
    # Verificar si ya existe un comprobante con ese eNCF y RNCEmisor
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

    # Insertar nuevo comprobante
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
