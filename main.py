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

# Endpoint para recibir e insertar comprobantes
@app.post("/recibir-comprobante")
async def recibir_comprobante(data: Comprobante):
    query = comprobantes.insert().values(
        RNCEmisor=data.RNCEmisor,
        eNCF=data.eNCF,
        FechaEmision=data.FechaEmision,
        XMLBase64=data.XMLBase64
    )
    comprobante_id = await database.execute(query)
    return {
        "mensaje": "Comprobante recibido correctamente",
        "id": comprobante_id,
        "eNCF": data.eNCF
    }

from typing import List

@app.get("/comprobantes", response_model=List[Comprobante])
async def listar_comprobantes():
    query = comprobantes.select()
    resultados = await database.fetch_all(query)
    return resultados