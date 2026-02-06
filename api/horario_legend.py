from collections import defaultdict, Counter
from datetime import date
from django.db.models import Q
from .models import Horario  # или .models если файл рядом
from datetime import time

def _minutes(t1, t2) -> int:
    a = t1.hour * 60 + t1.minute
    b = t2.hour * 60 + t2.minute
    return b - a

def _layer_q(tipo: str, grupo: str) -> Q:
    tipo = (tipo or "curso").strip().lower()
    grupo = (grupo or "").strip()
    if tipo == "practica":
        if not grupo:
            raise ValueError("grupo es obligatorio para práctica")
        return Q(tipo="practica", grupo=grupo)
    return (Q(tipo__isnull=True) | Q(tipo="") | Q(tipo="curso"))

def _day_facts(qs):
    by_day = defaultdict(list)
    for h in qs:
        if h.dia and h.hora_inicio and h.hora_fin:
            by_day[h.dia].append(h)

    facts = {}
    for d, slots in by_day.items():
        start = min(s.hora_inicio for s in slots)
        end   = max(s.hora_fin for s in slots)
        minutes = sum(max(0, _minutes(s.hora_inicio, s.hora_fin)) for s in slots)
        facts[d] = {"start": start, "end": end, "minutes": minutes, "slots": slots}
    return facts
    
def _dominant_pattern(day_facts):
    c = Counter((v["start"], v["end"]) for v in day_facts.values())
    (base_start, base_end), _ = c.most_common(1)[0]
    return base_start, base_end
    
def _format_dmy(d: date) -> str:
    return d.strftime("%d/%m/%Y")

def build_horario_header_from_db(curso, tipo, grupo):
    layer = _layer_q(tipo, grupo)
    qs = (Horario.objects
          .filter(curso=curso).filter(layer)
          .order_by("dia", "hora_inicio", "hora_fin"))

    day_facts = _day_facts(qs)
    if not day_facts:
        return {"main": "", "exceptions": []}

    days_sorted = sorted(day_facts.keys())
    base_start, base_end = _dominant_pattern(day_facts)

    # основной период = весь диапазон (это важно!)
    main = f"Del {_format_dmy(days_sorted[0])} al {_format_dmy(days_sorted[-1])} " \
           f"{base_start.strftime('%H:%M')} – {base_end.strftime('%H:%M')}"

    exceptions = []
    for d in days_sorted:
        v = day_facts[d]
        if (v["start"], v["end"]) != (base_start, base_end):
            exceptions.append({
                "date": d,
                "line": f"El {_format_dmy(d)} el horario será de {round(v['minutes']/60,1)} horas "
                        f"(de {v['start'].strftime('%H:%M')} a {v['end'].strftime('%H:%M')})"
            })

    # ✅ если исключений много и реально есть смена режима на долго — можно дополнить режимами,
    # но твой кейс “всего один день” решается этим блоком.

    return {"main": main, "exceptions": exceptions}
   
def build_modules_legend_from_db(curso):
    qs = (Horario.objects
          .filter(curso=curso)
          .filter(Q(tipo__isnull=True) | Q(tipo="") | Q(tipo="curso"))
          .exclude(modulo__isnull=True).exclude(modulo="")
          .order_by("dia", "hora_inicio", "hora_fin"))

    by_mod = defaultdict(list)
    for h in qs:
        by_mod[h.modulo].append(h)

    out = []
    for mod_key, slots in by_mod.items():
        # диапазон дат модуля
        days = sorted({s.dia for s in slots})
        d_from, d_to = days[0], days[-1]

        # факты по дням внутри модуля
        by_day = defaultdict(list)
        for s in slots:
            by_day[s.dia].append(s)

        day_minutes = {}
        day_span = {}
        for d, ss in by_day.items():
            mins = sum(max(0, _minutes(x.hora_inicio, x.hora_fin)) for x in ss)
            st = min(x.hora_inicio for x in ss)
            en = max(x.hora_fin for x in ss)
            day_minutes[d] = mins
            day_span[d] = (st, en)

        # “типичный” день для этого модуля
        typical = Counter(day_minutes.values()).most_common(1)[0][0]

        exceptions = []
        for d in sorted(by_day.keys()):
            mins = day_minutes[d]
            if mins != typical:
                st, en = day_span[d]
                exceptions.append(
                    f"El {_format_dmy(d)} el horario será de {round(mins/60,1)} horas "
                    f"(de {st.strftime('%H:%M')} a {en.strftime('%H:%M')})"
                )

        out.append({
            "mod_key": mod_key,
            "from": d_from,
            "to": d_to,
            "exceptions": exceptions,
        })

    # сортировка по началу модуля
    out.sort(key=lambda x: x["from"])
    return out
    
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def _set_cell_text(cell, text, bold=False):
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(text or "")
    run.bold = bold
    run.font.size = Pt(11)

def _set_table_borders(table, outer_sz=18, inner_sz=8, color="000000"):
    """
    outer_sz / inner_sz: Word border size units (1/8 pt). 18 ≈ 2.25pt, 8 ≈ 1pt
    """
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = tblPr.find(qn("w:tblBorders"))
    if tblBorders is None:
        tblBorders = OxmlElement("w:tblBorders")
        tblPr.append(tblBorders)

    def _border(tag, sz):
        el = tblBorders.find(qn(f"w:{tag}"))
        if el is None:
            el = OxmlElement(f"w:{tag}")
            tblBorders.append(el)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)

    # внешние
    _border("top", outer_sz)
    _border("left", outer_sz)
    _border("bottom", outer_sz)
    _border("right", outer_sz)
    # внутренние
    _border("insideH", inner_sz)
    _border("insideV", inner_sz)

def _shade_row(row, fill="F3F3F3"):
    for cell in row.cells:
        tcPr = cell._tc.get_or_add_tcPr()
        shd = tcPr.find(qn("w:shd"))
        if shd is None:
            shd = OxmlElement("w:shd")
            tcPr.append(shd)
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), fill)

from datetime import datetime
from docx.shared import Pt

def _es_dmy(ymd: str) -> str:
    try:
        return datetime.strptime(ymd, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return ymd or ""

def _range_es(seg: dict) -> str:
    f = _es_dmy(seg.get("from", ""))
    t = _es_dmy(seg.get("to", ""))
    if f and t and f != t:
        return f"Del {f} al {t}"
    return f or t or ""

def _add_legend_nonlective(doc, vacaciones: list):
    # Заголовок секции
    p = doc.add_paragraph("Días no lectivos / vacaciones")
    if p.runs:
        p.runs[0].bold = True
        p.runs[0].font.size = Pt(12)

    # 1) Выходные
    doc.add_paragraph("• Fines de semana (sábado y domingo) — día no lectivo")

    # 2) Сегменты vacaciones
    if not vacaciones:
        doc.add_paragraph("• (Sin días no lectivos adicionales en el rango del curso)")
        return

    for seg in vacaciones:
        rango = _range_es(seg)
        motivo = (seg.get("motivo") or "").strip()
        line = f"• {rango}" if rango else "•"
        if motivo:
            line += f" – {motivo}"
        doc.add_paragraph(line)
        
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def _shade_cell(cell, fill_hex):
    fill = (fill_hex or "").replace("#", "").strip().upper() or "FFFFFF"
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcPr.append(shd)
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)

def _set_table_borders_nil(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = tblPr.find(qn("w:tblBorders"))
    if tblBorders is None:
        tblBorders = OxmlElement("w:tblBorders")
        tblPr.append(tblBorders)

    for tag in ("top","left","bottom","right","insideH","insideV"):
        el = tblBorders.find(qn(f"w:{tag}"))
        if el is None:
            el = OxmlElement(f"w:{tag}")
            tblBorders.append(el)
        el.set(qn("w:val"), "nil")

def _add_modules_legend_blocks(doc, curso, legend_items):
    """
    legend_items: список из payload.legend (у тебя legendJson):
      [{ titulo, rango, color, ufs:[{titulo,rango,detalles:[]},...], detallesMF:[] }, ...]
    """
    # ✅ разрыв страницы перед легендой
    doc.add_page_break()

    # ✅ заголовок = курс + общее время
    title = f"{(curso.titulo or '').strip()} — {int(getattr(curso, 'horas_total', 0) or 0)} horas"
    p = doc.add_paragraph(title)
    if p.runs:
        p.runs[0].bold = True
        p.runs[0].font.size = Pt(12)

    for item in legend_items:
        color = (item.get("color") or "#FFFFFF")
        titulo = (item.get("titulo") or "").strip()
        rango  = (item.get("rango") or "").strip()

        # 1 блок = 1x1 table с заливкой (как в HTML bgcolor)
        t = doc.add_table(rows=1, cols=1)
        _set_table_borders_nil(t)

        cell = t.rows[0].cells[0]
        _shade_cell(cell, color)

        # очистим дефолтный параграф
        cell.text = ""

        # заголовок
        pt = cell.add_paragraph()
        run = pt.add_run(titulo)
        run.bold = True
        run.font.size = Pt(11)

        # диапазон
        if rango:
            pr = cell.add_paragraph(rango)
            pr.runs[0].font.size = Pt(10)

        # MF детали (если вдруг есть)
        for line in (item.get("detallesMF") or []):
            pr = cell.add_paragraph(f"• {line}")
            pr.runs[0].font.size = Pt(9.5)

        # UFs
        for uf in (item.get("ufs") or []):
            ut = (uf.get("titulo") or "").strip()
            ur = (uf.get("rango") or "").strip()

            if ut:
                pr = cell.add_paragraph(ut)
                pr.runs[0].bold = True
                pr.runs[0].font.size = Pt(10)

            if ur:
                pr = cell.add_paragraph(ur)
                pr.runs[0].font.size = Pt(9.5)

            for line in (uf.get("detalles") or []):
                pr = cell.add_paragraph(f"• {line}")
                pr.runs[0].font.size = Pt(9.5)

        # маленький отступ после блока
        doc.add_paragraph("")