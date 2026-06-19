# Bulk Image Metadata Stripper

## Overview

A lightweight web-based single-page application for stripping metadata from image files in bulk. Upload multiple images, choose output format (JPEG or PNG) and export mode (overwrite or copy), then download a zip of all stripped results.

## Stack

- **Backend**: Python 3 + FastAPI + Uvicorn
- **Processing**: Pillow (PIL)
- **Frontend**: Plain HTML + CSS + JS (single page, no framework)
- **Dependencies**: fastapi, uvicorn[standard], Pillow, python-multipart

## Supported Formats

| Input        | Output          |
|-------------|-----------------|
| JPEG, PNG, WebP, GIF, TIFF, BMP | JPG or PNG (user selects) |

## Architecture

### Backend Endpoints

- `GET /` — Serves the single-page frontend (from `templates/index.html`)
- `POST /upload` — Accepts multipart form data (images + options), processes all files server-side, returns a zip containing the output images
- Temporary uploads and intermediate files live in `uploads/` and are cleaned up after the response is sent

### Processing Logic

1. User uploads N images via the web form
2. For each image:
   a. Open with Pillow
   b. Re-save with zero metadata (Pillow strips all EXIF/IPTC/XMP on re-encode by default)
   c. Convert RGBA→RGB when outputting to JPEG (white background)
   d. Convert to user-chosen output format
3. Zip all processed images into a single archive
4. Return zip as a download response
5. Clean up temp files

### Export Modes

- **Overwrite**: Each file is re-encoded with the same filename (but new extension if format changed). Original files are bundled into the zip as a backup.
- **Copy new**: Stripped files are saved with a `_stripped` suffix before the extension. Originals remain untouched. Both originals and stripped files are bundled into the zip.

### Frontend

- File picker: `<input type="file" multiple accept="image/*">`
- Output format: radio buttons (JPEG / PNG)
- Export mode: radio buttons (Overwrite / Copy new)
- Upload button triggers the submission
- Progress area shows status per-file as they process
- A download link appears when the zip is ready
- Clean, minimal design, works on desktop and mobile

### Error Handling

- Invalid file types are rejected before upload
- Server returns per-file error messages if any fail to process
- Zip download still contains successfully processed files even if some fail

## File Structure

```
metadata-remover/
├── main.py
├── requirements.txt
├── templates/
│   └── index.html
├── uploads/          # Temp — gitignored
└── docs/superpowers/specs/
    └── 2026-06-19-metadata-remover-design.md
```
