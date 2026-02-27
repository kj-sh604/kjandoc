#!/usr/bin/env python3

# kjandoc demoware server
# a tiny threaded http server for the web interface.
#
# usage: python server.py [port]
# default port: 8080

import os
import sys
import json
import uuid
import time
import shutil
import threading
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from urllib.parse import unquote


PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'output'

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# {job_id: {status, command, output, log}}
jobs = {}
jobs_lock = threading.Lock()


class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class Handler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    # -- routing --

    def do_POST(self):
        if self.path == '/api/upload':
            self._upload()
        elif self.path == '/api/merge':
            self._merge()
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path.startswith('/api/status/'):
            self._status()
        else:
            super().do_GET()

    # -- helpers --

    def _json(self, code, data):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- handlers --

    def _upload(self):
        job_id = self.headers.get('X-Job-Id', '')
        raw_name = self.headers.get('X-Filename', '')
        length = int(self.headers.get('Content-Length', 0))

        if not job_id or not raw_name:
            return self._json(400, {"error": "missing headers"})
        if length <= 0:
            return self._json(400, {"error": "empty file"})

        name = Path(unquote(raw_name)).name
        if not name.lower().endswith('.pptx'):
            return self._json(400, {"error": "not a .pptx file"})

        job_dir = UPLOAD_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        dest = job_dir / name

        with open(dest, 'wb') as f:
            left = length
            while left > 0:
                chunk = self.rfile.read(min(left, 65536))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)

        self._json(200, {"ok": True, "file": name})

    def _merge(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return self._json(400, {"error": "bad json"})

        job_id = data.get('job_id', '')
        files = data.get('files', [])

        if not job_id or not files:
            return self._json(400, {"error": "missing job_id or files"})

        job_dir = UPLOAD_DIR / job_id
        if not job_dir.exists():
            return self._json(400, {"error": "upload dir not found — did you upload first?"})

        mode = data.get('mode', 'render')
        if mode not in ('render', 'same-template'):
            return self._json(400, {"error": f"invalid mode: {mode}"})

        # validate filenames (no path traversal)
        for f in files:
            if '/' in f or '\\' in f or '..' in f:
                return self._json(400, {"error": f"bad filename: {f}"})
            if not (job_dir / f).exists():
                return self._json(400, {"error": f"not found: {f}"})

        # pick the right binary
        binary = 'kjandoc-st' if mode == 'same-template' else 'kjandoc'

        if not shutil.which(binary):
            return self._json(500, {"error": f"{binary} not found in PATH"})

        # output: epoch_shortid.pptx
        epoch = int(time.time())
        uid = uuid.uuid4().hex[:8]
        out_name = f"{epoch}_{uid}.pptx"
        out_path = OUTPUT_DIR / out_name

        # build the real command
        inputs = [str(job_dir / f) for f in files]
        cmd = [binary] + inputs + ['-o', str(out_path)]

        # pretty command for display (strip numeric id prefixes like "3_")
        pretty_names = []
        for f in files:
            parts = f.split('_', 1)
            pretty_names.append(parts[1] if len(parts) == 2 and parts[0].isdigit() else f)
        cmd_str = f"{binary} {' '.join(pretty_names)} -o output/{out_name}"

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

        self._json(200, {
            "ok": True,
            "job_id": job_id,
            "command": cmd_str,
            "output": out_name,
        })

    def _status(self):
        job_id = self.path.rsplit('/', 1)[-1]
        with jobs_lock:
            job = jobs.get(job_id)
            snapshot = dict(job) if job else None
        if not snapshot:
            return self._json(404, {"error": "unknown job"})
        self._json(200, snapshot)


def main():
    kjandoc_path = shutil.which('kjandoc')
    if not kjandoc_path:
        print(f"[!] kjandoc not found in PATH", file=sys.stderr)
        print(f"    install kjandoc or ensure it's available in your PATH", file=sys.stderr)
        sys.exit(1)

    st_path = shutil.which('kjandoc-st')

    srv = ThreadedServer(('', PORT), Handler)
    print(f"[*] kjandoc demoware")
    print(f"[*] http://localhost:{PORT}")
    print(f"[*] kjandoc: {kjandoc_path}")
    if st_path:
        print(f"[*] kjandoc-st: {st_path}")
    else:
        print(f"[!] kjandoc-st not found (same-template mode unavailable)")
    print(f"[*] ctrl-c to stop")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] bye")
        srv.shutdown()


if __name__ == '__main__':
    main()
