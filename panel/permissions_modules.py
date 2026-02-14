# panel/permissions_modules.py
from panel.models import StudentModuleAccess

def get_disabled_modules(curso, alumno) -> set[str]:
    return set(
        StudentModuleAccess.objects
            .filter(curso=curso, alumno=alumno, is_enabled=False)
            .values_list("module_key", flat=True)
    )

def is_module_enabled(curso, alumno, module_key: str) -> bool:
    if not module_key:
        return True
    row = StudentModuleAccess.objects.filter(
        curso=curso, alumno=alumno, module_key=module_key
    ).first()
    return True if row is None else bool(row.is_enabled)