"""Проверка backend: успешная загрузка, миниатюра, статика и ошибки 400."""

import io
import json
import sys
import urllib.error
import urllib.request
import uuid

from PIL import Image

BASE = "http://127.0.0.1:8000"


def png_bytes(size=(1200, 600), color=(90, 140, 255)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def post_file(name, content_type, data):
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request(
        f"{BASE}/api/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def check(label, condition, extra=""):
    print(("PASS  " if condition else "FAIL  ") + label + (f"  -> {extra}" if extra else ""))
    if not condition:
        sys.exit(1)


status, payload = post_file("test.png", "image/png", png_bytes())
check("upload PNG -> 200", status == 200, status)
check("full original URL", payload["original_url"].startswith("http://"), payload.get("original_url"))
check("full thumbnail URL", payload["thumbnail_url"].startswith("http://"), payload.get("thumbnail_url"))

with urllib.request.urlopen(payload["original_url"]) as response:
    check("original served by StaticFiles", response.status == 200)

with urllib.request.urlopen(payload["thumbnail_url"]) as response:
    thumb_data = response.read()
    check("thumbnail served by StaticFiles", response.status == 200)

thumb = Image.open(io.BytesIO(thumb_data))
check(
    "thumbnail keeps aspect ratio",
    abs(thumb.width / thumb.height - 2.0) < 0.02,
    f"{thumb.width}x{thumb.height}",
)
check("thumbnail is smaller", max(thumb.size) <= 320, thumb.size)

status, payload = post_file("test.txt", "text/plain", b"not an image")
check("wrong mime -> 400", status == 400, payload)
print("     detail:", payload.get("detail"))

big = png_bytes((3000, 3000))
big += b"\0" * (6 * 1024 * 1024)
status, payload = post_file("big.png", "image/png", big)
check(">5MB -> 400", status == 400, payload)
print("     detail:", payload.get("detail"))

status, payload = post_file("fake.png", "image/png", b"definitely not a png")
check("broken image -> 400", status == 400, payload)
print("     detail:", payload.get("detail"))

with urllib.request.urlopen(f"{BASE}/api/images") as response:
    items = json.loads(response.read())
check("history endpoint lists uploads", any(i["id"] == payload.get("id") for i in items) or len(items) > 0, len(items))

print("\nAll backend checks passed.")
