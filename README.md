# Andes SCD – Automatización de documentos (MVP)

Este proyecto es un **MVP** para diligenciar archivos (PDF / Word / Excel) con los **datos fijos de Andes SCD**
y generar **salida final en PDF**.

Incluye **2 módulos**:
- **EJECUTIVOS** → usa Representante Legal **principal**
- **CONTACT_CENTER** → usa Representante Legal **suplente**

## Requisitos
- Windows 10/11
- Python 3.10+ instalado
- Visual Studio Code
- (Recomendado) LibreOffice instalado para convertir DOCX/XLSX a PDF

## Paso a paso (principiante)

### 1) Abrir el proyecto
1. Descomprime el ZIP.
2. Abre la carpeta en VS Code (**File > Open Folder**).

### 2) Crear y activar entorno virtual
En la terminal de VS Code (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Si PowerShell bloquea la activación, ejecuta:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```
y vuelve a activar.

### 3) Configurar datos Andes
Edita `config/andes_scd.yml` y completa/ajusta los campos.

### 4) PDF rellenable (con campos)
1. Pon el PDF en `input/`
2. Lista los campos:
```powershell
python scripts\extract_pdf_fields.py "input\TU_ARCHIVO.pdf"
```
3. Ajusta `mapping/pdf_fields.yml`
4. Genera:
```powershell
python scripts\fill_pdf_form.py --module EJECUTIVOS --pdf "input\TU_ARCHIVO.pdf" --mapping "mapping\pdf_fields.yml"
```

### 5) Word (DOCX) → PDF
1. Convierte tu Word a plantilla con variables `{{...}}` (ej: `{{ANDES.NIT}}`, `{{FIRMANTE.NOMBRE}}`)
2. Ponla en `templates/`
3. Genera DOCX diligenciado:
```powershell
python scripts\fill_docx_template.py --module CONTACT_CENTER --template "templates\plantilla.docx"
```
4. Convierte a PDF (LibreOffice):
```powershell
python scripts\convert_to_pdf.py "output\plantilla_CONTACT_CENTER_diligenciada.docx"
```

### 6) Excel (XLSX) → PDF
1. Define celdas en `mapping/xlsx_cells.yml`
2. Genera XLSX diligenciado:
```powershell
python scripts\fill_xlsx_template.py --module EJECUTIVOS --template "templates\plantilla.xlsx" --mapping "mapping\xlsx_cells.yml"
```
3. Convierte a PDF (LibreOffice):
```powershell
python scripts\convert_to_pdf.py "output\plantilla_EJECUTIVOS_diligenciada.xlsx"
```

## Nota sobre PDFs sin campos o escaneados
- Si el PDF **no tiene campos**, este MVP no puede “adivinar” dónde escribir.
- Para esos casos se necesita **modo plantilla por coordenadas (overlay)** o un asistente visual (fase 2).

