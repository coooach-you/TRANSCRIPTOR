"""
Kam Transcriptor ukládá přepisy.

- LocalStorage: složka na počítači (třeba synchronizovaná složka Google Disku). Verze pro PC.
- DriveStorage: složka na Google Disku přes Google Drive API. Webová verze.

Obě ukládají stejnou strukturu, takže web i PC vidí stejné přepisy:
    <složka>/<přepis>/data.json, prepis.txt, prepis.docx, shrnuti_*.md ...
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
TOKEN_URI = "https://oauth2.googleapis.com/token"
FOLDER_MIME = "application/vnd.google-apps.folder"
SETTINGS_FILE = "nastaveni.json"


class LocalStorage:
    """Přepisy ve složce na disku počítače."""

    slow = False

    def __init__(self, root: Path):
        self.root = Path(root)

    def describe(self) -> str:
        return str(self.root)

    def list_jobs(self, marker: str = "data.json") -> list[str]:
        try:
            return sorted((p.name for p in self.root.iterdir() if (p / marker).exists()), reverse=True)
        except OSError:
            return []

    def read(self, job: str, name: str) -> bytes | None:
        try:
            return (self.root / job / name).read_bytes()
        except OSError:
            return None

    def mtime(self, job: str, name: str = "data.json") -> float | None:
        try:
            return (self.root / job / name).stat().st_mtime
        except OSError:
            return None

    def write_many(self, job: str, files: dict[str, bytes]) -> dict[str, float]:
        d = self.root / job
        d.mkdir(parents=True, exist_ok=True)
        out = {}
        for name, data in files.items():
            # zapisujeme najednou, aby Google Disk nikdy nesynchronizoval rozepsanou verzi
            path = d / name
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, path)
            out[name] = path.stat().st_mtime
        return out

    def delete(self, job: str, names: list[str]):
        for name in names:
            (self.root / job / name).unlink(missing_ok=True)


class DriveStorage:
    """Přepisy ve složce na Google Disku (přes Drive API, s trvalým povolením = refresh token)."""

    slow = True
    API = "https://www.googleapis.com/drive/v3/files"
    UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"

    def __init__(self, folder_name: str, client_id: str, client_secret: str, refresh_token: str):
        from google.oauth2.credentials import Credentials

        self.folder_name = folder_name
        self.creds = Credentials(None, refresh_token=refresh_token, client_id=client_id,
                                 client_secret=client_secret, token_uri=TOKEN_URI, scopes=[DRIVE_SCOPE])
        self._local = threading.local()
        self._lock = threading.Lock()
        self._root_id: str | None = None
        self._job_ids: dict[str, str] = {}

    # --- HTTP ----------------------------------------------------------------------------

    def _session(self):
        from google.auth.transport.requests import AuthorizedSession, Request

        with self._lock:  # obnovení přístupového tokenu jen v jednom vlákně
            if not self.creds.valid:
                self.creds.refresh(Request())
        if not hasattr(self._local, "s"):
            self._local.s = AuthorizedSession(self.creds)
        return self._local.s

    def _call(self, method: str, url: str, **kw):
        for attempt in range(4):
            r = self._session().request(method, url, timeout=120, **kw)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(1.5 * 2 ** attempt)
                continue
            if r.status_code >= 400:
                if "invalid_grant" in r.text:
                    raise RuntimeError("Povolení pro Google Disk vypršelo. Připojte Disk znovu (viz návod).")
                raise RuntimeError(f"Google Disk hlásí chybu {r.status_code}: {r.text[:300]}")
            return r
        raise RuntimeError("Google Disk neodpovídá.")

    def _list(self, q: str, fields: str = "id,name,modifiedTime,parents") -> list[dict]:
        out, token = [], None
        while True:
            params = {"q": q, "fields": f"nextPageToken,files({fields})", "pageSize": 1000,
                      "orderBy": "modifiedTime desc", "spaces": "drive"}
            if token:
                params["pageToken"] = token
            data = self._call("GET", self.API, params=params).json()
            out += data.get("files", [])
            token = data.get("nextPageToken")
            if not token:
                return out

    @staticmethod
    def _q(text: str) -> str:
        return text.replace("\\", "\\\\").replace("'", "\\'")

    def _create_folder(self, name: str, parent: str) -> str:
        meta = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent]}
        return self._call("POST", self.API, json=meta, params={"fields": "id"}).json()["id"]

    # --- složky --------------------------------------------------------------------------

    def root_id(self) -> str:
        if not self._root_id:
            found = self._list(f"name = '{self._q(self.folder_name)}' and mimeType = '{FOLDER_MIME}' "
                               "and 'root' in parents and trashed = false")
            self._root_id = found[0]["id"] if found else self._create_folder(self.folder_name, "root")
        return self._root_id

    def _job_folders(self) -> dict[str, str]:
        folders = self._list(f"'{self.root_id()}' in parents and mimeType = '{FOLDER_MIME}' "
                             "and trashed = false")
        self._job_ids = {}
        for f in reversed(folders):  # při shodě jmen vyhraje naposledy změněná složka
            self._job_ids[f["name"]] = f["id"]
        return self._job_ids

    def _job_id(self, job: str, create: bool = False) -> str | None:
        if job not in self._job_ids:
            self._job_folders()
        if job not in self._job_ids and create:
            self._job_ids[job] = self._create_folder(job, self.root_id())
        return self._job_ids.get(job)

    def _files(self, job: str) -> dict[str, dict]:
        fid = self._job_id(job)
        if not fid:
            return {}
        files = self._list(f"'{fid}' in parents and trashed = false")
        out = {}
        for f in files:  # seřazeno od nejnovějšího, při duplicitě bereme nejnovější
            out.setdefault(f["name"], f)
        return out

    # --- rozhraní stejné jako LocalStorage --------------------------------------------------

    def describe(self) -> str:
        return f"Google Disk › {self.folder_name}"

    def list_jobs(self, marker: str = "data.json") -> list[str]:
        folders = self._job_folders()
        by_id = {v: k for k, v in folders.items()}
        hits = self._list(f"name = '{self._q(marker)}' and trashed = false", "id,parents")
        jobs = {by_id[p] for f in hits for p in f.get("parents", []) if p in by_id}
        return sorted(jobs, reverse=True)

    def read(self, job: str, name: str) -> bytes | None:
        f = self._files(job).get(name)
        if not f:
            return None
        return self._call("GET", f"{self.API}/{f['id']}", params={"alt": "media"}).content

    def mtime(self, job: str, name: str = "data.json") -> float | None:
        f = self._files(job).get(name)
        return _parse_time(f["modifiedTime"]) if f else None

    def _upload(self, parent: str, existing: dict | None, name: str, data: bytes) -> float:
        params = {"fields": "id,modifiedTime"}
        if existing:
            r = self._call("PATCH", f"{self.UPLOAD}/{existing['id']}",
                           params={**params, "uploadType": "media"}, data=data,
                           headers={"Content-Type": "application/octet-stream"})
        else:
            boundary = uuid.uuid4().hex
            meta = json.dumps({"name": name, "parents": [parent]}).encode("utf-8")
            body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode()
                    + meta + f"\r\n--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n".encode()
                    + data + f"\r\n--{boundary}--".encode())
            r = self._call("POST", self.UPLOAD, params={**params, "uploadType": "multipart"}, data=body,
                           headers={"Content-Type": f"multipart/related; boundary={boundary}"})
        return _parse_time(r.json()["modifiedTime"])

    def write_many(self, job: str, files: dict[str, bytes]) -> dict[str, float]:
        parent = self._job_id(job, create=True)
        existing = self._files(job)
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {name: pool.submit(self._upload, parent, existing.get(name), name, data)
                       for name, data in files.items()}
            return {name: fut.result() for name, fut in futures.items()}

    def delete(self, job: str, names: list[str]):
        files = self._files(job)
        for name in names:
            if name in files:  # do koše, ne natrvalo
                self._call("PATCH", f"{self.API}/{files[name]['id']}", json={"trashed": True})

    # --- nastavení (třeba uspořádání přepisu) --------------------------------------------

    def get_settings(self) -> dict:
        found = self._list(f"name = '{SETTINGS_FILE}' and '{self.root_id()}' in parents "
                           "and trashed = false")
        if not found:
            return {}
        try:
            return json.loads(self._call("GET", f"{self.API}/{found[0]['id']}",
                                         params={"alt": "media"}).content)
        except ValueError:
            return {}

    def set_settings(self, values: dict):
        found = self._list(f"name = '{SETTINGS_FILE}' and '{self.root_id()}' in parents "
                           "and trashed = false")
        data = {**self.get_settings(), **values}
        self._upload(self.root_id(), found[0] if found else None, SETTINGS_FILE,
                     json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))


def _parse_time(text: str) -> float:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


# --- jednorázové připojení Google Disku (získání trvalého povolení) ---------------------------


def drive_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    from urllib.parse import urlencode

    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": DRIVE_SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
    })


def drive_exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> str:
    import requests

    r = requests.post(TOKEN_URI, timeout=30, data={
        "client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri,
        "code": code, "grant_type": "authorization_code",
    })
    data = r.json()
    if r.status_code >= 400 or "refresh_token" not in data:
        raise RuntimeError(f"Google povolení nevydal: {data.get('error_description') or data}")
    return data["refresh_token"]
