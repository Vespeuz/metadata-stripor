# Bulk Metadata Stripper

A lightweight web app that strips EXIF, IPTC, and XMP metadata from images in bulk. Built with **FastAPI** and **Pillow**.

Upload multiple images at once, choose your output format and mode, and download clean, metadata-free images — no tracking, no data leaving your machine, everything runs locally.

## Features

- **Bulk upload** — select any number of images at once
- **Two output modes**
  - **Copy new** — creates new stripped files (named `_stripped`) and bundles them in a ZIP
  - **Overwrite** — replaces the originals with stripped versions and shows individual download links
- **Format conversion** — output as JPEG (strips all metadata) or PNG (strips metadata when possible)
- **Handles transparency** — RGBA images are automatically flattened to RGB when saving as JPEG
- **Supported formats** — `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.tiff`, `.tif`, `.bmp`
- **Self-contained** — no external services, no telemetry, no database

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

Open **http://localhost:8000** in your browser.

## How It Works

1. Images are uploaded to a temporary working directory
2. Pillow opens each image and re-saves it in the chosen format, which discards all metadata
3. For JPEG output, RGBA images are composited onto a white background automatically
4. Processed files are served as a ZIP download (copy-new mode) or individual links (overwrite mode)
5. All processed files are also saved to the `output/` folder on disk

### Modes

| Mode | Behavior |
|---|---|
| **Copy new** | Original files are kept in the temp workspace. Returns a ZIP of `<name>_stripped.jpg/png` files. |
| **Overwrite** | Original files are backed up to a `_originals` subfolder in the temp workspace. Returns individual download links for each stripped file. |

## Tech Stack

- **Python 3.12+** — language
- **FastAPI** — web framework
- **Pillow** — image loading, conversion, and re-saving (which strips metadata by nature)
- **uvicorn** — ASGI server
- **python-multipart** — multipart form parsing

## Project Structure

```
├── main.py              # FastAPI app — routes, image processing, file handling
├── requirements.txt     # Python dependencies
├── templates/
│   └── index.html       # Single-page upload UI
├── uploads/             # Temp working directory (gitignored)
├── output/              # Processed files are saved here (gitignored)
└── docs/                # Additional documentation
```

## API

### `POST /upload`

Upload one or more images for metadata stripping.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `files` | `UploadFile[]` | required | The images to process |
| `output_format` | `string` | `JPEG` | `JPEG` or `PNG` |
| `mode` | `string` | `copy_new` | `copy_new` (ZIP) or `overwrite` (individual links) |

In **copy-new mode**, returns a ZIP file. In **overwrite mode**, returns an HTML page with individual download links.

### `GET /download/{filename}`

Download a specific processed file by name (used for the individual links in overwrite mode).
