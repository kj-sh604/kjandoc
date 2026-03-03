#!/usr/bin/env python3

# kjandoc demoware server
# fastapi server for the web interface + programmatic merge API.
#
# usage: python server.py [port]
# default port: 8080

# new API durrhurrr:
#   POST /api  — upload .pptx files (multipart), receive merged .pptx
#     curl -X POST http://localhost:8080/api \
#       -F "files=@a.pptx" -F "files=@b.pptx" -o merged.pptx

import os
import sys
import uuid
import time
import shutil
import tempfile
import threading
import subprocess
from pathlib import Path
from urllib.parse import unquote

import uvicorn
from fastapi import FastAPI, File, Query, Request, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask


PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'output'

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# {job_id: {status, command, output, log}}
jobs = {}
jobs_lock = threading.Lock()

app = FastAPI(
    title="kjandoc",
    summary="merge multiple .pptx presentations into one",
    description=(
        "kjandoc merges PowerPoint (.pptx) files while preserving full "
        "editability — layouts, masters, themes, media, and notes are all "
        "carried over.\n\n"
        "### usage\n\n"
        "Upload two or more `.pptx` files via `POST /api` (multipart form) "
        "and receive the merged presentation as a direct download.\n\n"
        "```bash\n"
        "curl -X POST http://localhost:8080/api \\\n"
        "  -F \"files=@deck_a.pptx\" \\\n"
        "  -F \"files=@deck_b.pptx\" \\\n"
        "  -o merged.pptx\n"
        "```\n\n"
        "source: [github.com/kj-sh604/kjandoc](https://github.com/kj-sh604/kjandoc)"
    ),
    version="2026.03.03",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# -- demoware UI endpoints (used by index.html) --

@app.post("/api/upload", include_in_schema=False)
async def upload_file(request: Request):
    job_id = request.headers.get('X-Job-Id', '')
    raw_name = request.headers.get('X-Filename', '')

    if not job_id or not raw_name:
        return JSONResponse(status_code=400, content={"error": "missing headers"})

    body = await request.body()
    if len(body) <= 0:
        return JSONResponse(status_code=400, content={"error": "empty file"})

    name = Path(unquote(raw_name)).name
    if not name.lower().endswith('.pptx'):
        return JSONResponse(status_code=400, content={"error": "not a .pptx file"})

    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    dest = job_dir / name

    dest.write_bytes(body)

    return {"ok": True, "file": name}


@app.post("/api/merge", include_in_schema=False)
async def merge_job(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "bad json"})

    job_id = data.get('job_id', '')
    files = data.get('files', [])

    if not job_id or not files:
        return JSONResponse(status_code=400, content={"error": "missing job_id or files"})

    job_dir = UPLOAD_DIR / job_id
    if not job_dir.exists():
        return JSONResponse(status_code=400, content={"error": "upload dir not found — did you upload first?"})

    # validate filenames (no path traversal)
    for f in files:
        if '/' in f or '\\' in f or '..' in f:
            return JSONResponse(status_code=400, content={"error": f"bad filename: {f}"})
        if not (job_dir / f).exists():
            return JSONResponse(status_code=400, content={"error": f"not found: {f}"})

    # output: epoch_shortid.pptx
    epoch = int(time.time())
    uid = uuid.uuid4().hex[:8]
    out_name = f"{epoch}_{uid}.pptx"
    out_path = OUTPUT_DIR / out_name

    # build the real command
    inputs = [str(job_dir / f) for f in files]
    cmd = ['kjandoc'] + inputs + ['-o', str(out_path)]

    # pretty command for display (strip numeric id prefixes like "3_")
    pretty_names = []
    for f in files:
        parts = f.split('_', 1)
        pretty_names.append(parts[1] if len(parts) == 2 and parts[0].isdigit() else f)
    cmd_str = f"kjandoc {' '.join(pretty_names)} -o output/{out_name}"

    with jobs_lock:
        jobs[job_id] = {
            "status": "running",
            "command": cmd_str,
            "output": out_name,
            "log": "",
        }

    def do_merge():
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            log = result.stdout + result.stderr
            status = "done" if result.returncode == 0 else "error"
        except subprocess.TimeoutExpired:
            log = "timed out (10 min limit)"
            status = "error"
        except Exception as e:
            log = str(e)
            status = "error"

        with jobs_lock:
            jobs[job_id]["log"] = log
            jobs[job_id]["status"] = status

        # clean up uploads for this job
        shutil.rmtree(job_dir, ignore_errors=True)

    threading.Thread(target=do_merge, daemon=True).start()

    return {
        "ok": True,
        "job_id": job_id,
        "command": cmd_str,
        "output": out_name,
    }


@app.get("/api/status/{job_id}", include_in_schema=False)
async def job_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        snapshot = dict(job) if job else None
    if not snapshot:
        return JSONResponse(status_code=404, content={"error": "unknown job"})
    return snapshot


# -- programmatic merge API --

@app.post(
    "/api",
    summary="merge presentations",
    response_class=FileResponse,
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": {}
            },
            "description": "the merged .pptx file",
        },
        400: {"description": "bad request (fewer than 2 files, or non-.pptx file)"},
        500: {"description": "kjandoc merge failed"},
        504: {"description": "merge timed out (10 min limit)"},
    },
)
async def api_merge(
    files: list[UploadFile] = File(
        ..., description=".pptx files to merge (order is preserved)"
    ),
    filename: str | None = Query(
        None,
        description=(
            "output filename for the merged .pptx "
            "(default: {unix-epoch}-{uid}.pptx)"
        ),
    ),
):
    """Upload two or more .pptx files and receive the merged presentation.

    Files are merged in the order they appear in the multipart request.
    The response is the merged `.pptx` returned directly as a binary download.

    The optional `filename` query parameter controls the `Content-Disposition`
    filename of the returned file.  When omitted, a name in the form
    `{unix-epoch}-{uid}.pptx` is generated automatically.
    """
    if len(files) < 2:
        raise HTTPException(
            status_code=400,
            detail="at least 2 .pptx files required",
        )

    for f in files:
        if not f.filename or not f.filename.lower().endswith('.pptx'):
            raise HTTPException(
                status_code=400,
                detail=f"not a .pptx file: {f.filename}",
            )

    # resolve output filename
    if filename:
        # strip any path components and ensure .pptx extension
        out_name = Path(filename).name
        if not out_name.lower().endswith('.pptx'):
            out_name += '.pptx'
    else:
        uid = uuid.uuid4().hex[:8]
        out_name = f"{int(time.time())}-{uid}.pptx"

    tmpdir = tempfile.mkdtemp(prefix="kjandoc_api_")
    try:
        input_paths = []
        for i, f in enumerate(files):
            # prefix with index to preserve order and avoid name collisions
            safe_name = f"{i}_{Path(f.filename).name}"
            dest = os.path.join(tmpdir, safe_name)
            content = await f.read()
            with open(dest, 'wb') as out:
                out.write(content)
            input_paths.append(dest)

        out_path = os.path.join(tmpdir, out_name)
        cmd = ['kjandoc'] + input_paths + ['-o', out_path]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "kjandoc failed"
            raise HTTPException(status_code=500, detail=detail)

        return FileResponse(
            out_path,
            media_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
            filename=out_name,
            background=BackgroundTask(shutil.rmtree, tmpdir, True),
        )
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=504, detail="kjandoc timed out (10 min limit)")
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


# -- static files (demoware UI + output downloads) --

app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/", StaticFiles(directory=str(BASE_DIR), html=True), name="static")


def main():
    kjandoc_path = shutil.which('kjandoc')
    if not kjandoc_path:
        print("[!] kjandoc not found in PATH", file=sys.stderr)
        print("    install kjandoc or ensure it's available in your PATH", file=sys.stderr)
        sys.exit(1)

    print(f"[*] kjandoc demoware")
    print(f"[*] http://localhost:{PORT}")
    print(f"[*] api: POST http://localhost:{PORT}/api")
    print(f"[*] kjandoc: {kjandoc_path}")
    print(f"[*] ctrl-c to stop")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")


if __name__ == '__main__':
    main()
