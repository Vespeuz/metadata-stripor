import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from starlette.responses import HTMLResponse
from PIL import Image

app = FastAPI(title="Metadata Stripper")

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tiff", ".tif", ".bmp"}
OUTPUT_FORMATS = {"JPEG": "JPEG", "PNG": "PNG"}


def is_allowed(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def strip_metadata_and_convert(input_path: Path, output_path: Path, output_format: str):
    img = Image.open(input_path)
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

    work_dir = Path(tempfile.mkdtemp(dir=UPLOAD_DIR))
    local_output = work_dir / "output"
    local_output.mkdir()

    processed = []
    errors = []
    output_files = []

    for file in files:
        if not file.filename or not is_allowed(file.filename):
            errors.append(f"'{file.filename}': Unsupported format.")
            continue

        try:
            safe_filename = Path(file.filename).name
            safe_stem = Path(safe_filename).stem

            input_path = work_dir / safe_filename
            content = await file.read()
            input_path.write_bytes(content)

            out_ext = ".jpg" if output_format == "JPEG" else ".png"
            if mode == "overwrite":
                out_name = safe_stem + out_ext
            else:
                out_name = f"{safe_stem}_stripped{out_ext}"

            output_path = local_output / out_name
            strip_metadata_and_convert(input_path, output_path, output_format)

            # Copy to persistent output dir for individual file serving
            persistent_path = OUTPUT_DIR / out_name
            shutil.copy2(output_path, persistent_path)

            if mode == "overwrite":
                backup_dir = local_output / "_originals"
                backup_dir.mkdir(exist_ok=True)
                shutil.copy2(input_path, backup_dir / safe_filename)

            output_files.append(out_name)
            processed.append(file.filename)
        except Exception as e:
            errors.append(f"'{file.filename}': {str(e)}")

    if not processed:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(400, "No files could be processed. " + "; ".join(errors))

    # Overwrite mode: return individual download links
    if mode == "overwrite":
        shutil.rmtree(work_dir, ignore_errors=True)

        links_html = "".join(
            f'<a href="/download/{name}" class="file-link">{name}</a>'
            for name in output_files
        )
        errors_html = f'<div class="errors">{"<br>".join(errors)}</div>' if errors else ""

        return HTMLResponse(f"""<!DOCTYPE html>
<style>
.file-link {{ display:block; padding:0.6rem 1rem; background:#1976d2; color:#fff; border-radius:8px; text-decoration:none; font-weight:600; text-align:center }}
.file-link:hover {{ background:#1565c0 }}
.errors {{ margin-top:0.75rem; color:#d32f2f; font-size:0.85rem }}
</style>
<body style="font-family:system-ui;padding:2rem;max-width:500px;margin:auto;background:#f5f5f5">
<div style="background:#fff;border-radius:12px;padding:2rem;box-shadow:0 2px 12px rgba(0,0,0,0.08)">
<h2 style="margin-top:0">Stripped {len(output_files)} file{"s" if len(output_files)>1 else ""}</h2>
<div style="display:flex;flex-direction:column;gap:0.5rem;margin:1rem 0">{links_html}</div>
{errors_html}
<p style="color:#666;font-size:0.85rem">Files also saved to <code>output/</code> folder</p>
<a href="/" style="display:inline-block;margin-top:1rem;color:#1976d2">← Back</a>
</div></body>""")

    # Copy-new mode: return zip (original)
    zip_path = work_dir / "stripped_images.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in local_output.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(local_output))

    errors_str = "; ".join(errors)
    headers = {"X-Processing-Errors": errors_str} if errors else {}

    cleanup_path = str(work_dir)
    cleanup_task = BackgroundTask(shutil.rmtree, cleanup_path, ignore_errors=True)

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="stripped_images.zip",
        headers=headers,
        background=cleanup_task,
    )


@app.get("/download/{filename}")
async def download_file(filename: str):
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(file_path, filename=safe_name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
