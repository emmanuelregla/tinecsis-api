from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

router = APIRouter()
TOKEN_FILE = Path("token.txt")

# 📦 Estructura de entrada esperada
class TokenInput(BaseModel):
    token: str

# 🎯 Endpoint para guardar token manualmente
@router.post("/auth/token/manual")
def guardar_token_manual(data: TokenInput):
    try:
        TOKEN_FILE.write_text(data.token.strip(), encoding="utf-8")
        return {"mensaje": "✅ Token guardado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error al guardar el token: {e}")
