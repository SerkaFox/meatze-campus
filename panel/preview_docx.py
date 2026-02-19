# panel/preview_docx.py
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

LO_BIN = "soffice"

def ensure_docx_preview_pdf(src_abs_path: str, preview_abs_path: str) -> str:
    src = Path(src_abs_path)
    out = Path(preview_abs_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # cache
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return str(out)

    with tempfile.TemporaryDirectory(prefix="mz_docx2pdf_") as tmpdir:
        tmp = Path(tmpdir)
        cmd = [
            LO_BIN,
            "--headless", "--nologo", "--nofirststartwizard",
            "--convert-to", "pdf",
            "--outdir", str(tmp),
            str(src),
        ]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"docx->pdf failed: {p.stderr[:500]}")

        # LibreOffice может назвать pdf не как src.stem + ".pdf"
        pdfs = list(tmp.glob("*.pdf"))
        if not pdfs:
            # полезная диагностика: покажем что LO написал
            raise RuntimeError(
                "LibreOffice did not produce PDF. "
                f"stdout={p.stdout[-400:]} stderr={p.stderr[-400:]}"
            )

        # берём самый свежий pdf (на всякий, если их несколько)
        produced = max(pdfs, key=lambda x: x.stat().st_mtime)

        tmp_out = out.with_suffix(out.suffix + ".tmp")
        shutil.copy2(str(produced), str(tmp_out))
        os.replace(str(tmp_out), str(out))

    return str(out)

def preview_pdf_path_for(filefield) -> str:
    src = Path(filefield.path)
    return str(src.parent / "_previews" / (src.name + ".pdf"))