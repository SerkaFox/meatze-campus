# api/emails.py
"""
Plantillas de e-mail transaccional (PIN de acceso, etc).

HTML de tablas + estilos inline a propósito: es lo único que se
renderiza de forma consistente en Gmail/Outlook/Apple Mail. Nada de
JS — un botón "copiar" no funcionaría en ningún cliente de correo, así
que en su lugar el código se muestra grande, monoespaciado y con
espaciado entre letras para que sea fácil seleccionarlo con un
doble clic.
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

LOGO_URL = "https://curso.webimpulsa.es/static/files/logo.png"
BRAND = "Aurora Campus"


def _pin_html(pin: str) -> str:
    # sin espacios reales entre dígitos: el espaciado es solo visual
    # (CSS letter-spacing), así el código sigue siendo una sola
    # "palabra" y un doble clic lo selecciona entero.
    return f"""\
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0b1220;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b1220;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background:#111827;border-radius:20px;overflow:hidden;border:1px solid #1f2937;">

        <tr>
          <td align="center" style="background:linear-gradient(135deg,#1d4ed8,#0ea5e9);padding:28px 24px;">
            <img src="{LOGO_URL}" width="56" height="56" alt="{BRAND}" style="display:block;border-radius:14px;margin-bottom:10px;">
            <div style="color:#ffffff;font-size:18px;font-weight:800;letter-spacing:.01em;">{BRAND}</div>
          </td>
        </tr>

        <tr>
          <td style="padding:32px 28px 8px;color:#e5e7eb;font-size:15px;line-height:1.6;">
            Hola,<br><br>
            Usa este código para entrar en tu cuenta de {BRAND}. Es válido durante
            <strong style="color:#ffffff;">10 minutos</strong>.
          </td>
        </tr>

        <tr>
          <td align="center" style="padding:20px 28px 8px;">
            <div style="display:inline-block;background:#0b1220;border:1px solid #334155;border-radius:14px;padding:18px 26px;">
              <span style="font-family:'Courier New',Courier,monospace;font-size:34px;font-weight:800;
                           color:#7dd3fc;">{pin}</span>
            </div>
          </td>
        </tr>

        <tr>
          <td style="padding:8px 28px 28px;color:#9ca3af;font-size:12.5px;line-height:1.6;text-align:center;">
            Consejo: haz doble clic sobre el código para seleccionarlo entero y copiarlo.
          </td>
        </tr>

        <tr>
          <td style="padding:18px 28px;border-top:1px solid #1f2937;color:#6b7280;font-size:12px;line-height:1.6;">
            Si no has solicitado este código, puedes ignorar este correo con tranquilidad —
            nadie podrá acceder a tu cuenta sin él.
          </td>
        </tr>

      </table>
      <div style="color:#4b5563;font-size:11px;margin-top:16px;">
        {BRAND} · correo automático, no respondas a este mensaje.
      </div>
    </td></tr>
  </table>
</body>
</html>
"""


def _pin_text(pin: str) -> str:
    return (
        f"Hola,\n\n"
        f"Tu código de acceso a {BRAND} es: {pin}\n\n"
        f"Es válido durante 10 minutos.\n\n"
        f"Si no has solicitado este código, puedes ignorar este correo.\n\n"
        f"Un saludo,\nEquipo {BRAND}"
    )


def send_pin_email(email: str, pin: str) -> None:
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER
    msg = EmailMultiAlternatives(
        subject=f"Tu PIN de acceso a {BRAND}",
        body=_pin_text(pin),
        from_email=from_email,
        to=[email],
    )
    msg.attach_alternative(_pin_html(pin), "text/html")
    msg.send(fail_silently=False)
