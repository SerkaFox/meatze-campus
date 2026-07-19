# api/lanbide_soap.py
"""
Servicio web de seguimiento (Anexo V, Orden TMS/369/2019) — somos el
SERVIDOR SOAP que invoca el SEPE, no al revés.

Contrato verificado contra el WSDL oficial (ProveedorCentroTFWS, publicado en
sepe.es) y el PDF "Modelo de datos para el seguimiento de las acciones
formativas impartidas en modalidad de teleformación". Ver docs/lanbide_teleformacion.md.

Fase 1 (esta implementación): fontanería SOAP completa + crearCentro /
obtenerDatosCentro con persistencia real. crearAccion / obtenerAccion /
obtenerListaAcciones / eliminarAccion responden de forma válida pero con
CODIGO_RETORNO=-2 ("WS no disponible") hasta que exista el modelo de datos
de acciones formativas (fase 2/3 del plan).
"""
import base64
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from lxml import etree

from api.models import LanbideCentro

NS = {
    "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
    "wsse": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd",
    "impl": "http://impl.ws.application.proveedorcentro.meyss.spee.es",
    "entsal": "http://entsal.bean.domain.common.proveedorcentro.meyss.spee.es",
    "salida": "http://salida.bean.domain.common.proveedorcentro.meyss.spee.es",
}

SOAPENV = NS["soapenv"]
IMPL = NS["impl"]
ENTSAL = NS["entsal"]
SALIDA = NS["salida"]

OPERATIONS = {
    "crearCentro",
    "obtenerDatosCentro",
    "crearAccion",
    "obtenerAccion",
    "obtenerListaAcciones",
    "eliminarAccion",
}

NOT_YET_IMPLEMENTED = {"crearAccion", "obtenerAccion", "obtenerListaAcciones", "eliminarAccion"}


class SoapFault(Exception):
    def __init__(self, faultstring, faultcode="soapenv:Client"):
        self.faultcode = faultcode
        self.faultstring = faultstring
        super().__init__(faultstring)


def _q(ns, tag):
    return f"{{{ns}}}{tag}"


def _text(parent, tag_local, ns=None):
    """Busca un hijo directo por nombre local (con o sin namespace) y devuelve su texto."""
    if parent is None:
        return ""
    if ns:
        el = parent.find(_q(ns, tag_local))
        if el is not None:
            return (el.text or "").strip()
    # los campos locales (no referenciados desde otro schema) van sin namespace
    el = parent.find(tag_local)
    if el is not None:
        return (el.text or "").strip()
    # fallback: cualquier namespace
    for child in parent:
        if etree.QName(child).localname == tag_local:
            return (child.text or "").strip()
    return ""


# ---------------------------------------------------------------------------
# WS-Security
# ---------------------------------------------------------------------------

def _check_ws_security(envelope):
    expected_user = (getattr(settings, "LANBIDE_WS_USERNAME", "") or "").strip()
    expected_pass = (getattr(settings, "LANBIDE_WS_PASSWORD", "") or "").strip()

    if not expected_user or not expected_pass:
        # Fail-closed: sin credenciales configuradas no se acepta ninguna llamada.
        raise SoapFault("Servicio no configurado (sin credenciales WS-Security).",
                         faultcode="soapenv:Server")

    header = envelope.find(_q(SOAPENV, "Header"))
    security = header.find(_q(NS["wsse"], "Security")) if header is not None else None
    token = security.find(_q(NS["wsse"], "UsernameToken")) if security is not None else None
    if token is None:
        raise SoapFault("Falta wsse:UsernameToken.", faultcode="wsse:FailedAuthentication")

    username = _text(token, "Username", NS["wsse"])
    pwd_el = token.find(_q(NS["wsse"], "Password"))
    password = (pwd_el.text or "").strip() if pwd_el is not None else ""
    pwd_type = pwd_el.get("Type", "") if pwd_el is not None else ""

    # Solo se admite PasswordText (lo exige el propio Anexo V).
    if pwd_type and "PasswordText" not in pwd_type:
        raise SoapFault("Solo se admite wsse:PasswordText.", faultcode="wsse:FailedAuthentication")

    if username != expected_user or password != expected_pass:
        raise SoapFault("Credenciales inválidas.", faultcode="wsse:FailedAuthentication")


# ---------------------------------------------------------------------------
# DATOS_IDENTIFICATIVOS <-> LanbideCentro
# ---------------------------------------------------------------------------

def _centro_singleton():
    obj, _ = LanbideCentro.objects.get_or_create(pk=1)
    return obj


def _parse_datos_identificativos(el):
    id_centro = el.find("ID_CENTRO")
    origen = _text(id_centro, "ORIGEN_CENTRO") if id_centro is not None else ""
    codigo = _text(id_centro, "CODIGO_CENTRO") if id_centro is not None else ""
    return {
        "origen_centro": origen,
        "codigo_centro": codigo,
        "nombre_centro": _text(el, "NOMBRE_CENTRO"),
        "url_plataforma": _text(el, "URL_PLATAFORMA"),
        "url_seguimiento": _text(el, "URL_SEGUIMIENTO"),
        "telefono": _text(el, "TELEFONO"),
        "email": _text(el, "EMAIL"),
    }


def _dat_id_elem(centro: LanbideCentro, tag):
    el = etree.Element(tag)
    id_centro = etree.SubElement(el, "ID_CENTRO")
    etree.SubElement(id_centro, "ORIGEN_CENTRO").text = centro.origen_centro
    etree.SubElement(id_centro, "CODIGO_CENTRO").text = centro.codigo_centro
    etree.SubElement(el, "NOMBRE_CENTRO").text = centro.nombre_centro
    etree.SubElement(el, "URL_PLATAFORMA").text = centro.url_plataforma
    etree.SubElement(el, "URL_SEGUIMIENTO").text = centro.url_seguimiento
    etree.SubElement(el, "TELEFONO").text = centro.telefono
    etree.SubElement(el, "EMAIL").text = centro.email
    return el


# ---------------------------------------------------------------------------
# Operation handlers — each returns (codigo_retorno, etiqueta_error, extra_els)
# ---------------------------------------------------------------------------

def _op_crear_centro(body_el):
    datos_el = body_el.find(_q(ENTSAL, "DATOS_IDENTIFICATIVOS"))
    if datos_el is None:
        datos_el = body_el.find("DATOS_IDENTIFICATIVOS")
    parsed = _parse_datos_identificativos(datos_el) if datos_el is not None else {}

    centro = _centro_singleton()
    if centro.codigo_centro:
        # Ya existe un centro dado de alta -> conflicto (código 1: "Centro con acciones").
        return 1, "CODIGO_CENTRO", [_dat_id_elem(centro, f"{{{ENTSAL}}}DATOS_IDENTIFICATIVOS")]

    for field, value in parsed.items():
        if value:
            setattr(centro, field, value)
    centro.save()

    return 0, "", [_dat_id_elem(centro, f"{{{ENTSAL}}}DATOS_IDENTIFICATIVOS")]


def _op_obtener_datos_centro(body_el):
    centro = _centro_singleton()
    return 0, "", [_dat_id_elem(centro, f"{{{ENTSAL}}}DATOS_IDENTIFICATIVOS")]


def _op_not_implemented(body_el):
    return -2, "NO_IMPLEMENTADO_AUN", []


HANDLERS = {
    "crearCentro": _op_crear_centro,
    "obtenerDatosCentro": _op_obtener_datos_centro,
    "crearAccion": _op_not_implemented,
    "obtenerAccion": _op_not_implemented,
    "obtenerListaAcciones": _op_not_implemented,
    "eliminarAccion": _op_not_implemented,
}

RESPONSE_WRAPPER = {
    "crearCentro": ("crearCentroResponse", "RESPUESTA_DATOS_CENTRO"),
    "obtenerDatosCentro": ("obtenerDatosCentroResponse", "RESPUESTA_DATOS_CENTRO"),
    "crearAccion": ("crearAccionResponse", "RESPUESTA_OBT_ACCION"),
    "obtenerAccion": ("obtenerAccionResponse", "RESPUESTA_OBT_ACCION"),
    "obtenerListaAcciones": ("obtenerListaAccionesResponse", "RESPUESTA_OBT_LISTA_ACCIONES"),
    "eliminarAccion": ("eliminarAccionResponse", "RESPUESTA_ELIMINAR_ACCION"),
}


# ---------------------------------------------------------------------------
# Envelope building
# ---------------------------------------------------------------------------

def _soap_envelope(body_children):
    nsmap = {"soapenv": SOAPENV}
    envelope = etree.Element(_q(SOAPENV, "Envelope"), nsmap=nsmap)
    etree.SubElement(envelope, _q(SOAPENV, "Header"))
    body = etree.SubElement(envelope, _q(SOAPENV, "Body"))
    for child in body_children:
        body.append(child)
    return envelope


def _build_success_response(operation, codigo_retorno, etiqueta_error, extra_els):
    response_tag, wrapper_tag = RESPONSE_WRAPPER[operation]

    op_el = etree.Element(_q(IMPL, response_tag), nsmap={"impl": IMPL})
    wrapper_el = etree.SubElement(op_el, _q(SALIDA, wrapper_tag), nsmap={"salida": SALIDA})
    etree.SubElement(wrapper_el, "CODIGO_RETORNO").text = str(codigo_retorno)
    etiqueta = etree.SubElement(wrapper_el, "ETIQUETA_ERROR")
    if etiqueta_error:
        etiqueta.text = etiqueta_error
    for el in extra_els:
        wrapper_el.append(el)

    return _soap_envelope([op_el])


def _build_fault_response(fault: SoapFault):
    fault_el = etree.Element(_q(SOAPENV, "Fault"))
    etree.SubElement(fault_el, "faultcode").text = fault.faultcode
    etree.SubElement(fault_el, "faultstring").text = fault.faultstring
    return _soap_envelope([fault_el])


def _xml_response(envelope, status=200):
    xml_bytes = etree.tostring(envelope, xml_declaration=True, encoding="UTF-8")
    return HttpResponse(xml_bytes, content_type="text/xml; charset=utf-8", status=status)


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def soap_endpoint(request):
    try:
        try:
            envelope = etree.fromstring(request.body)
        except etree.XMLSyntaxError as e:
            raise SoapFault(f"XML mal formado: {e}")

        _check_ws_security(envelope)

        body = envelope.find(_q(SOAPENV, "Body"))
        if body is None or len(body) == 0:
            raise SoapFault("soapenv:Body vacío o ausente.")

        op_el = body[0]
        operation = etree.QName(op_el).localname
        if operation not in OPERATIONS:
            raise SoapFault(f"Operación desconocida: {operation}")

        handler = HANDLERS[operation]
        codigo_retorno, etiqueta_error, extra_els = handler(op_el)

        response_envelope = _build_success_response(operation, codigo_retorno, etiqueta_error, extra_els)
        return _xml_response(response_envelope)

    except SoapFault as fault:
        return _xml_response(_build_fault_response(fault), status=500)
