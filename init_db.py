import os
import sqlalchemy

DATABASE_URL = "postgresql://tinecsis_ecf_db_user:U31Vw2pt46Qxrc3c5fDhCnN3NJEvQdQL@dpg-d1iki12li9vc73898a6g-a.oregon-postgres.render.com/tinecsis_ecf_db"  # Reemplaza con tu external URL de Render

engine = sqlalchemy.create_engine(DATABASE_URL)
metadata = sqlalchemy.MetaData()

comprobantes = sqlalchemy.Table(
    "comprobantes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("RNCEmisor", sqlalchemy.String),
    sqlalchemy.Column("eNCF", sqlalchemy.String),
    sqlalchemy.Column("FechaEmision", sqlalchemy.String),
    sqlalchemy.Column("XMLBase64", sqlalchemy.Text),
)

metadata.create_all(engine)
print("✅ Tabla creada correctamente")

