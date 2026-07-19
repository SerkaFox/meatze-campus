# Lanbide / SEPE — requisitos para teleformación (referencia)

Investigación hecha el 2026-07-19. Fuentes primarias verificadas leyendo el PDF/BOE
directamente (no solo resúmenes), porque hay normativa derogada circulando en blogs
de terceros que ya no aplica.

## Dos regímenes distintos — no confundir

1. **Autorización administrativa** para impartir certificados de profesionalidad en
   modalidad teleformación (trámite en la sede electrónica del SEPE, con certificado
   digital / Cl@ve / DNIe). Esto es papeleo, no integración técnica.
   Fuente: [Instrucciones Lanbide](https://www.lanbide.euskadi.eus/contenidos/informacion/formacion_instrucciones_2017/eu_def/adjuntos/2021/INSTRUCCIONES-SOLICITUD-AUTORIZACION-DE-ACCIONES-FORMATIVOS-EN-MODALIDAD-DE-TELEFORMACION.pdf)
   Puntos clave:
   - Solicitud 30 días naturales antes del inicio; firma digital obligatoria (no manuscrita/escaneada).
   - Una solicitud = un único módulo formativo.
   - Máx. 2 acciones nuevas por semana y entidad; entre 50h y 120h por mes natural.
   - Solo participan personas con NIF/NIE en vigor que cumplan el art. 20 RD 34/2008.
   - Tras autorización, "Comunicación de inicio" antes de empezar.
   - Contacto Lanbide: `teleformacion@lanbide.eus`, 945062411 (Marian), 945181369 (Begoña).
   - Rige el **RD 34/2008** desarrollado por la **Orden ESS/1897/2013** (para certificados
     de profesionalidad) — su Anexo II técnico está **derogado**.

2. **Requisitos técnicos de la plataforma de teleformación** — vigentes, en la
   **Orden TMS 369/2019** (Anexo II y Anexo V), que sustituyó al Anexo II derogado de la
   Orden ESS/1897/2013. Verificado línea por línea sobre el texto consolidado del BOE.
   Fuente: [BOE-A-2019-4716 consolidado (Fundae)](https://www.fundae.es/docs/default-source/empresas/documentos/boe-a-2019-4716-consolidado.pdf)

   **Esto solo aplica si el curso está registrado oficialmente en modalidad
   "teleformación" dentro del Catálogo de Especialidades Formativas** (subvencionado,
   con seguimiento por la administración). Si Meatze se usa como portal de apoyo a
   cursos **presenciales**, este régimen pesado no aplica tal cual — lo que sigue
   aplicando siempre es la necesidad de justificar horas/asistencia/entrega de
   material ante Lanbide, que es más ligero.

## Anexo II — requisitos técnicos de la plataforma (si es teleformación oficial)

**Infraestructura**
- Servidor propio con ancho de banda mínimo 100 Mbs simétrico (subida/bajada).
- Hospedaje para el total de alumnos activos; máx. 80 alumnos/tutor, 40% concurrencia.
- Funcionamiento 24h/7 días.
- Para certificados de profesionalidad: disponibilidad ≥99%, recuperación ante fallos ≤8h.

**Software**
- Compatibilidad SCORM + paquetes IMS.
- Accesibilidad AA — norma UNE 139803:2012 (equivalente WCAG 2.0 AA).
- Cumplimiento LO 3/2018 (protección de datos) — identificar ubicación física del servidor.
- Multisoporte (portátil, móvil, tablet) para certificados de profesionalidad.
- **"Disponibilidad del servicio web de seguimiento de las acciones formativas...
  conforme al modelo de datos y protocolo de transmisión establecidos en el anexo V"**
  — este es el punto técnico grande que falta (ver abajo).

**Servicios y soporte**
- Comunicación síncrona (aula virtual, chat, pizarra) + asíncrona (email, foro,
  calendario, tablón). Mínimo obligatorio: mensajería + foro + chat.
- Herramientas de colaboración (grupos, carpetas compartidas, foros/chats privados).
- Administración de usuarios (altas/bajas, roles, permisos, autenticación).
- Gestión de contenidos (subir/organizar/publicar archivos).
- Evaluación (pruebas, autocorrección, calificación, informes de seguimiento).
- CAU (Centro de Atención a Usuarios): teléfono + mensajería, horario mañana/tarde,
  respuesta ≤48h laborables.
- Imagen institucional del SEPE/administración laboral correspondiente.

## Anexo V — el servicio web de seguimiento (la integración técnica real)

Esta es la pieza que de verdad significa "conectar la plataforma con Lanbide/SEPE":

- **Protocolo: SOAP 1.1 sobre HTTPS**, ajustado a un **WSDL publicado por el SEPE**
  (no lo define la entidad de formación).
- Autenticación: **WS-Security UsernameToken Profile 1.0** (credenciales `wsse:PasswordText`).
- Confidencialidad vía SSL.
- La entidad de formación **implementa un servidor SOAP** (no un cliente) que la
  Administración invoca. Operaciones obligatorias que debe exponer:
  - `crearCentro`
  - `obtenerDatosCentro`
  - `crearAccion`
  - `obtenerListaAcciones`
  - `obtenerAccion`
  - `eliminarAccion`
- Cada operación devuelve `<codigoRetorno>` (0=correcto, 1=conflicto, 2=error de
  parámetro, -1=error inesperado, -2=WS no disponible).
- Seguimiento activo desde el inicio previsto de la acción hasta 30 días naturales
  tras su fin; resultados accesibles 90 días naturales tras la finalización.
- Periodicidad: al inicio (tras comunicación de inicio), durante el desarrollo (la
  que determine la administración), y tras la finalización.
- Solo la **URL de seguimiento declarada en la acreditación/inscripción** es fuente
  válida — no se puede cambiar libremente.

**Además del servicio web**, el Anexo V exige **visita virtual**: credenciales de
acceso de perfil administrador (solo lectura, sin poder modificar datos) para que
la administración entre directamente a revisar informes de seguimiento generados
automáticamente por alumno/curso/módulo y por rango de fechas.

## Auditoría (Anexo II.C)

Cada plataforma de teleformación se audita (inicial, y en modificaciones relevantes)
mediante pruebas reales sobre infraestructura + LMS. Para poder auditar, la entidad
debe entregar, al solicitar la acreditación/inscripción, credenciales de administrador
de solo lectura (y también de tutor/alumno para certificados de profesionalidad).

## Qué tiene Meatze hoy vs. qué faltaría

| Requisito | Estado en Meatze |
|---|---|
| Seguimiento de actividad por alumno/curso/fecha | ✅ `LearningEvent` + panel Lanbide (`api/views_events.py`, `lanbide.js`) |
| Registro de asistencia | ✅ `AttendanceSession` |
| Trazabilidad de entrega de material (digital/físico) | ✅ `MaterialDownload` / `MaterialReceipt` / `CursoPhysicalConfig` |
| Exportación de horarios con membrete Lanbide+Euskadi | ✅ `docx_export.py`, `panel/views.py` |
| Exportación CSV de actividad | ✅ botón "Exportar CSV" en panel Lanbide |
| SCORM/IMS en el contenido de los módulos | ❌ no existe (los materiales son archivos sueltos, no paquetes SCORM) |
| Servicio web SOAP de seguimiento (Anexo V) | ❌ no existe ningún endpoint SOAP/WSDL |
| Acceso de solo-lectura para auditoría/visita virtual | ❌ no hay un rol "auditor" separado del admin compartido actual |
| Accesibilidad AA (UNE 139803 / WCAG 2.0 AA) | ⚠️ no auditado |
| CAU con SLA de 48h documentado | ⚠️ existe el chat widget, pero sin SLA formal declarado |
| 24/7 + 99% disponibilidad + recuperación ≤8h | ⚠️ depende del hosting actual, no verificado |

## Antes de programar nada más

No sé si los cursos de Meatze están dados de alta oficialmente como **modalidad
teleformación** dentro del Catálogo de Especialidades Formativas, o si el centro
opera en **presencial** y esta plataforma es solo un portal de apoyo. Esa respuesta
cambia completamente el alcance:

- Si es teleformación oficial → falta construir el servidor SOAP del Anexo V (trabajo
  de varios días: WSDL, WS-Security, y coordinarlo con el expediente real del centro
  en Lanbide) y probablemente empaquetar contenidos en SCORM.
- Si es presencial/mixto → lo que ya existe (actividad, asistencia, material,
  horarios con membrete) es probablemente suficiente para justificar ante Lanbide;
  no hace falta el SOAP.

Contactar `teleformacion@lanbide.eus` para confirmar bajo qué modalidad está
acreditado cada curso antes de invertir tiempo en el servicio SOAP.
