# DocuMaster

Aplicación de escritorio offline para capturar datos editables, calcular importes, modificar cláusulas y generar un contrato de arrendamiento/factura proforma en PDF.

## Ejecutar

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Microsoft Edge se usa como motor principal para imprimir el HTML/CSS con fidelidad visual. WeasyPrint queda como segunda opción y ReportLab como último fallback de contingencia. Edge debe estar instalado en Windows; normalmente ya viene incluido.
