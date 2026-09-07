from django.db import models


class DailyMetric(models.Model):
    """Placeholder for later analytics aggregation."""

    day = models.DateField(unique=True)
    requests_total = models.PositiveIntegerField(default=0)
    llm_calls_total = models.PositiveIntegerField(default=0)
    cache_hits_total = models.PositiveIntegerField(default=0)
    execution_success_total = models.PositiveIntegerField(default=0)
    execution_failure_total = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-day"]

    def __str__(self) -> str:
        return str(self.day)
