# panel/utils.py
import re

def _m_name(m):
    return (m.get("name") or m.get("nombre") or m.get("titulo") or "").strip()

def _m_code(m):
    return (m.get("code") or m.get("codigo") or m.get("clave") or "").strip()

def curso_modules_choices(curso):
    """
    Возвращает список [(key, label), ...]
    key = name (как у тебя в materiales module_key)
    """
    raw = getattr(curso, "modules", None) or []
    out = []
    seen = set()

    for m in raw:
        if not isinstance(m, dict):
            continue

        name = _m_name(m)
        code = _m_code(m)

        # label красивый: "MF1 ... (MF1)" если есть код
        label = name
        if code and code not in name:
            label = f"{name} ({code})" if name else code

        # key: используем name как module_key (совпадает с твоей логикой в materiales)
        key = name or code
        if not key:
            continue

        if key in seen:
            continue
        seen.add(key)
        out.append((key, label))

    return out

def curso_module_label(curso, module_key: str) -> str:
    module_key = (module_key or "").strip()
    if not module_key:
        return ""
    for k, label in curso_modules_choices(curso):
        if k == module_key:
            return label
    return module_key


def extract_convocatoria(title: str) -> int | None:
    s = (title or "").lower()

    # варианты: "1ª", "1a", "primera", "convocatoria 1", "(c1)"
    if re.search(r"(convocatoria\s*1|\b1\s*[ªa]\b|\bprimera\b|\(c1\))", s):
        return 1
    if re.search(r"(convocatoria\s*2|\b2\s*[ªa]\b|\bsegunda\b|\(c2\))", s):
        return 2
    return None

def is_final_exam(title: str) -> bool:
    s = (title or "").lower()
    return ("examen" in s) and ("final" in s)
import re

def extract_mod_token(s: str) -> str:
    s = (s or "").upper()
    m = re.search(r"\b(UF\d{3,5}|MF\d{3,5}(?:_\d)?)\b", s)
    return m.group(1) if m else ""

def curso_module_names(curso):
    # то же, что ты используешь в INFO: name/code
    raw = curso.modules or []
    out = []
    for m in raw:
        if not isinstance(m, dict):
            continue
        name = (m.get("name") or m.get("nombre") or m.get("titulo") or "").strip()
        code = (m.get("code") or m.get("codigo") or m.get("clave") or "").strip()
        if name:
            out.append(name)
        elif code:
            out.append(code)
    return out

def guess_module_key_for_task(curso, title: str) -> str:
    tok = extract_mod_token(title)
    if not tok:
        return ""
    for mod_name in curso_module_names(curso):
        if extract_mod_token(mod_name) == tok:
            return mod_name
    return ""

def resolve_convocatoria(task) -> int | None:
    if getattr(task, "convocatoria", None) in (1, 2):
        return int(task.convocatoria)
    c = extract_convocatoria(getattr(task, "title", ""))
    if c in (1, 2):
        return c
    return None


def assign_convocatorias_auto(tasks_sorted):
    """
    tasks_sorted: список задач (обычно одного module_key), уже отсортированных по created_at/id
    Возвращает dict {1: task or None, 2: task or None}
    Логика:
      - сначала забираем те, у кого resolve_convocatoria_from_task() вернул 1/2
      - оставшиеся задачи распределяем по свободным слотам 1ª затем 2ª по порядку
    """
    slots = {1: None, 2: None}

    rest = []
    for t in tasks_sorted:
        c = resolve_convocatoria(t)
        if c in (1, 2) and slots[c] is None:
            slots[c] = t
        else:
            rest.append(t)

    for t in rest:
        if slots[1] is None:
            slots[1] = t
        elif slots[2] is None:
            slots[2] = t
        else:
            # больше двух финальных экзаменов на модуль — игнорируем лишние
            pass

    return slots
