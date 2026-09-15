import json
import sqlite3
from datetime import datetime
from pathlib import Path

from documaster.models.orden_salida import OrdenSalidaSchema


class PersistenceService:
    def __init__(self, root: Path):
        self.root = root
        self.storage = root / "storage"
        self.storage.mkdir(exist_ok=True)
        self.db_path = self.storage / "documaster.db"
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS expedientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folio TEXT NOT NULL,
                    cliente TEXT NOT NULL,
                    total TEXT NOT NULL,
                    ruta TEXT NOT NULL,
                    creado_en TEXT NOT NULL
                )
                """
            )

    def save(self, order: OrdenSalidaSchema, html: str, pdf_path: Path) -> Path:
        folder = self.storage / "expedientes" / str(order.fecha_emision.year) / order.folio
        folder.mkdir(parents=True, exist_ok=True)
        json_path = folder / "datos.json"
        html_path = folder / "contrato_factura.html"
        json_path.write_text(order.model_dump_json(indent=2), encoding="utf-8")
        html_path.write_text(html, encoding="utf-8")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO expedientes (folio, cliente, total, ruta, creado_en) VALUES (?, ?, ?, ?, ?)",
                (order.folio, order.cliente_razon_social, str(order.total), str(pdf_path), datetime.now().isoformat()),
            )
        return json_path
