import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, JSONResponse
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

app = FastAPI()

# ---------------------------
# DATOS FIJOS DE ANDES SCD
# (Luego los leemos desde tu Excel/base de datos)
# ---------------------------
ANDES = {
    "empresa_nombre": "ANDES SERVICIO DE CERTIFICACION DIGITAL S A S",
    "nit": "900000000-0",
    "email": "info@andesscd.com.co",
    "telefono": "6012415539",
    "rep_principal": "REPRESENTANTE LEGAL PRINCIPAL",
    "rep_suplente": "REPRESENTANTE LEGAL SUPLENTE",
}

def ensure_need_appearances(writer: PdfWriter):
    """Hace que el visor (Chrome/Adobe) renderice los valores sin regenerar fuentes."""
    try:
        if "/AcroForm" in writer._root_object:
            acro = writer._root_object["/AcroForm"]
            acro.update({NameObject("/NeedAppearances"): BooleanObject(True)})
    except Exception:
        pass

@app.get("/")
def home():
    return {"status": "API Andes SCD funcionando"}

# 1) ENDPOINT: ver campos reales del PDF
@app.post("/fields")
async def fields(file: UploadFile = File(...)):
    raw = await file.read()
    reader = PdfReader(io.BytesIO(raw))
    f = reader.get_fields() or {}
    return {"count": len(f), "fields": list(f.keys())}

# 2) ENDPOINT: debug para etiquetar campos (sin crashear por fuentes)
@app.post("/debug/label")
async def debug_label(file: UploadFile = File(...)):
    raw = await file.read()
    reader = PdfReader(io.BytesIO(raw))
    fields = reader.get_fields() or {}

    if not fields:
        return JSONResponse(
            status_code=400,
            content={"detail": "Este PDF no tiene campos de formulario (no es rellenable)."}
        )

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    acro = reader.trailer["/Root"].get("/AcroForm")
    if acro:
        writer._root_object.update({NameObject("/AcroForm"): acro})

    ensure_need_appearances(writer)

    label_map = {k: k[:28] for k in fields.keys()}  # corto para que quepa

    for page in writer.pages:
        # CLAVE: evitar error /DescendantFonts
        writer.update_page_form_field_values(page, label_map, auto_regenerate=False)

    out = io.BytesIO()
    writer.write(out)

    return Response(
        content=out.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="debug_labeled.pdf"'}
    )

# 3) ENDPOINT: diligenciar el PDF según módulo
@app.post("/generate")
async def generate(
    module: str = Form(...),  # EJECUTIVOS o CONTACT_CENTER
    file: UploadFile = File(...)
):
    module = (module or "").upper().strip()
    if module not in ("EJECUTIVOS", "CONTACT_CENTER"):
        raise HTTPException(status_code=400, detail="module debe ser EJECUTIVOS o CONTACT_CENTER")

    rep = ANDES["rep_principal"] if module == "EJECUTIVOS" else ANDES["rep_suplente"]

    raw = await file.read()
    reader = PdfReader(io.BytesIO(raw))
    pdf_fields = reader.get_fields() or {}
    if not pdf_fields:
        raise HTTPException(status_code=400, detail="Este PDF no tiene campos de formulario.")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    acro = reader.trailer["/Root"].get("/AcroForm")
    if acro:
        writer._root_object.update({NameObject("/AcroForm"): acro})

    ensure_need_appearances(writer)

    # ✅ MVP: llenado de prueba (para confirmar que YA escribe en el PDF)
    # Luego hacemos el mapeo real "campo -> dato correcto".
    fill_map = {}
    for k in pdf_fields.keys():
        if k.startswith("Text"):
            fill_map[k] = ANDES["empresa_nombre"]  # por ahora llena para validar
    # ejemplo: ponemos representante en un campo específico si existe
    if "Text10" in pdf_fields:
        fill_map["Text10"] = rep
    if "Text11" in pdf_fields:
        fill_map["Text11"] = ANDES["nit"]
    if "Text12" in pdf_fields:
        fill_map["Text12"] = ANDES["email"]
    if "Text13" in pdf_fields:
        fill_map["Text13"] = ANDES["telefono"]

    for page in writer.pages:
        writer.update_page_form_field_values(page, fill_map, auto_regenerate=False)

    out = io.BytesIO()
    writer.write(out)

    return Response(
        content=out.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ANDES_{module}.pdf"'}
    )





