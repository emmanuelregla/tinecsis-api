import asyncio
import asyncpg

# Coloca aquí tu EXTERNAL DATABASE URL de Render
DATABASE_URL = "postgresql://tinecsis_ecf_db_user:U31Vw2pt46Qxrc3c5fDhCnN3NJEvQdQL@dpg-d1iki12li9vc73898a6g-a.oregon-postgres.render.com/tinecsis_ecf_db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS comprobantes (
    id SERIAL PRIMARY KEY,
    "RNCEmisor" VARCHAR,
    "eNCF" VARCHAR,
    "FechaEmision" VARCHAR,
    "XMLBase64" TEXT
);
"""

async def create_table():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(CREATE_TABLE_SQL)
    await conn.close()
    print("✅ Tabla 'comprobantes' creada correctamente.")

if __name__ == "__main__":
    asyncio.run(create_table())