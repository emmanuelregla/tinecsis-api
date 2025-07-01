from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Servidor activo"}

class Comprobante(BaseModel):
    RNCEmisor: str
    eNCF: str
    FechaEmision: str
    XMLBase64: str

@app.post("/recibir-comprobante")
async def recibir_comprobante(data: Comprobante):
    print(f"📥 Recibido: {data.eNCF}")
    return {
        "mensaje": "Comprobante recibido correctamente",
        "eNCF": data.eNCF
    }
