from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.requests.services import run_execute


class ExecuteSerializer(serializers.Serializer):
    text = serializers.CharField()
    confirm = serializers.BooleanField(required=False, default=False)


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, _request: Request) -> Response:
        return Response({"status": "ok", "service": "econ"})


class ExecuteView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: Request) -> Response:
        serializer = ExecuteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        debug = request.query_params.get("debug", "").lower() in {"1", "true", "yes"}
        result = run_execute(
            serializer.validated_data["text"],
            debug=debug,
            confirmed=bool(serializer.validated_data.get("confirm")),
        )
        payload: dict[str, object] = {
            "status": result.status,
            "intent": result.intent,
            "entity": result.entity,
            "flow_id": result.flow_id,
            "execution_time_ms": result.execution_time_ms,
            "llm_used": result.llm_used,
            "message": result.message,
            "argv": result.argv,
        }
        if debug:
            payload["debug"] = result.debug
        status_code = 200
        if result.status == "error":
            status_code = 503
        elif result.status == "denied":
            status_code = 403
        elif result.status == "confirm_required":
            status_code = 202
        elif result.status == "failed":
            status_code = 422
        return Response(payload, status=status_code)
