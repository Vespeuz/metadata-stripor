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
UPLOAD_DIR.mkdir(exist_ok=True)

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

            input_path = work_dir / file.filename
            content = await file.read()
            input_path.write_bytes(content)

            out_ext = ".jpg" if output_format == "JPEG" else ".png"
            if mode == "overwrite":
                out_name = safe_name + out_ext
            else:
                out_name = f"{safe_name}_stripped{out_ext}"

            output_path = output_dir / out_name
            strip_metadata_and_convert(input_path, output_path, output_format)

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

    zip_path = work_dir / "stripped_images.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in output_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(output_dir))

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
