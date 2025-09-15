import os
from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, String
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")  # Asegura que lo busque explícitamente


# Cargar las variables desde el archivo .env
load_dotenv()

# Construir la URL correctamente
DATABASE_URL = os.getenv("DATABASE_URL")

# Conexión a la base de datos
database = Database(DATABASE_URL)

# Crear engine para SQLAlchemy
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Definir una tabla para probar
comprobantes = Table(
    "comprobantes",
    metadata,
    Column("eNCF", String, primary_key=True),
    Column("RNCEmisor", String),
    Column("FechaEmision", String),
    Column("XMLBase64", String),
)

# Crear tabla en la base de datos
def crear_tabla():
    metadata.create_all(engine)
    print("✅ Tabla creada correctamente")

# Ejecutar prueba
if __name__ == "__main__":
    crear_tabla()
