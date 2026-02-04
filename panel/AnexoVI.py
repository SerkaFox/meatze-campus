# panel/AnexoVI.py

from pathlib import Path
from datetime import date

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required

from docxtpl import DocxTemplate

from api.models import Curso, Enrol


# =========================================================
# Helper
# =========================================================

def _render_docx(template_path: Path, out_path: Path, context: dict):
    doc = DocxTemplate(str(template_path))
    doc.render(context)
    doc.save(str(out_path))


# =========================================================
# View
# =========================================================

@login_required
def anexo_vi_doc(request, codigo: str, alumno_id: int):
    """
    Генерация Anexo VI для 1 ученика
    /panel/anexo_vi/<codigo>/<alumno_id>/
    """

    curso = get_object_or_404(Curso, codigo=codigo)

    # только teacher
    is_teacher = Enrol.objects.filter(
        user=request.user,
        codigo=curso.codigo,
        role="teacher"
    ).exists()

    if not is_teacher:
        raise Http404

    # =====================================================
    # 🔹 ТУТ ФОРМИРУЕМ ДАННЫЕ
    # =====================================================

    hoy = date.today()

    context = {
        # ---------- верхняя часть ----------
        "codigo_especialidad": "IFCD0110",
        "especialidad": curso.titulo,
        "codigo_accion": curso.codigo,
        "duracion_horas": "120",
        "fecha_inicio": "01/02/2026",
        "fecha_fin": "30/04/2026",
        "entidad_formacion": "MEATZE",
        "n_censo": "00001",
        "direccion": "Bilbao",
        "localidad": "Bilbao",
        "territorio": "Bizkaia",

        "alumno_nombre": "APELLIDOS, NOMBRE",
        "dni": "00000000A",

        # fecha inferior
        "dia": f"{hoy.day:02d}",
        "mes": hoy.strftime("%m"),
        "ano": hoy.year,

        # ---------- TABLAS ----------
        # 🔹 строки UF
        "rows_uf": [
            {
                "mod_codigo_nombre": "MF1234 — Programación",
                "uf": "UF1",
                "e1": "7",
                "e2": "8",
                "e3": "",
                "e4": "",
                "media": "7.5",
                "conv1": "8",
                "conv2": "",
                "fin_apto": "Apto (7.8)",
                "cal_final": "Apto (7.8)",
            },
        ],

        # 🔹 строки без UF
        "rows_mf": [
            {
                "mod_codigo_nombre": "MF9999 — Proyecto final",
                "e1": "8",
                "e2": "9",
                "e3": "",
                "e4": "",
                "media": "8.5",
                "conv1": "9",
                "conv2": "",
                "cal_final": "Apto (8.7)",
            }
        ],
    }

    # =====================================================
    # 🔹 РЕНДЕР
    # =====================================================

    template_path = Path(__file__).parent / "anexo_vi_template.docx"

    out_dir = Path(settings.MEDIA_ROOT) / "tmp_docs"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"anexo_vi_{codigo}_{alumno_id}.docx"

    _render_docx(template_path, out_path, context)

    return FileResponse(open(out_path, "rb"), as_attachment=True)
