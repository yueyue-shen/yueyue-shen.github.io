#!/usr/bin/env python3
"""Validate/stage this static site using Python's standard library only."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
# Complete deployment allowlist: archives and source tooling never ship.
PUBLIC_FILES = (
    "index.html", "404.html", ".nojekyll", "robots.txt", "sitemap.xml", "LICENSE",
    "google51b83618de64f97b.html",
    "assets/css/main.css", "assets/js/main.js", "assets/img/prof_pic.jpg",
    "assets/img/favicon.png", "assets/pdf/YueyueShen_CV.pdf",
    "assets/img/research/method-framework.webp", "assets/pdf/research/method-framework.pdf",
    "assets/img/research/collinder-135-cmd.png", "assets/img/research/spatial-feh.png",
    "assets/fonts/lora-latin-wght-normal.woff2", "assets/fonts/OFL-Lora.txt",
    "projects/index.html", "publications/index.html", "cv/index.html",
    *(f"projects/{number}_project/index.html" for number in range(1, 6)),
)


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.references = []
        self.errors = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                self.errors.append(f"duplicate id: {attrs['id']}")
            self.ids.add(attrs["id"])
        for key in ("src", "href"):
            if key in attrs:
                self.references.append(attrs[key])
        if tag == "img" and not attrs.get("alt"):
            self.errors.append("image missing descriptive alt text")
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            self.references.append(attrs["content"].split("url=", 1)[1])


def check(base):
    base = base.resolve()
    errors = []
    pages = {}
    for name in PUBLIC_FILES:
        path = base / name
        if not path.is_file() or path.is_symlink():
            errors.append(f"missing public file or unexpected symlink: {name}")
            continue
        if path.suffix in (".html", ".css", ".js", ".txt", ".xml"):
            text = path.read_text()
            if "{{" in text or "{%" in text or text.startswith("---\n"):
                errors.append(f"template syntax remains: {name}")
        if path.suffix == ".html":
            pages[path] = Page(text)
            errors.extend(f"{name}: {error}" for error in pages[path].errors)

    for path, page in pages.items():
        for ref in page.references:
            parts = urlsplit(ref)
            if parts.scheme or parts.netloc:
                continue
            target = path
            if parts.path:
                target = ((base / unquote(parts.path).lstrip("/")) if parts.path.startswith("/")
                          else (path.parent / unquote(parts.path))).resolve()
            if not target.is_relative_to(base):
                errors.append(f"{path.relative_to(base)}: link escapes site: {ref}")
                continue
            if target.is_dir():
                target /= "index.html"
            relative = target.relative_to(base).as_posix()
            if relative not in PUBLIC_FILES or not target.is_file():
                errors.append(f"{path.relative_to(base)}: missing/non-public target: {ref}")
            elif parts.fragment and target in pages and unquote(parts.fragment) not in pages[target].ids:
                errors.append(f"{path.relative_to(base)}: missing fragment: {ref}")

    home = base / "index.html"
    if home.is_file():
        text = home.read_text()
        if len(re.findall(r'class="project-card"', text)) != 1:
            errors.append("homepage must contain exactly one project")
        title = "Probing Young Galactic Star Clusters: Metallicities and Kinematics with LAMOST and Gaia"
        headings = [re.sub(r"<[^>]+>", "", heading)
                    for heading in re.findall(r"<h3\b[^>]*>(.*?)</h3>", text, flags=re.DOTALL)]
        if title not in headings:
            errors.append("the approved project title is missing or altered")
        required = ("intro", "about", "research", "projects", "publications", "cv", "contact")
        if not set(required).issubset(pages[home].ids):
            errors.append("a required homepage section is missing")
    pdf = base / "assets/pdf/YueyueShen_CV.pdf"
    if pdf.is_file() and not pdf.read_bytes().startswith(b"%PDF-"):
        errors.append("CV is not a PDF")
    if (base / "sitemap.xml").is_file():
        try:
            ET.parse(base / "sitemap.xml")
        except ET.ParseError as error:
            errors.append(f"invalid sitemap: {error}")
    if base != ROOT:
        actual = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file() or p.is_symlink()}
        if actual != set(PUBLIC_FILES):
            errors.append(f"unexpected deployment files: {sorted(actual - set(PUBLIC_FILES))}")
    if errors:
        raise SystemExit("Site validation failed:\n- " + "\n- ".join(errors))
    print(f"Validated {len(PUBLIC_FILES)} public files, {len(pages)} HTML pages, local links, anchors, and CV.")


def stage():
    check(ROOT)
    destination = ROOT / "_publish"
    if destination.is_symlink():
        raise SystemExit("Refusing to replace a symlink at _publish")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir()
    for name in PUBLIC_FILES:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    check(destination)
    print("Staged only public files in _publish/; no Jekyll build needed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "stage"), nargs="?", default="check")
    parser.add_argument("directory", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.command == "stage":
        stage()
    else:
        check(args.directory)
