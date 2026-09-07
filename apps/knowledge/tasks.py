from celery import shared_task
from django.conf import settings

from apps.knowledge.learning import apply_usage, persist_proposal, record_alias_candidate
from apps.requests.models import RequestLog
from core.llm import HermesProposal


@shared_task
def learn_from_execution(request_id: int) -> str:
    log = (
        RequestLog.objects.select_related("intent", "entity", "flow", "execution")
        .filter(pk=request_id)
        .first()
    )
    if log is None:
        return "missing"
    if log.status not in {"success", "failed"}:
        return "skipped"

    success = log.status == "success"
    intent = log.intent
    entity = log.entity
    flow = log.flow
    proposal = None
    if log.llm_used and log.proposal:
        try:
            proposal = HermesProposal.model_validate(log.proposal)
        except Exception:  # noqa: BLE001
            proposal = None

    if proposal and success:
        argv = list(log.execution.argv) if log.execution else []
        created = persist_proposal(proposal, argv)
        if created is not None:
            log.flow = created
            log.intent = created.intent or log.intent
            entity_node = created.nodes.filter(entity__isnull=False).first()
            if entity_node:
                log.entity = entity_node.entity
            log.save(update_fields=["flow", "intent", "entity"])
            flow = created
            intent = log.intent
            entity = log.entity

    apply_usage(intent=intent, entity=entity, flow=flow, success=success)

    required = int(str(settings.ECON.get("ALIAS_CONFIRMATIONS", 3)))
    if success and entity is not None and log.match_method in {"prefix", "fuzzy", "semantic"}:
        remainder = log.normalized_text
        if intent:
            for phrase in intent.aliases.values_list("normalized_phrase", flat=True):
                if remainder == phrase or remainder.startswith(f"{phrase} "):
                    remainder = remainder[len(phrase) :].strip()
                    break
        record_alias_candidate(
            remainder=remainder,
            entity=entity,
            success=True,
            required_confirmations=required,
        )

    from apps.analytics.tasks import record_request_metric

    record_request_metric.delay(request_id)
    return "learned"
