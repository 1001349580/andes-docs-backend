from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

app = FastAPI()

# ---------------------------
# DATOS FIJOS DE ANDES SCD
# ---------------------------
ANDES_BASE = {
    # Ajusta estos valores con tus datos reales (NIT, dirección, banco, etc.)
    "empresa_nombre": "ANDES SERVICIO DE CERTIFICACION DIGITAL S A S",
    "empresa_nit": "900000000-0",
    "empresa_email": "info@andesscd.com.co",
    "empresa_telefono": "6012415539",
    "rep_principal_nombre": "REPRESENTANTE LEGAL PRINCIPAL",
    "rep_suplente_nombre": "REPRESENTANTE LEGAL SUPLENTE",
    "rep_principal_email": "info@andesscd.com.co",
    "rep_suplente_email": "info@andesscd.com.co",
    "rep_principal_telefono": "6012415539",
    "rep_suplente_telefono": "6012415539",
}

def get_actor(module: str) -> dict:
    module = (module or "").upper().strip()
    if module == "EJECUTIVOS":
        return {
            "rep_nombre": ANDES_BASE["rep_principal_nombre"],
            "rep_email": ANDES_BASE["rep_principal_email"],
            "rep_telefono": ANDES_BASE["rep_principal_telefono"],
        }
    if module == "CONTACT_CENTER":
        return {
            "rep_nombre": ANDES_BASE["rep_suplente_nombre"],
            "rep_email": ANDES_BASE["rep_suplente_email"],
            "rep_telefono": ANDES_BASE["rep_suplente_telefono"],
        }
    raise HTTPException(status_code=400, detail="module debe ser EJECUTIVOS o CONTACT_CENTER")

def ensure_need_appearances(writer: PdfWriter):
    # Hace que muchos visores "pinten" el texto en campos rellenados
    if "/AcroForm" not in writer._root_object:
        return
    acro = writer._root_object["/AcroForm"]
    acro.update({NameObject("/NeedAppearances"): BooleanObject(True)})

def fill_pdf_form(pdf_bytes: bytes, values: dict) -> bytes:
    reader = PdfReader(io_bytes(pdf_bytes))
    writer = PdfWriter()

    # Copiar páginas
    for page in reader.pages:
        writer.add_page(page)

    # Copiar acroform si existe
    if reader.trailer["/Root"].get("/AcroForm"):
        writer._root_object.update(
            {NameObject("/AcroForm"): reader.trailer["/Root"]["/AcroForm"]}
        )

    ensure_need_appearances(writer)

    # Llenar campos si existen
    # NOTA: esto solo funciona si el PDF tiene campos de formulario (rellenable)
    for page in writer.pages:
        writer.update_page_form_field_values(page, values)

    out = bytes_out(writer)
    return out

# -------- helpers sin dependencias extra --------
import io

def io_bytes(b: bytes) -> io.BytesIO:
    return io.BytesIO(b)

def bytes_out(writer: PdfWriter) -> bytes:
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

@app.get("/")
def home():
    return {"message": "Andes SCD API funcionando"}

@app.post("/generate")
async def generate(
    module: str = Form(...),   # EJECUTIVOS o CONTACT_CENTER
    file: UploadFile = File(...)
):
    actor = get_actor(module)

    filename = file.filename or "documento"
    ext = filename.lower().split(".")[-1]

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    # Valores que intentaremos mapear a campos del PDF
    # (Luego lo hacemos inteligente con mapeos por formato)
    values = {
        "NOMBRE_EMPRESA": ANDES_BASE["empresa_nombre"],
        "NIT": ANDES_BASE["empresa_nit"],
        "EMAIL": ANDES_BASE["empresa_email"],
        "TELEFONO": ANDES_BASE["empresa_telefono"],
        "REPRESENTANTE": actor["rep_nombre"],
        "REP_EMAIL": actor["rep_email"],
        "REP_TELEFONO": actor["rep_telefono"],
    }

    # MVP: solo PDFs rellenables
    if ext != "pdf":
        raise HTTPException(
            status_code=400,
            detail="MVP: por ahora solo PDF rellenable. Luego activamos Word/Excel."
        )

    # Intentar leer campos para validar si es rellenable
    reader = PdfReader(io_bytes(raw))
    fields = reader.get_fields()
    if not fields:
        raise HTTPException(
            status_code=400,
            detail="Este PDF no tiene campos rellenables (probable escaneado o no-form). Requiere configuración especial."
        )

    # IMPORTANTE: Los nombres de campo reales NO son "NIT" etc.
    # En producción, mapearemos: campo_del_pdf -> valor
    # Por ahora, llenamos SOLO si el PDF tiene esos nombres exactamente.
    filled_pdf = fill_pdf_form(raw, values)

    out_name = f"ANDES_{module}_{filename.rsplit('.',1)[0]}.pdf"
    return Response(
        content=filled_pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{out_name}"'
        }
    )
from fastapi.responses import JSONResponse
import io
from pypdf import PdfReader, PdfWriter

@app.post("/fields")
async def fields(file: UploadFile = File(...)):
    raw = await file.read()
    reader = PdfReader(io.BytesIO(raw))
    f = reader.get_fields() or {}
    return {"count": len(f), "fields": list(f.keys())}

@app.post("/debug/label")
async def debug_label(file: UploadFile = File(...)):
    raw = await file.read()
    reader = PdfReader(io.BytesIO(raw))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    if reader.trailer["/Root"].get("/AcroForm"):
        writer._root_object.update({"/AcroForm": reader.trailer["/Root"]["/AcroForm"]})

    fields = reader.get_fields() or {}

    if not fields:
        return JSONResponse(
            status_code=400,
            content={"detail": "Este PDF no tiene campos de formulario"}
        )

    for page in writer.pages:
        writer.update_page_form_field_values(page, {k: k for k in fields.keys()})

    output = io.BytesIO()
    writer.write(output)

    return Response(
        content=output.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=debug_labeled.pdf"}
    )

