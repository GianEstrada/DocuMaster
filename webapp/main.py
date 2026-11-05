from datetime import date
from urllib.parse import parse_qs

from fastapi import Body, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field, ValidationError

from documaster.models.orden_salida import DEFAULT_CLAUSES, OrdenSalidaSchema
from documaster.services.document_service import DocumentService
from webapp import auth, db
from webapp.settings import ROOT, SESSION_TTL_SECONDS

app = FastAPI(title="DocuMaster", docs_url=None, redoc_url=None, openapi_url=None)
templates = Environment(
    loader=FileSystemLoader(ROOT / "webapp" / "templates"),
    autoescape=select_autoescape(["html"]),
)
documents = DocumentService(ROOT)

COMPUTED_FIELDS = ("subtotal", "iva", "total")
PRINT_TOOLBAR = """
<style>
  .no-print { position: sticky; top: 0; display: flex; gap: 10px; padding: 10px; background: #183b63; font-family: Arial, sans-serif; }
  .no-print a, .no-print button { color: #fff; background: #2e6da4; border: 0; padding: 12px 18px; border-radius: 6px; font-size: 16px; text-decoration: none; cursor: pointer; }
  @media print { .no-print { display: none; } }
</style>
<div class="no-print">
  <a href="/">Nuevo contrato</a>
  <a href="/contratos">Historial</a>
  <button onclick="window.print()">Imprimir / Guardar PDF</button>
</div>
"""


class Arrendador(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    rfc: str = Field(pattern=r"^[A-ZÑ&a-zñ]{3,4}\d{6}[A-Za-z0-9]{3}$")


def page(name: str, **context) -> HTMLResponse:
    return HTMLResponse(templates.get_template(name).render(**context))


def validation_errors(error: ValidationError) -> JSONResponse:
    errores = [
        {"campo": ".".join(str(part) for part in item["loc"]), "mensaje": item["msg"]}
        for item in error.errors()
    ]
    return JSONResponse({"errores": errores}, status_code=422)


@app.exception_handler(auth.NotAuthenticated)
async def not_authenticated(request: Request, _: auth.NotAuthenticated):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "No autenticado."}, status_code=401)
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(db.DatabaseError)
async def database_error(_: Request, error: db.DatabaseError):
    return JSONResponse({"error": str(error)}, status_code=502)


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return page("login.html", error=None)


@app.post("/login")
async def login(request: Request):
    form = parse_qs((await request.body()).decode())
    if not auth.check_password(form.get("password", [""])[0]):
        return HTMLResponse(templates.get_template("login.html").render(error="Contraseña incorrecta."), status_code=401)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.create_token(),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@app.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(auth.COOKIE_NAME)
    return response


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(auth.require_login)])
def form():
    return page(
        "form.html",
        arrendador=db.get_arrendador(),
        clausulas=DEFAULT_CLAUSES,
        hoy=date.today().isoformat(),
    )


@app.get("/contratos", response_class=HTMLResponse, dependencies=[Depends(auth.require_login)])
def history():
    return page("lista.html", contratos=db.list_contratos())


@app.get("/contratos/{contrato_id}", response_class=HTMLResponse, dependencies=[Depends(auth.require_login)])
def view_contract(contrato_id: str):
    row = db.get_contrato(contrato_id)
    if not row:
        return HTMLResponse("Contrato no encontrado.", status_code=404)
    datos = {key: value for key, value in row["datos"].items() if key not in COMPUTED_FIELDS}
    html = documents.render(OrdenSalidaSchema.model_validate(datos))
    return HTMLResponse(html.replace("<body>", f"<body>{PRINT_TOOLBAR}", 1))


@app.put("/api/arrendador", dependencies=[Depends(auth.require_login)])
def update_landlord(payload: Arrendador):
    db.save_arrendador(payload.nombre.strip(), payload.rfc.strip().upper())
    return {"ok": True}


@app.post("/api/contratos", dependencies=[Depends(auth.require_login)])
def create_contract(payload: dict = Body(...)):
    for number, clause in enumerate(payload.get("clausulas") or [], start=1):
        if isinstance(clause, dict):
            clause["numero"] = number
    try:
        order = OrdenSalidaSchema.model_validate(payload)
    except ValidationError as error:
        return validation_errors(error)
    try:
        row = db.insert_contrato(order.folio, order.cliente_razon_social, str(order.total), order.model_dump(mode="json"))
    except db.DuplicateFolio:
        return JSONResponse(
            {"errores": [{"campo": "folio", "mensaje": "Ya existe un contrato con ese folio."}]},
            status_code=422,
        )
    db.save_arrendador(order.arrendador_nombre, order.arrendador_rfc)
    return {"id": row["id"], "url": f"/contratos/{row['id']}"}
