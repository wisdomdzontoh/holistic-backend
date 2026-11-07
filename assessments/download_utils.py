"""Helpers for file-download responses."""
import re
import unicodedata
from datetime import datetime
from urllib.parse import quote

_ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]')


def assessment_export_filename(org_unit_name, when=None, extension='xlsx'):
    """
    The naming convention for exported assessments: "<Org unit name>_<dd_mm_yyyy>.<ext>",
    e.g. "Adabraka Polyclinic_05_08_2026.xlsx". Keeps the name human-readable
    (spaces intact) and only strips characters that are illegal in filenames.
    """
    name = _ILLEGAL_FILENAME_CHARS.sub('_', (org_unit_name or '').strip()).strip(' ._') or 'Assessment'
    date_part = (when or datetime.now()).strftime('%d_%m_%Y')
    return f"{name}_{date_part}.{extension}"


def content_disposition_attachment(filename):
    """
    Content-Disposition value that survives non-ASCII org unit names: an ASCII
    fallback in `filename` plus the exact UTF-8 name in `filename*` (RFC 6266/5987),
    which every current browser prefers.
    """
    ascii_name = (
        unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
        .replace('"', '').replace('\\', '')
    ) or 'download'
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename, safe='')}"
