from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

STUB_ANSWER = (
    "El asistente de IA está temporalmente desactivado mientras se configura "
    "el proveedor. Vuelve a intentarlo más adelante."
)


@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def ai_warmup(request):
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def ai_ask(request):
    return Response({"ok": True, "answer": STUB_ANSWER})


@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def ai_help(request):
    return Response({"ok": True, "answer": STUB_ANSWER})
