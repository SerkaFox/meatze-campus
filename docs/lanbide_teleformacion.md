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

## Modelo de datos real (Anexo V) — verificado sobre el WSDL y el PDF oficiales

A diferencia de todo lo anterior (que salía de texto legal), esto sale de los
artefactos técnicos reales publicados por el SEPE, descargados y parseados
directamente:
- WSDL: `https://www.sepe.es/SiteSepe/contenidos/personas/formacion/centros_formacion/pdf/ProveedorCentroTFWS_20140619.wsdl`
- Modelo de datos (27 págs.): `.../pdf/Modelo_Datos_Seguimiento_Teleformacion.pdf`

### Las 6 operaciones (nosotros somos el SERVIDOR SOAP, el SEPE es el cliente)

| Operación | Entrada | Salida | Quién la dispara |
|---|---|---|---|
| `crearCentro` | `DATOS_IDENTIFICATIVOS` (sin CODIGO_CENTRO) | `RESPUESTA_DATOS_CENTRO` con el `CODIGO_CENTRO` que nos asigna el SEPE | SEPE, una vez tras acreditación |
| `obtenerDatosCentro` | (vacío) | `RESPUESTA_DATOS_CENTRO` | SEPE, cuando quiera |
| `crearAccion` | `ACCION_FORMATIVA` (sin código) | `RESPUESTA_OBT_ACCION` con `CODIGO_ACCION` asignado | SEPE, tras autorizar cada acción formativa |
| `obtenerListaAcciones` | (vacío) | lista de `ID_ACCION` | SEPE |
| `obtenerAccion` | `ID_ACCION` | `RESPUESTA_OBT_ACCION` (toda la ficha + uso + participantes) | SEPE, periódicamente (inicio/durante/fin) |
| `eliminarAccion` | `ID_ACCION` | `RESPUESTA_ELIMINAR_ACCION` | SEPE |

Todas devuelven `CODIGO_RETORNO` (-2 WS no disponible, -1 error inesperado, 0
correcto, 1 conflicto/ya existe, 2 error de parámetro) + `ETIQUETA_ERROR`
(nombre del campo que falló, si aplica).

### DATOS_IDENTIFICATIVOS (centro)
`ID_CENTRO{ORIGEN_CENTRO, CODIGO_CENTRO}`, `NOMBRE_CENTRO` (≤40), `URL_PLATAFORMA`,
`URL_SEGUIMIENTO` (la que declaramos en la acreditación — es la única fuente válida,
no se puede cambiar libremente), `TELEFONO`, `EMAIL`.
`CODIGO_CENTRO` = provincia (2 dígitos; teleformación siempre **80**, no hay
provincia física) + secuencial de 8 dígitos que **asigna el SEPE**, no nosotros.

### ACCION_FORMATIVA (lo grande)
```
ID_ACCION{ORIGEN_ACCION, CODIGO_ACCION}      # CODIGO_ACCION lo asigna el SEPE
SITUACION                                     # 10 Solicitada / 20 Programada-Autorizada /
                                               # 30 Iniciada / 40 Finalizada / 50 Cancelada
ID_ESPECIALIDAD_PRINCIPAL{ORIGEN, AREA_PROFESIONAL(4), CODIGO_ESPECIALIDAD(14)}
DURACION (horas), FECHA_INICIO, FECHA_FIN (dd/mm/aaaa)
IND_ITINERARIO_COMPLETO (SI/NO)
TIPO_FINANCIACION                             # PU público / PR privado
NUMERO_ASISTENTES
DESCRIPCION_ACCION{DENOMINACION, INFORMACION_GENERAL, HORARIOS, REQUISITOS, CONTACTO_ACCION}
ESPECIALIDADES_ACCION.ESPECIALIDAD[]          # un módulo/unidad formativa por entrada:
  ID_ESPECIALIDAD{ORIGEN, AREA_PROFESIONAL, CODIGO_ESPECIALIDAD}
  CENTRO_IMPARTICION{ORIGEN_CENTRO, CODIGO_CENTRO}
  FECHA_INICIO, FECHA_FIN
  MODALIDAD_IMPARTICION                       # TF teleformación / PR presencial / PE práctica
  DATOS_DURACION{HORAS_PRESENCIAL, HORAS_TELEFORMACION}
  CENTROS_SESIONES_PRESENCIALES.CENTRO_PRESENCIAL[]{ORIGEN, CODIGO}   # EM si es empresa
  TUTORES_FORMADORES.TUTOR_FORMADOR[]
    ID_TUTOR{TIPO_DOCUMENTO(D/E/U/W/G/H), NUM_DOCUMENTO, LETRA_NIF}
    ACREDITACION_TUTOR (texto libre, título/certificación máxima)
    EXPERIENCIA_PROFESIONAL (años, entero)
    COMPETENCIA_DOCENTE                       # código 01-06, ver tabla abajo
    EXPERIENCIA_MODALIDAD_TELEFORMACION (horas como tutor online)
    FORMACION_MODALIDAD_TELEFORMACION         # código 01-06 análogo, formación específica en teleform.
  USO.{HORARIO_MANANA|TARDE|NOCHE}{NUM_PARTICIPANTES, NUMERO_ACCESOS, DURACION_TOTAL}
      .SEGUIMIENTO_EVALUACION{NUM_PARTICIPANTES, NUMERO_ACTIVIDADES_APRENDIZAJE,
                               NUMERO_INTENTOS, NUMERO_ACTIVIDADES_EVALUACION}
PARTICIPANTES.PARTICIPANTE[]
  ID_PARTICIPANTE{TIPO_DOCUMENTO, NUM_DOCUMENTO, LETRA_NIF}   # NIF/NIE real del alumno
  INDICADOR_COMPETENCIAS_CLAVE
  CONTRATO_FORMACION{ID_CONTRATO_CFA?, CIF_EMPRESA?, ID_TUTOR_EMPRESA?, ID_TUTOR_FORMACION?}
  ESPECIALIDADES_PARTICIPANTE.ESPECIALIDAD[]  # por cada módulo en el que está matriculado:
    ID_ESPECIALIDAD{...}, FECHA_ALTA, FECHA_BAJA
    TUTORIAS_PRESENCIALES.TUTORIA_PRESENCIAL[]{CENTRO_PRESENCIAL_TUTORIA, FECHA_INICIO, FECHA_FIN}
    EVALUACION_FINAL{CENTRO_PRESENCIAL_EVALUACION?, FECHA_INICIO?, FECHA_FIN?}
    RESULTADOS{RESULTADO_FINAL?, CALIFICACION_FINAL?, PUNTUACION_FINAL?}
```

`TIPO_DOCUMENTO`: D=DNI, E=NIE, U=identificación EEE sin NIE, W=identificación
fuera del EEE sin NIE, G=persona privada de libertad, H=identificación
convencional (duplicados/casos especiales).

`COMPETENCIA_DOCENTE` / `FORMACION_MODALIDAD_TELEFORMACION` (códigos 01-06):
01 certificado de profesionalidad de docencia FPE, 02 certificado formador
ocupacional, 03 CAP/especialización didáctica, 04 máster habilitante docencia,
05 curso equivalente a formación pedagógica, 06 experiencia docente ≥600h en
los últimos 10 años.

### WS-Security (autenticación de las llamadas entrantes del SEPE hacia nosotros)
SOAP 1.1 sobre HTTPS, cabecera `wsse:UsernameToken` tipo `wsse:PasswordText`
(usuario/contraseña en texto plano dentro del sobre, protegido solo por el TLS
del transporte — por eso el requisito explícito de SSL). Las credenciales se
acuerdan con el SEPE/Lanbide al declarar la URL de seguimiento en la
acreditación; no las inventamos nosotros solos.

## Gaps de datos que faltan hoy en Meatze para poder rellenar esto

Ninguno de estos campos existe actualmente en el modelo de datos:
- **NIF/NIE de alumnos y tutores** — `User`/`UserProfile` no tienen ningún
  campo de documento de identidad.
- **Cualificación del tutor** (`ACREDITACION_TUTOR`, `COMPETENCIA_DOCENTE`,
  `EXPERIENCIA_PROFESIONAL`, `EXPERIENCIA_MODALIDAD_TELEFORMACION`,
  `FORMACION_MODALIDAD_TELEFORMACION`) — no se registra en ningún sitio.
- **Resultado/calificación final por alumno y módulo** (`RESULTADOS`) — no
  existe un modelo de notas/evaluación, solo entregas de tareas (`TaskSubmission`).
- **Código de especialidad formativa** (área profesional + código de 14
  dígitos del Catálogo SEPE) por curso/módulo — `Curso.modules` es JSON libre
  sin ese código.
- **Modalidad de impartición por módulo** (TF/PR/PE) — no existe, todo se
  trata igual.

## Plan de implementación propuesto (por fases)

1. ✅ **Fontanería del servicio SOAP** — `api/lanbide_soap.py`, endpoint en
   `/lanbide/seguimiento/` (`meatze_site/urls.py`). Implementado y probado
   end-to-end (`curl` con sobres SOAP reales):
   - Parseo del sobre + validación `wsse:UsernameToken`/`PasswordText`
     (fail-closed: sin `LANBIDE_WS_USERNAME`/`LANBIDE_WS_PASSWORD`
     configurados, rechaza todo con `soapenv:Fault`).
   - `crearCentro`: guarda `DATOS_IDENTIFICATIVOS` en el modelo
     `LanbideCentro` (fila única). Si ya existe centro, devuelve
     `CODIGO_RETORNO=1` (conflicto) con los datos actuales en vez de
     sobrescribir.
   - `obtenerDatosCentro`: devuelve lo que tengamos guardado.
   - `crearAccion` / `obtenerAccion` / `obtenerListaAcciones` /
     `eliminarAccion`: responden de forma válida (XML conforme al WSDL)
     con `CODIGO_RETORNO=-2` ("WS no disponible") hasta la fase 2/3.
   - Credenciales de prueba en `deploy/.env`
     (`LANBIDE_WS_USERNAME=aurora_test_user`) — **sustituir por las reales
     antes de declarar la URL a Lanbide**.
2. **Modelo de datos que falta**: NIF/NIE, campos de cualificación del tutor,
   código de especialidad por módulo, modalidad de impartición, resultado
   final — más la UI de admin para rellenarlos.
3. **Mapeo real**: construir `ACCION_FORMATIVA`/`PARTICIPANTE` a partir de
   `Enrol`, `AttendanceSession`, `LearningEvent`, `TaskSubmission` y los
   campos nuevos de la fase 2.
4. **Acreditar de verdad con Lanbide** (`teleformacion@lanbide.eus`): darles
   la URL de seguimiento real, coordinar credenciales WS-Security, y validar
   con la herramienta de autoevaluación del SEPE (`ProvCentTFVal_20161118.zip`,
   publicada en sepe.es) antes de presentar la solicitud.
