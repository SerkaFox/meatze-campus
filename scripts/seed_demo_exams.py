from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone

from api.models import Curso, Enrol
from panel.models import CourseTask, CourseTaskAttachment, TaskSubmission
from panel.utils import curso_module_label, curso_modules_choices


COURSE_CODE = "IFCT0209-DEMO"
TEACHER_EMAIL = "serkafox@gmail.com"
PREFIX = "DEMO |"


def tiny_pdf(title, body):
    text = (title + "\\n" + body).replace("(", "[").replace(")", "]")
    stream = f"BT /F1 14 Tf 72 740 Td ({text[:780]}) Tj ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(stream.encode('utf-8'))} >> stream\\n{stream}\\nendstream endobj",
    ]
    out = "%PDF-1.4\\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(out.encode("utf-8")))
        out += obj + "\\n"
    xref = len(out.encode("utf-8"))
    out += f"xref\\n0 {len(objects)+1}\\n0000000000 65535 f \\n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \\n"
    out += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\\nstartxref\\n{xref}\\n%%EOF\\n"
    return out.encode("utf-8")


def put_file(field, name, title, body):
    field.save(name, ContentFile(tiny_pdf(title, body)), save=False)


def upsert_task(curso, teacher, spec):
    title = f"{PREFIX} {spec['title']}"
    CourseTask.objects.filter(curso=curso, title=title).delete()

    task = CourseTask.objects.create(
        curso=curso,
        created_by=teacher,
        title=title,
        description=spec["description"],
        module_key=spec["module_key"],
        module_label=curso_module_label(curso, spec["module_key"]),
        is_final_exam=spec.get("is_final_exam", False),
        convocatoria=spec.get("convocatoria"),
        is_published=True,
        is_closed=spec.get("is_closed", False),
        due_at=timezone.now() + spec.get("due_delta", timezone.timedelta(days=7)),
    )
    filename = spec["file_name"]
    put_file(task.file, filename, title, spec["description"])
    task.file_name = filename
    task.file_size = task.file.size
    task.ext = "pdf"
    task.save(update_fields=["file", "file_name", "file_size", "ext"])

    for idx, attach_title in enumerate(spec.get("attachments", []), start=1):
        attach_name = f"{filename.rsplit('.', 1)[0]}_anexo_{idx}.pdf"
        a = CourseTaskAttachment(task=task, file_name=attach_name, ext="pdf")
        put_file(a.file, attach_name, f"Anexo {idx} - {title}", attach_title)
        a.file_size = a.file.size
        a.save()

    return task


def upsert_submission(task, student, status, grade=None, feedback="", comment=""):
    sub = TaskSubmission.objects.filter(task=task, alumno=student).first()
    if sub and sub.file:
        sub.file.delete(save=False)
    if not sub:
        sub = TaskSubmission(task=task, alumno=student)

    filename = f"entrega_{student.id}_{task.id}.pdf"
    body = comment or f"Entrega de {student.get_full_name() or student.email} para {task.title}"
    put_file(sub.file, filename, f"Entrega - {task.title}", body)
    sub.file_name = filename
    sub.file_size = sub.file.size
    sub.ext = "pdf"
    sub.comment = comment
    sub.status = status
    sub.submitted_at = timezone.now()

    if status == TaskSubmission.STATUS_GRADED:
        sub.grade = Decimal(str(grade))
        sub.teacher_feedback = feedback
        sub.graded_by = task.created_by
        sub.graded_at = timezone.now()
    else:
        sub.grade = None
        sub.teacher_feedback = ""
        sub.graded_by = None
        sub.graded_at = None

    sub.save()
    return sub


curso = Curso.objects.get(codigo=COURSE_CODE)
User = get_user_model()
teacher = User.objects.get(email=TEACHER_EMAIL)
students = list(
    User.objects.filter(
        id__in=Enrol.objects.filter(codigo=curso.codigo, role="student").values_list("user_id", flat=True)
    ).order_by("id")
)
modules = curso_modules_choices(curso)
module_keys = [k for k, _ in modules]

if len(module_keys) < 3 or not students:
    raise RuntimeError("No hay suficientes módulos o alumnos para crear la demo.")

specs = [
    {
        "title": "Test diagnóstico - sistema operativo",
        "description": "Prueba corta para revisar conceptos básicos antes de la corrección formal.",
        "module_key": module_keys[0],
        "file_name": "demo_test_diagnostico_so.pdf",
        "attachments": ["Plantilla de respuesta y criterios de corrección."],
    },
    {
        "title": "Práctica evaluable - configuración de usuario",
        "description": "Entrega práctica con evidencias de configuración, capturas y explicación breve.",
        "module_key": module_keys[1],
        "file_name": "demo_practica_configuracion_usuario.pdf",
    },
    {
        "title": "Examen final ANEXO VI - Variante A",
        "description": "Variante A del examen final. Incluye tareas de instalación, verificación y explotación de funcionalidades.",
        "module_key": module_keys[1],
        "file_name": "demo_anexo_vi_variante_a.pdf",
        "is_final_exam": True,
        "convocatoria": 1,
        "attachments": ["Rúbrica oficial: instalación, evidencias, seguridad y documentación."],
    },
    {
        "title": "Examen final ANEXO VI - Variante B",
        "description": "Variante B para comparar el flujo de corrección de varios modelos del mismo examen.",
        "module_key": module_keys[1],
        "file_name": "demo_anexo_vi_variante_b.pdf",
        "is_final_exam": True,
        "convocatoria": 1,
    },
    {
        "title": "Examen recuperación ANEXO VI - 2ª convocatoria",
        "description": "Modelo de recuperación para ver la segunda convocatoria en la cola y en el libro de notas.",
        "module_key": module_keys[2],
        "file_name": "demo_anexo_vi_recuperacion.pdf",
        "is_final_exam": True,
        "convocatoria": 2,
    },
]

tasks = [upsert_task(curso, teacher, spec) for spec in specs]

if len(students) >= 3:
    s1, s2, s3 = students[:3]
else:
    s1 = s2 = s3 = students[0]

upsert_submission(tasks[0], s1, TaskSubmission.STATUS_GRADED, "8.50", "Buen dominio general. Revisa la parte de permisos.", "Respondo con capturas y explicación.")
upsert_submission(tasks[0], s2, TaskSubmission.STATUS_GRADED, "6.75", "Correcto, pero faltan evidencias en dos apartados.", "Adjunto mi test.")
upsert_submission(tasks[0], s3, TaskSubmission.STATUS_SUBMITTED, comment="Pendiente de revisar por el docente.")

upsert_submission(tasks[1], s1, TaskSubmission.STATUS_SUBMITTED, comment="He incluido capturas y pasos realizados.")
upsert_submission(tasks[1], s2, TaskSubmission.STATUS_SUBMITTED, comment="Entrega con dudas en el apartado final.")

upsert_submission(tasks[2], s1, TaskSubmission.STATUS_SUBMITTED, comment="Variante A completada.")
upsert_submission(tasks[2], s2, TaskSubmission.STATUS_GRADED, "9.00", "Muy completo. Evidencias claras y buen orden.", "Variante A con evidencias.")

upsert_submission(tasks[3], s3, TaskSubmission.STATUS_SUBMITTED, comment="Variante B entregada para corrección.")

upsert_submission(tasks[4], s1, TaskSubmission.STATUS_GRADED, "5.25", "Aprobado justo. Conviene reforzar instalación de periféricos.", "Recuperación entregada.")

print(f"Demo creada: {len(tasks)} tareas/exámenes, {TaskSubmission.objects.filter(task__in=tasks).count()} entregas.")
for task in tasks:
    print(f"- {task.title}: {task.submissions.count()} entregas")
