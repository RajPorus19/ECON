from datetime import date

from celery import shared_task
from django.db.models import Avg, Count, F, Q, Sum

from apps.analytics.models import DailyMetric
from apps.requests.models import RequestLog


@shared_task
def ping() -> str:
    return "pong"


@shared_task
def record_request_metric(request_id: int) -> str:
    log = RequestLog.objects.filter(pk=request_id).first()
    if log is None:
        return "missing"
    day = log.created_at.date() if log.created_at else date.today()
    metric, _ = DailyMetric.objects.get_or_create(day=day)
    metric.requests_total = int(metric.requests_total) + 1
    if log.llm_used:
        metric.llm_calls_total = int(metric.llm_calls_total) + 1
    if log.cache_layer:
        metric.cache_hits_total = int(metric.cache_hits_total) + 1
    if log.status == "success":
        metric.execution_success_total = int(metric.execution_success_total) + 1
    elif log.status == "failed":
        metric.execution_failure_total = int(metric.execution_failure_total) + 1
    metric.tokens_consumed_total = int(metric.tokens_consumed_total) + int(
        log.prompt_tokens + log.completion_tokens
    )
    metric.tokens_saved_total = int(metric.tokens_saved_total) + int(log.tokens_saved)
    metric.save()
    return "ok"


@shared_task
def recompute_daily_metrics(day_iso: str | None = None) -> str:
    target = date.fromisoformat(day_iso) if day_iso else date.today()
    qs = RequestLog.objects.filter(created_at__date=target)
    agg = qs.aggregate(
        requests_total=Count("id"),
        llm_calls_total=Count("id", filter=Q(llm_used=True)),
        cache_hits_total=Count("id", filter=~Q(cache_layer="")),
        execution_success_total=Count("id", filter=Q(status="success")),
        execution_failure_total=Count("id", filter=Q(status="failed")),
        tokens_consumed_total=Sum(F("prompt_tokens") + F("completion_tokens")),
        tokens_saved_total=Sum("tokens_saved"),
        avg_latency_ms=Avg("duration_ms"),
    )
    DailyMetric.objects.update_or_create(
        day=target,
        defaults={
            "requests_total": agg["requests_total"] or 0,
            "llm_calls_total": agg["llm_calls_total"] or 0,
            "cache_hits_total": agg["cache_hits_total"] or 0,
            "execution_success_total": agg["execution_success_total"] or 0,
            "execution_failure_total": agg["execution_failure_total"] or 0,
            "tokens_consumed_total": int(agg["tokens_consumed_total"] or 0),
            "tokens_saved_total": int(agg["tokens_saved_total"] or 0),
            "avg_latency_ms": int(agg["avg_latency_ms"] or 0),
        },
    )
    return "ok"
