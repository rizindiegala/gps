#!/usr/bin/env python3
"""Updater a doppio clic per GPS (Windows e macOS)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable

REPOSITORY = "rizindiegala/gps"
BRANCH = "main"
API_COMMIT_URL = f"https://api.github.com/repos/{REPOSITORY}/commits/{BRANCH}"
ARCHIVE_URL = f"https://codeload.github.com/{REPOSITORY}/zip/refs/heads/{BRANCH}"
STATE_FILENAME = ".gps-update-state.json"
APP_PORT = 2000
REQUIRED_FILES = {"app.py", "requirements.txt", ".env.example"}
PROTECTED_PREFIXES = (
    ".env",
    ".git",
    ".svn",
    STATE_FILENAME,
    "env",
    "venv",
    ".venv",
    "exports",
    "data_file/data.json",
    "endpoints/chrome_driver",
    "cookies.json",
    "debug.log",
    "__pycache__",
    "aggiorna gps.exe",
    "aggiorna gps.app",
    "aggiorna-gps-windows.exe",
)

LogCallback = Callable[[str], None]


class UpdateError(RuntimeError):
    """Errore previsto e presentabile all'utente."""


def _normalized(relative_path: str | Path) -> str:
    return PurePosixPath(str(relative_path).replace("\\", "/")).as_posix().lstrip("./").lower()


def is_protected(relative_path: str | Path) -> bool:
    path = _normalized(relative_path)
    for prefix in PROTECTED_PREFIXES:
        protected = _normalized(prefix)
        if path == protected or path.startswith(protected + "/"):
            return True
    return path.endswith(".log") or "/__pycache__/" in f"/{path}/" or path.endswith((".pyc", ".pyo"))


def find_app_dir(explicit: str | None = None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if (candidate / "app.py").is_file():
            return candidate
        raise UpdateError(f"La cartella indicata non contiene app.py: {candidate}")

    starts = [Path.cwd(), Path(sys.executable).resolve(), Path(__file__).resolve()]
    checked: set[Path] = set()
    for start in starts:
        current = start if start.is_dir() else start.parent
        for candidate in (current, *current.parents):
            if candidate in checked:
                continue
            checked.add(candidate)
            if (candidate / "app.py").is_file() and (candidate / "requirements.txt").is_file():
                return candidate
    raise UpdateError(
        "Cartella dell'app non trovata. Copia l'updater nella cartella che contiene app.py."
    )


def app_is_running(port: int = APP_PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.25)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def _request_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "GPS-Updater/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise UpdateError(f"Impossibile contattare GitHub: {exc}") from exc


def latest_commit_sha() -> str:
    data = _request_json(API_COMMIT_URL)
    sha = data.get("sha")
    if not isinstance(sha, str) or len(sha) < 7:
        raise UpdateError("GitHub non ha restituito una versione valida.")
    return sha


def download_archive(destination: Path) -> None:
    request = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "GPS-Updater/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UpdateError(f"Download dell'aggiornamento non riuscito: {exc}") from exc


def extract_archive(archive: Path, destination: Path) -> Path:
    try:
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            roots = {
                PurePosixPath(member.filename).parts[0]
                for member in members
                if PurePosixPath(member.filename).parts
            }
            if len(roots) != 1:
                raise UpdateError("Il pacchetto GitHub ha una struttura inattesa.")
            root_name = next(iter(roots))
            for member in members:
                member_path = PurePosixPath(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise UpdateError("Il pacchetto contiene un percorso non sicuro.")
            bundle.extractall(destination)
    except (zipfile.BadZipFile, OSError) as exc:
        raise UpdateError(f"Pacchetto di aggiornamento non valido: {exc}") from exc

    source = destination / root_name
    missing = sorted(name for name in REQUIRED_FILES if not (source / name).is_file())
    if missing:
        raise UpdateError("Nel pacchetto mancano file obbligatori: " + ", ".join(missing))
    return source


def collect_managed_files(source: Path) -> list[str]:
    files: list[str] = []
    for item in source.rglob("*"):
        if item.is_file():
            relative = item.relative_to(source).as_posix()
            if not is_protected(relative):
                files.append(relative)
    return sorted(files)


def load_state(app_dir: Path) -> dict:
    state_path = app_dir / STATE_FILENAME
    if not state_path.is_file():
        return {"sha": "", "managed_files": []}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("managed_files", []), list):
            raise ValueError("formato errato")
        return data
    except (OSError, ValueError, json.JSONDecodeError):
        return {"sha": "", "managed_files": []}


def save_state(app_dir: Path, sha: str, managed_files: Iterable[str]) -> None:
    state_path = app_dir / STATE_FILENAME
    temporary = state_path.with_suffix(".tmp")
    payload = {"sha": sha, "managed_files": sorted(managed_files)}
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, state_path)


def _remove_empty_parents(path: Path, root: Path) -> None:
    parent = path.parent
    while parent != root and parent.is_dir():
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def synchronize_files(
    source: Path,
    app_dir: Path,
    new_files: list[str],
    old_files: Iterable[str],
    operation_hook: Callable[[str, str], None] | None = None,
) -> None:
    """Sincronizza i file e ripristina lo stato precedente in caso di errore."""
    old_set = {item for item in old_files if not is_protected(item)}
    new_set = set(new_files)
    affected = sorted(old_set | new_set)

    with tempfile.TemporaryDirectory(prefix="gps-backup-") as backup_name:
        backup = Path(backup_name)
        existed: set[str] = set()
        for relative in affected:
            destination = app_dir / relative
            if destination.is_file():
                backup_file = backup / relative
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup_file)
                existed.add(relative)

        try:
            for relative in sorted(old_set - new_set):
                destination = app_dir / relative
                if destination.is_file():
                    destination.unlink()
                    _remove_empty_parents(destination, app_dir)
                if operation_hook:
                    operation_hook("remove", relative)

            for relative in new_files:
                source_file = source / relative
                destination = app_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, destination)
                if operation_hook:
                    operation_hook("copy", relative)
        except Exception:
            for relative in new_set - existed:
                destination = app_dir / relative
                if destination.is_file():
                    destination.unlink()
                    _remove_empty_parents(destination, app_dir)
            for relative in existed:
                backup_file = backup / relative
                destination = app_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, destination)
            raise


def _venv_python(app_dir: Path) -> Path | None:
    candidates = (
        app_dir / "env" / "Scripts" / "python.exe",
        app_dir / "env" / "bin" / "python3",
        app_dir / "env" / "bin" / "python",
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def ensure_python_environment(app_dir: Path, log: LogCallback) -> Path:
    existing = _venv_python(app_dir)
    if existing:
        return existing

    bootstrap = next(
        (path for command in ("python3", "python", "py") if (path := shutil.which(command))),
        None,
    )
    if not bootstrap:
        raise UpdateError(
            "Python non è installato e la cartella env non esiste. Installa Python 3 e riprova."
        )
    log("Creo l'ambiente Python locale...")
    result = subprocess.run(
        [bootstrap, "-m", "venv", str(app_dir / "env")],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode:
        raise UpdateError("Creazione dell'ambiente Python fallita:\n" + (result.stderr or result.stdout))
    python = _venv_python(app_dir)
    if not python:
        raise UpdateError("L'ambiente Python è stato creato, ma il suo interprete non è disponibile.")
    return python


def install_dependencies(python: Path, requirements: Path, log: LogCallback) -> None:
    log("Aggiorno le dipendenze Python...")
    # Un pip vecchio non sa installare i pacchetti pubblicati solo come wheel
    # recenti: se l'aggiornamento non riesce si prosegue comunque.
    try:
        subprocess.run(
            [str(python), "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        result = subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(requirements)],
            capture_output=True,
            text=True,
            timeout=900,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(f"Installazione dipendenze non riuscita: {exc}") from exc
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        raise UpdateError("Installazione dipendenze fallita:\n" + details[-3000:])


BROWSER_WARMUP = (
    "from selenium import webdriver\n"
    "options = webdriver.ChromeOptions()\n"
    "options.add_argument('--headless=new')\n"
    "driver = webdriver.Chrome(options=options)\n"
    "driver.quit()\n"
)


def prepare_browser(python: Path, log: LogCallback) -> None:
    """Procura in anticipo driver e browser, così la prima ricerca non attende.

    Selenium scarica da sé chromedriver e Chrome for Testing quando non sono
    installati: farlo ora evita che l'utente aspetti senza spiegazioni al primo
    utilizzo. Se non riesce non è un errore: verrà ritentato alla prima ricerca.
    """
    log("Preparo il browser per le ricerche...")
    try:
        result = subprocess.run(
            [str(python), "-c", BROWSER_WARMUP],
            capture_output=True,
            text=True,
            timeout=900,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"Browser non preparato ({exc}). Verrà scaricato alla prima ricerca.")
        return
    if result.returncode:
        log("Browser non preparato. Verrà scaricato alla prima ricerca.")
        return
    log("Browser pronto.")


def validate_python_sources(python: Path, source: Path) -> None:
    result = subprocess.run(
        [str(python), "-m", "compileall", "-q", str(source)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode:
        raise UpdateError("Il nuovo codice Python non è valido:\n" + (result.stderr or result.stdout))


def perform_update(app_dir: Path, log: LogCallback = print, force: bool = False) -> str:
    if app_is_running():
        raise UpdateError("GPS è aperto. Chiudilo, poi avvia nuovamente l'updater.")

    log("Controllo l'ultima versione online...")
    sha = latest_commit_sha()
    state = load_state(app_dir)
    if not force and state.get("sha") == sha:
        log("GPS è già aggiornato.")
        return "up-to-date"

    with tempfile.TemporaryDirectory(prefix="gps-update-") as temporary_name:
        temporary = Path(temporary_name)
        archive = temporary / "update.zip"
        log("Scarico l'aggiornamento...")
        download_archive(archive)
        log("Verifico il pacchetto...")
        source = extract_archive(archive, temporary / "extracted")
        new_files = collect_managed_files(source)

        python = ensure_python_environment(app_dir, log)
        validate_python_sources(python, source)
        install_dependencies(python, source / "requirements.txt", log)

        log("Installo i nuovi file...")
        try:
            synchronize_files(source, app_dir, new_files, state.get("managed_files", []))
            save_state(app_dir, sha, new_files)
        except (OSError, shutil.Error) as exc:
            raise UpdateError(f"Aggiornamento annullato; i file precedenti sono stati ripristinati: {exc}") from exc

        prepare_browser(python, log)

    log(f"Aggiornamento completato ({sha[:7]}).")
    return "updated"


def run_gui(app_dir: Path) -> int:
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title("Aggiorna GPS")
    root.geometry("520x300")
    root.resizable(False, False)

    title = ttk.Label(root, text="Aggiornamento GPS", font=("", 16, "bold"))
    title.pack(pady=(20, 8))
    location = ttk.Label(root, text=str(app_dir), wraplength=470)
    location.pack(pady=(0, 12))
    progress = ttk.Progressbar(root, mode="indeterminate", length=460)
    progress.pack(pady=6)
    output = tk.Text(root, height=8, width=62, state="disabled", wrap="word")
    output.pack(padx=20, pady=10)
    close_button = ttk.Button(root, text="Chiudi", command=root.destroy, state="disabled")
    close_button.pack()

    def write_log(message: str) -> None:
        def append() -> None:
            output.configure(state="normal")
            output.insert("end", message.rstrip() + "\n")
            output.see("end")
            output.configure(state="disabled")

        root.after(0, append)

    def worker() -> None:
        try:
            result = perform_update(app_dir, write_log)
            if result == "updated":
                root.after(0, lambda: messagebox.showinfo("Aggiorna GPS", "Aggiornamento completato."))
        except Exception as exc:
            write_log(f"ERRORE: {exc}")
            root.after(0, lambda: messagebox.showerror("Aggiorna GPS", str(exc)))
        finally:
            root.after(0, progress.stop)
            root.after(0, lambda: close_button.configure(state="normal"))

    progress.start(12)
    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggiorna GPS dall'ultima versione GitHub.")
    parser.add_argument("--app-dir", help="Cartella dell'app da aggiornare")
    parser.add_argument("--force", action="store_true", help="Reinstalla anche la versione corrente")
    parser.add_argument("--console", action="store_true", help="Usa il terminale invece della finestra")
    parser.add_argument("--version", action="store_true", help="Mostra la versione dell'updater")
    args = parser.parse_args(argv)
    if args.version:
        print("GPS Updater 1.0")
        return 0

    try:
        app_dir = find_app_dir(args.app_dir)
        if args.console:
            perform_update(app_dir, print, args.force)
            return 0
        return run_gui(app_dir)
    except Exception as exc:
        if args.console:
            print(f"ERRORE: {exc}", file=sys.stderr)
        else:
            try:
                from tkinter import messagebox

                messagebox.showerror("Aggiorna GPS", str(exc))
            except Exception:
                print(f"ERRORE: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
