import os
import databases
import sqlalchemy

# URL de la base de datos desde variable de entorno
DATABASE_URL = os.getenv("DATABASE_URL")

# Conexión a la base de datos
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# Tabla comprobantes
comprobantes = sqlalchemy.Table(
    "comprobantes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("RNCEmisor", sqlalchemy.String),
    sqlalchemy.Column("eNCF", sqlalchemy.String),
    sqlalchemy.Column("FechaEmision", sqlalchemy.String),
    sqlalchemy.Column("XMLBase64", sqlalchemy.Text),
)

# Crear engine y las tablas
engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)
