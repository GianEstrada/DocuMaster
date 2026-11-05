import httpx

from webapp.settings import env


class DuplicateFolio(Exception):
    pass


class DatabaseError(Exception):
    pass


def _client() -> httpx.Client:
    key = env("SUPABASE_SERVICE_ROLE_KEY")
    return httpx.Client(
        base_url=f"{env('SUPABASE_URL').rstrip('/')}/rest/v1",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )


def _request(method: str, path: str, **kwargs):
    try:
        with _client() as client:
            response = client.request(method, path, **kwargs)
    except httpx.HTTPError as error:
        raise DatabaseError("No fue posible conectar con la base de datos.") from error
    if response.status_code == 409:
        raise DuplicateFolio()
    if response.status_code >= 400:
        raise DatabaseError(f"Error de base de datos ({response.status_code}).")
    return response.json() if response.content else None


def get_arrendador() -> dict:
    rows = _request("GET", "/arrendador", params={"id": "eq.1", "select": "nombre,rfc"})
    return rows[0] if rows else {"nombre": "NOMBRE DEL ARRENDADOR", "rfc": "XAXX010101000"}


def save_arrendador(nombre: str, rfc: str) -> None:
    _request(
        "POST",
        "/arrendador",
        headers={"Prefer": "resolution=merge-duplicates"},
        json={"id": 1, "nombre": nombre, "rfc": rfc},
    )


def insert_contrato(folio: str, cliente: str, total: str, datos: dict) -> dict:
    rows = _request(
        "POST",
        "/contratos",
        headers={"Prefer": "return=representation"},
        json={"folio": folio, "cliente": cliente, "total": total, "datos": datos},
    )
    return rows[0]


def get_contrato(contrato_id: str) -> dict | None:
    rows = _request("GET", "/contratos", params={"id": f"eq.{contrato_id}", "select": "*"})
    return rows[0] if rows else None


def list_contratos(limit: int = 100) -> list[dict]:
    return _request(
        "GET",
        "/contratos",
        params={"select": "id,folio,cliente,total,created_at", "order": "created_at.desc", "limit": limit},
    )
