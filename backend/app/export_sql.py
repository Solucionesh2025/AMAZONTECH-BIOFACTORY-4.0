"""Genera el DDL de PostgreSQL a partir de los modelos: python -m app.export_sql > ../../db/schema.sql"""
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from . import models  # noqa: F401
from .database import Base

print("-- BIOFACTORY 4.0 — esquema PostgreSQL (generado desde los modelos)\n")
for table in Base.metadata.sorted_tables:
    print(str(CreateTable(table).compile(dialect=postgresql.dialect())).strip() + ";\n")
    for idx in table.indexes:
        print(str(CreateIndex(idx).compile(dialect=postgresql.dialect())).strip() + ";")
    print()
