from datetime import date, timedelta

from django.db.models import Avg, Count, F, Q, Sum
from django.http import StreamingHttpResponse
from django.views import View
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import DailyMetric
from apps.requests.models import RequestLog
from core.events import EVENT_CHANNEL


def _today_stats() -> dict:
    today = date.today()
    qs = RequestLog.objects.filter(created_at__date=today)
    agg = qs.aggregate(
        requests_total=Count("id"),
        llm_calls=Count("id", filter=Q(llm_used=True)),
        tokens_saved=Sum("tokens_saved"),
        tokens_consumed=Sum(F("prompt_tokens") + F("completion_tokens")),
        avg_latency=Avg("duration_ms"),
    )
    total = int(agg["requests_total"] or 0)
    llm = int(agg["llm_calls"] or 0)
    avoidance = 0.0 if total == 0 else round(100.0 * (total - llm) / total, 1)
    return {
        "day": str(today),
        "requests_today": total,
        "llm_calls": llm,
        "llm_avoidance": avoidance,
        "tokens_saved": int(agg["tokens_saved"] or 0),
        "tokens_consumed": int(agg["tokens_consumed"] or 0),
        "average_latency_ms": int(agg["avg_latency"] or 0),
        "tokens_saved_are_estimated": True,
    }


class StatsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, _request: Request) -> Response:
        payload = _today_stats()
        payload["history"] = list(
            DailyMetric.objects.filter(day__gte=date.today() - timedelta(days=14)).values()
        )
        return Response(payload)


class OptimizationsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, _request: Request) -> Response:
        rows = (
            RequestLog.objects.exclude(intent__isnull=True)
            .values("intent__name")
            .annotate(
                total=Count("id"),
                llm=Count("id", filter=Q(llm_used=True)),
            )
            .order_by("-total")
        )
        items = []
        for row in rows:
            total = row["total"] or 0
            llm = row["llm"] or 0
            avoidance = 0.0 if total == 0 else round(100.0 * (total - llm) / total, 1)
            items.append(
                {
                    "intent": row["intent__name"],
                    "total": total,
                    "llm_calls": llm,
                    "llm_avoidance": avoidance,
                }
            )
        return Response({"intents": items})


class EventStreamView(View):
    """SSE over Django ASGI.

    Source: https://docs.djangoproject.com/en/6.1/ref/request-response/#streaminghttpresponse
    """

    def get(self, request):
        def stream():
            yield "retry: 2000\n\n"
            try:
                import redis
                from django.conf import settings

                url = str(settings.ECON.get("REDIS_URL") or settings.CELERY_RESULT_BACKEND)
                client = redis.from_url(url)
                pubsub = client.pubsub()
                pubsub.subscribe(EVENT_CHANNEL)
                while True:
                    message = pubsub.get_message(timeout=1.0, ignore_subscribe_messages=True)
                    if message and message.get("type") == "message":
                        data = message.get("data")
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")
                        yield f"data: {data}\n\n"
                    else:
                        yield ": keepalive\n\n"
            except Exception:  # noqa: BLE001
                yield 'data: {"event":"stream.unavailable","payload":{}}\n\n'

        response = StreamingHttpResponse(stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
