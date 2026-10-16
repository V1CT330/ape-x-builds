#!/usr/bin/env python3
"""Fetch a site's favicon and convert it into Android launcher icon assets.

Network failures are non-fatal: the generated generic Ape X icon remains in place.
Only HTTPS icon URLs on the website's configured allowed hosts are accepted.
"""
import io
import json
import sys
import urllib.error
import urllib.request
import xml.sax.saxutils
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
import ipaddress
import socket

from PIL import Image, ImageOps


MAX_PAGE_BYTES = 1_000_000
MAX_ICON_BYTES = 4_000_000
TIMEOUT_SECONDS = 12


class IconLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.icons = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "link":
            return
        values = {k.lower(): (v or "") for k, v in attrs}
        rel = {x.lower() for x in values.get("rel", "").split()}
        if rel.intersection({"icon", "shortcut", "apple-touch-icon", "apple-touch-icon-precomposed"}):
            href = values.get("href", "").strip()
            if href:
                self.icons.append(href)


def allowed_host(host, hosts):
    if not host:
        return False
    host = host.lower().rstrip(".")
    return any(host == h or host.endswith("." + h) for h in hosts)


def validate_url(url, hosts):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("icon URL must be an HTTPS URL without embedded credentials")
    host = parsed.hostname.lower().rstrip(".")
    if not allowed_host(host, hosts):
        raise ValueError("icon URL host is not in the website allowlist")
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal", ".test")):
        raise ValueError("local and internal hosts are not allowed for icon downloads")
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            raise ValueError("private or reserved IP addresses are not allowed for icon downloads")
        return url
    except ValueError as exc:
        if "not allowed" in str(exc):
            raise
        # For DNS names, reject any private/reserved address returned by DNS.
    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError(f"icon host could not be resolved: {host}") from exc
    if not addresses or any(not ipaddress.ip_address(item[4][0].split("%")[0]).is_global for item in addresses):
        raise ValueError("icon host resolves to a private or reserved IP address")
    return url


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        super().__init__()
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Validate the redirect target before urllib issues a request to it.
        validate_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, hosts, limit):
    validate_url(url, hosts)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ApeX-IconFetcher/1.0", "Accept": "text/html,image/*,*/*;q=0.5"},
    )
    opener = urllib.request.build_opener(SafeRedirectHandler(hosts))
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        final_url = response.geturl()
        validate_url(final_url, hosts)
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("response exceeds size limit")
        return data, response.headers.get("Content-Type", "").lower()


def icon_candidates(page_url, html, hosts):
    parser = IconLinkParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    candidates = []
    for href in parser.icons:
        candidate = urljoin(page_url, href)
        try:
            validate_url(candidate, hosts)
        except ValueError:
            continue
        if candidate not in candidates:
            candidates.append(candidate)
    fallback = urljoin(page_url, "/favicon.ico")
    try:
        validate_url(fallback, hosts)
        if fallback not in candidates:
            candidates.append(fallback)
    except ValueError:
        pass
    return candidates


def save_icons(icon_bytes, out):
    image = Image.open(io.BytesIO(icon_bytes)).convert("RGBA")
    if image.width < 1 or image.height < 1 or image.width > 4096 or image.height > 4096:
        raise ValueError("icon dimensions are invalid")
    # Preserve transparent edges and centre the logo on a square transparent canvas.
    square = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    contained = ImageOps.contain(image, (400, 400), method=Image.Resampling.LANCZOS)
    square.alpha_composite(contained, ((512 - contained.width) // 2, (512 - contained.height) // 2))
    png = out / "app/src/main/res/drawable-nodpi/ic_site_logo.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    square.save(png, format="PNG", optimize=True)

    for density, size in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)):
        folder = out / f"app/src/main/res/mipmap-{density}"
        folder.mkdir(parents=True, exist_ok=True)
        square.resize((size, size), Image.Resampling.LANCZOS).save(folder / "ic_launcher.png", format="PNG", optimize=True)

    adaptive = out / "app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml"
    adaptive.parent.mkdir(parents=True, exist_ok=True)
    adaptive.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">'
        '<background android:drawable="@drawable/ic_fg"/>'
        '<foreground android:drawable="@drawable/ic_site_logo"/>'
        '</adaptive-icon>\n',
        encoding="utf-8",
    )
    legacy = out / "app/src/main/res/mipmap/ic_launcher.xml"
    if legacy.exists():
        legacy.unlink()


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: fetch_site_icon.py spec.json GENERATED_ANDROID_DIR")
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    web = spec.get("webview") or {}
    app = spec.get("application") or {}
    start_url = web.get("startUrl") or ""
    start = urlparse(start_url)
    if start.scheme != "https" or not start.hostname:
        print("::warning::Cannot fetch site icon: startUrl is not HTTPS")
        return 0

    hosts = [str(h).strip().lower().rstrip(".") for h in (web.get("allowedHosts") or []) if str(h).strip()]
    if not hosts:
        hosts = [start.hostname.lower().rstrip(".")]
    if not allowed_host(start.hostname, hosts):
        hosts.append(start.hostname.lower().rstrip("."))

    try:
        explicit = (app.get("iconUrl") or "").strip()
        if explicit:
            candidates = [urljoin(start_url, explicit)]
        else:
            page_bytes, _ = fetch(start_url, hosts, MAX_PAGE_BYTES)
            candidates = icon_candidates(start_url, page_bytes, hosts)

        last_error = None
        for candidate in candidates:
            try:
                icon_bytes, _ = fetch(candidate, hosts, MAX_ICON_BYTES)
                save_icons(icon_bytes, Path(sys.argv[2]))
                print(f"Using website launcher icon from {urlparse(candidate).hostname}")
                return 0
            except Exception as exc:
                last_error = exc
        if last_error:
            print(f"::warning::Website icon could not be loaded; using the fallback icon ({last_error})")
        else:
            print("::warning::No usable website icon found; using the fallback icon")
    except Exception as exc:
        print(f"::warning::Website icon fetch failed; using the fallback icon ({exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
