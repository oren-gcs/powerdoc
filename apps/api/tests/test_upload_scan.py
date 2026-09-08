"""Unit tests for defensive form upload scanning."""

from app.engine.upload_scan import scan_upload


PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_clean_png_image():
    r = scan_upload(PNG_1X1, "photo.png", "image/png", kind="images")
    assert r["ok"] is True
    assert r["status"] == "clean"
    assert r["sniffed_mime"] == "image/png"


def test_reject_exe_extension():
    r = scan_upload(b"MZ" + b"\x00" * 64, "malware.exe", "application/octet-stream", kind="file")
    assert r["ok"] is False
    assert "disallowed" in r["reason"] or "executable" in r["reason"]


def test_reject_html_as_text():
    data = b"<!DOCTYPE html><html><script>alert(1)</script></html>"
    r = scan_upload(data, "note.txt", "text/plain", kind="file")
    assert r["ok"] is False


def test_reject_svg_image_kind():
    data = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><script/></svg>'
    r = scan_upload(data, "pic.svg", "image/svg+xml", kind="images")
    assert r["ok"] is False


def test_reject_empty():
    r = scan_upload(b"", "empty.png", "image/png", kind="images")
    assert r["ok"] is False
    assert "empty" in r["reason"]


def test_reject_pdf_with_javascript():
    data = b"%PDF-1.4\n1 0 obj\n<< /JavaScript 2 0 R >>\nendobj\n"
    r = scan_upload(data, "doc.pdf", "application/pdf", kind="file")
    assert r["ok"] is False
    assert "pdf" in r["reason"].lower() or "javascript" in r["reason"].lower()


def test_clean_plain_text():
    data = b"Invoice INV-1\nAmount: 10.00\n"
    r = scan_upload(data, "inv.txt", "text/plain", kind="file")
    assert r["ok"] is True
    assert r["sniffed_mime"] == "text/plain"


def test_reject_content_type_mismatch():
    r = scan_upload(PNG_1X1, "photo.png", "application/pdf", kind="images")
    assert r["ok"] is False
    assert "mismatch" in r["reason"]
