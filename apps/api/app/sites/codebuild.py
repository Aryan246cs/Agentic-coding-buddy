"""Compile fixed-stack generated site files without running customer code.

esbuild and Tailwind only parse/transform source files. The resulting browser
bundle is displayed inside an opaque sandboxed iframe by the web client.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.config import API_ROOT

MAX_SOURCE_BYTES = 60_000
ALLOWED_IMPORTS = {"react", "react-dom", "react-dom/client", "lucide-react"}
IMPORT_RE = re.compile(r"\bfrom\s*['\"]([^'\"]+)['\"]|\bimport\s*(?:\(['\"]|['\"])([^'\"]+)")
BLOCKED_API_RE = re.compile(
    r"\bfetch\s*\(|new\s+(?:XMLHttpRequest|WebSocket|EventSource|Worker)\b"
    r"|(?:window\s*\.\s*)?(?:localStorage|sessionStorage|indexedDB)\s*\."
    r"|\beval\s*\(|new\s+Function\b|navigator\s*\.\s*(?:sendBeacon|serviceWorker)"
    r"|document\s*\.\s*cookie|window\s*\.\s*(?:open|parent|top|opener)\b",
)


class SiteBuildError(ValueError):
    pass


def build_site_files(files: dict[str, str]) -> dict[str, str]:
    """Validate source files and return source plus compiled browser assets."""
    if set(files) != {"App.tsx", "styles.css"}:
        raise SiteBuildError("A custom site needs exactly App.tsx and styles.css.")
    app_source = files["App.tsx"]
    css_source = files["styles.css"]
    if not isinstance(app_source, str) or not isinstance(css_source, str):
        raise SiteBuildError("Site source files must contain text.")
    if len(app_source.encode()) > MAX_SOURCE_BYTES or len(css_source.encode()) > MAX_SOURCE_BYTES:
        raise SiteBuildError("A source file is too large (60 KB maximum).")
    if re.search(r"\brequire\s*\(|\bimport\s*\(", app_source):
        raise SiteBuildError("Dynamic imports are disabled in custom sites.")
    if BLOCKED_API_RE.search(app_source):
        raise SiteBuildError("Network, storage, and parent-page browser APIs are disabled in the site sandbox.")
    for match in IMPORT_RE.finditer(app_source):
        package = match.group(1) or match.group(2)
        if package not in ALLOWED_IMPORTS:
            raise SiteBuildError(f"Import '{package}' is not available in the site sandbox.")
    if re.search(r"@import|url\s*\(", css_source, re.I):
        raise SiteBuildError("CSS imports and external CSS URLs are disabled.")

    web_root = API_ROOT.parent / "web"
    node = shutil.which("node")
    if not node:
        raise SiteBuildError("Node.js is not installed on this server.")
    build_path = f"{Path(node).parent}:/usr/bin:/bin"
    esbuild = web_root / "node_modules/.bin/esbuild"
    tailwind = web_root / "node_modules/.bin/tailwindcss"
    if not esbuild.exists() or not tailwind.exists():
        raise SiteBuildError("The website build tools are not installed on this server.")

    with tempfile.TemporaryDirectory(prefix="sequence-site-") as temporary:
        root = Path(temporary)
        (root / "App.tsx").write_text(app_source, encoding="utf-8")
        (root / "input.css").write_text(
            "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n" + css_source,
            encoding="utf-8",
        )
        (root / "entry.tsx").write_text(
            'import React from "react";\n'
            'import { createRoot } from "react-dom/client";\n'
            'import Site from "./App.tsx";\n'
            'createRoot(document.getElementById("root")!).render(React.createElement(Site));\n',
            encoding="utf-8",
        )
        try:
            js = subprocess.run(
                [str(esbuild), "entry.tsx", "--bundle", "--minify", "--format=iife", "--platform=browser", "--target=es2020", "--outfile=app.js"],
                cwd=root, capture_output=True, text=True, timeout=25, check=False,
                env={"PATH": build_path, "HOME": temporary, "NODE_PATH": str(web_root / "node_modules")},
            )
            if js.returncode:
                detail = (js.stderr or js.stdout)[-2500:]
                raise SiteBuildError(f"The React build needs a fix: {detail}")
            css = subprocess.run(
                [str(tailwind), "-i", "input.css", "-o", "site.css", "--content", "App.tsx", "--minify"],
                cwd=root, capture_output=True, text=True, timeout=25, check=False,
                env={"PATH": build_path, "HOME": temporary, "NODE_PATH": str(web_root / "node_modules")},
            )
            if css.returncode:
                detail = (css.stderr or css.stdout)[-2500:]
                raise SiteBuildError(f"The style build needs a fix: {detail}")
        except subprocess.TimeoutExpired as exc:
            raise SiteBuildError("The site build took too long. Try simplifying the source.") from exc
        return {
            "App.tsx": app_source,
            "styles.css": css_source,
            "app.js": (root / "app.js").read_text(encoding="utf-8"),
            "site.css": (root / "site.css").read_text(encoding="utf-8"),
        }
