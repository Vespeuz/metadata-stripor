# Bulk Image Metadata Stripper — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight web-based single-page app where users upload multiple images, strip their metadata, and download the results as a zip.

**Architecture:** Python FastAPI backend serves a single HTML page. Uploaded images are processed with Pillow (re-save strips all metadata), then bundled into a zip and returned as a download.

**Tech Stack:** Python 3, FastAPI, Uvicorn, Pillow, python-multipart

---

### Task 1: Project Scaffolding

**Files:**
- Create: `D:\Repo\Random Personal Projects\MetadataRemover\requirements.txt`
- Create: `D:\Repo\Random Personal Projects\MetadataRemover\.gitignore`
- Create: `D:\Repo\Random Personal Projects\MetadataRemover\templates\index.html`
- Create: `D:\Repo\Random Personal Projects\MetadataRemover\main.py`

- [ ] **Step 1: Create requirements.txt**

```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
Pillow==11.1.0
python-multipart==0.0.19
```

- [ ] **Step 2: Create .gitignore**

```txt
__pycache__/
*.pyc
uploads/
venv/
.venv/
```

- [ ] **Step 3: Create the frontend HTML at `templates/index.html`**

A single-page with:
- `<input type="file" multiple accept="image/*">`
- Radio group: output format (JPEG / PNG), default JPEG
- Radio group: mode (Overwrite / Copy new), default Copy new
- Upload button
- Status area (shows per-file progress + error messages)
- Download link (hidden until zip is ready)

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bulk Metadata Stripper</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #222; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.container { background: #fff; border-radius: 12px; padding: 2rem; width: 100%; max-width: 500px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
p.sub { color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }
.form-group { margin-bottom: 1.25rem; }
label { display: block; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.4rem; }
.radio-group { display: flex; gap: 1rem; }
.radio-group label { font-weight: 400; font-size: 0.9rem; cursor: pointer; }
input[type="file"] { width: 100%; padding: 0.5rem; border: 2px dashed #ccc; border-radius: 8px; cursor: pointer; background: #fafafa; }
input[type="file"]:hover { border-color: #888; }
button { width: 100%; padding: 0.75rem; background: #222; color: #fff; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
button:hover { background: #000; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
#status { margin-top: 1rem; font-size: 0.85rem; line-height: 1.6; }
#status .error { color: #d32f2f; }
#status .success { color: #2e7d32; }
#download { display: none; margin-top: 1rem; }
#download a { display: block; text-align: center; padding: 0.75rem; background: #1976d2; color: #fff; border-radius: 8px; text-decoration: none; font-weight: 600; }
#download a:hover { background: #1565c0; }
</style>
</head>
<body>
<div class="container">
<h1>Metadata Stripper</h1>
<p class="sub">Strip EXIF / IPTC / XMP metadata from your images in bulk.</p>

<div class="form-group">
<label for="files">Select images</label>
<input type="file" id="files" multiple accept="image/jpeg,image/png,image/webp,image/gif,image/tiff,image/bmp">
</div>

<div class="form-group">
<label>Output format</label>
<div class="radio-group">
<label><input type="radio" name="format" value="JPEG" checked> JPEG</label>
<label><input type="radio" name="format" value="PNG"> PNG</label>
</div>
</div>

<div class="form-group">
<label>Mode</label>
<div class="radio-group">
<label><input type="radio" name="mode" value="overwrite"> Overwrite</label>
<label><input type="radio" name="mode" value="copy_new" checked> Copy new</label>
</div>
</div>

<button id="uploadBtn" onclick="upload()">Strip &amp; Download</button>

<div id="status"></div>
<div id="download"></div>
</div>

<script>
async function upload() {
const files = document.getElementById('files').files;
if (!files.length) { document.getElementById('status').innerHTML = '<span class="error">Select at least one image.</span>'; return; }

const format = document.querySelector('input[name="format"]:checked').value;
const mode = document.querySelector('input[name="mode"]:checked').value;
const btn = document.getElementById('uploadBtn');
const status = document.getElementById('status');
const download = document.getElementById('download');

btn.disabled = true;
download.style.display = 'none';
status.innerHTML = '';

const formData = new FormData();
for (const f of files) formData.append('files', f);
formData.append('output_format', format);
formData.append('mode', mode);

try {
const res = await fetch('/upload', { method: 'POST', body: formData });
if (!res.ok) {
const err = await res.json();
status.innerHTML = `<span class="error">${err.detail || 'Upload failed.'}</span>`;
btn.disabled = false;
return;
}
const blob = await res.blob();
const url = URL.createObjectURL(blob);
download.innerHTML = `<a href="${url}" download="stripped_images.zip">Download ZIP</a>`;
download.style.display = 'block';
status.innerHTML = '<span class="success">Done! Your images are ready.</span>';
} catch (e) {
status.innerHTML = `<span class="error">Error: ${e.message}</span>`;
}
btn.disabled = false;
}
</script>
</body>
</html>
```

- [ ] **Step 4: Create the FastAPI backend at `main.py`**

```python
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates  # will use custom HTML serving instead
from starlette.requests import Request
from starlette.responses import HTMLResponse
from PIL import Image

app = FastAPI(title="Metadata Stripper")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tiff", ".tif", ".bmp"}
OUTPUT_FORMATS = {"JPEG": "JPEG", "PNG": "PNG"}


def is_allowed(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def strip_metadata_and_convert(input_path: Path, output_path: Path, output_format: str):
    img = Image.open(input_path)
    # Convert RGBA to RGB for JPEG output
    if output_format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img)
        img = background
    elif output_format == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    elif output_format == "PNG" and img.mode not in ("RGB", "RGBA", "P"):
        img = img.convert("RGBA")

    img.save(output_path, format=output_format)
    img.close()


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/upload")
async def upload_images(
    files: list[UploadFile] = File(...),
    output_format: str = Form("JPEG"),
    mode: str = Form("copy_new"),
):
    if output_format not in OUTPUT_FORMATS:
        raise HTTPException(400, f"Invalid output format. Use JPEG or PNG.")
    if mode not in ("overwrite", "copy_new"):
        raise HTTPException(400, f"Invalid mode. Use 'overwrite' or 'copy_new'.")

    # Create a temp working directory
    work_dir = Path(tempfile.mkdtemp(dir=UPLOAD_DIR))
    output_dir = work_dir / "output"
    output_dir.mkdir()

    processed = []
    errors = []

    for file in files:
        if not file.filename or not is_allowed(file.filename):
            errors.append(f"'{file.filename}': Unsupported format.")
            continue

        try:
            ext = Path(file.filename).suffix.lower()
            safe_name = Path(file.filename).stem

            # Save uploaded file
            input_path = work_dir / file.filename
            content = await file.read()
            input_path.write_bytes(content)

            # Determine output filename
            out_ext = ".jpg" if output_format == "JPEG" else ".png"
            if mode == "overwrite":
                out_name = safe_name + out_ext
            else:
                out_name = f"{safe_name}_stripped{out_ext}"

            output_path = output_dir / out_name
            strip_metadata_and_convert(input_path, output_path, output_format)

            # If mode is overwrite, also bundle originals
            if mode == "overwrite":
                backup_dir = output_dir / "_originals"
                backup_dir.mkdir(exist_ok=True)
                shutil.copy2(input_path, backup_dir / file.filename)

            processed.append(file.filename)
        except Exception as e:
            errors.append(f"'{file.filename}': {str(e)}")

    if not processed:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(400, "No files could be processed. " + "; ".join(errors))

    # Create zip
    zip_path = work_dir / "stripped_images.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in output_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(output_dir))

    # Cleanup temp files after response
    response = FileResponse(
        zip_path,
        media_type="application/zip",
        filename="stripped_images.zip",
        headers={"X-Processing-Errors": "; ".join(errors)} if errors else {},
    )

    # Schedule cleanup
    import atexit
    cleanup_path = str(work_dir)
    atexit.register(lambda p=cleanup_path: shutil.rmtree(p, ignore_errors=True))

    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Task 2: Install Dependencies & Verify

**Files:**
- Modify: none (run commands)

- [ ] **Step 1: Create virtual environment and install dependencies**

```bash
cd D:\Repo\Random Personal Projects\MetadataRemover
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 2: Start the server and verify it works**

```bash
cd D:\Repo\Random Personal Projects\MetadataRemover
venv\Scripts\python main.py
```

Expected: Server starts on `http://0.0.0.0:8000`. Open in browser, upload images, verify download works.

- [ ] **Step 3: Stop the server**

Kill the uvicorn process.

### Task 3: Final Checks

- [ ] **Step 1: Verify .gitignore covers uploads/ and venv/**
- [ ] **Step 2: Make initial git commit**

```bash
git add -A
git commit -F - <<'EOF'
feat: initial bulk metadata stripper

Single-page FastAPI web app with Pillow-based metadata stripping.
Supports JPEG/PNG/WebP/GIF/TIFF/BMP input, JPEG/PNG output,
overwrite and copy-new modes.

Co-authored-by: CommandCodeBot <noreply@commandcode.ai>
EOF
```
