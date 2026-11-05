# DocuMaster

Genera contratos de arrendamiento / facturas proforma en PDF con datos y cláusulas editables. Hay dos versiones que comparten el modelo Pydantic y la plantilla HTML/CSS:

- **Web (Vercel + Supabase)**: se usa desde el navegador, incluida una tablet Android.
- **Escritorio (Windows, PyQt6)**: versión offline.

## Web: Supabase + Vercel

### 1. Supabase

1. Crea un proyecto en [supabase.com](https://supabase.com).
2. En **SQL Editor** ejecuta [supabase/schema.sql](supabase/schema.sql).
3. En **Project Settings > API** copia la `Project URL` y la clave `service_role`.
   La clave `service_role` es secreta: solo va en variables de entorno del servidor, nunca en el código ni en el navegador.

### 2. Vercel

1. Importa este repositorio en [vercel.com](https://vercel.com) (el *Framework Preset* puede quedarse en "Other").
2. En **Settings > Environment Variables** define:

| Variable | Descripción |
| --- | --- |
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave `service_role` |
| `APP_PASSWORD` | Contraseña de acceso a la app |
| `SESSION_SECRET` | Cadena aleatoria larga para firmar la sesión |

3. Despliega. Abre la URL desde la tablet e inicia sesión con `APP_PASSWORD`.

Genera un `SESSION_SECRET` con: `py -3.11 -c "import secrets; print(secrets.token_urlsafe(48))"`

### PDF

Vercel no puede ejecutar Edge ni WeasyPrint. Tras generar el contrato se abre la vista imprimible (mismo HTML/CSS que la versión de escritorio); toca **Imprimir / Guardar PDF** y elige "Guardar como PDF" en el navegador de la tablet.

### Ejecutar en local

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt uvicorn
$env:SUPABASE_URL="https://TU-PROYECTO.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="..."
$env:APP_PASSWORD="..."
$env:SESSION_SECRET="..."
uvicorn webapp.main:app --reload
```

Los datos del arrendador (nombre y RFC) se guardan en la tabla `arrendador` y se precargan en cada sesión. El acceso a la base está protegido con RLS y solo el backend puede leerla.

## Escritorio (Windows)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-desktop.txt
python app.py
```

Microsoft Edge se usa como motor principal para imprimir el HTML/CSS con fidelidad visual. WeasyPrint queda como segunda opción y ReportLab como último fallback de contingencia.

La pestaña **Arrendador** permite editar la razón social/nombre y RFC que aparecen en el contrato. Esos dos valores se guardan localmente mediante la configuración de Windows (`QSettings`) para reutilizarlos en la siguiente apertura; los datos del cliente y del contrato no se guardan en esa configuración.
