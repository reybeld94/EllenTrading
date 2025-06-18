from core.models.enums import *


class OpenStrategy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    confidence_threshold = models.IntegerField(default=70)
    auto_execute = models.BooleanField(default=False)
    score = models.IntegerField(default=1)
    performance_rate = models.FloatField(blank=True, null=True)  # será asignado después
    validity_minutes = models.IntegerField(default=60)
    required_bars = models.PositiveIntegerField(default=50)
    execution_mode = models.CharField(
        max_length=10,
        choices=ExecutionMode.choices,
        default=ExecutionMode.SIMULATED
    )

    priority = models.CharField(
        max_length=10,
        choices=PriorityLevel.choices,
        default=PriorityLevel.PRIMARY
    )

    timeframe = models.CharField(
        max_length=5,
        choices=Timeframe.choices,
        default=Timeframe.ONE_MIN
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} [{self.get_priority_display()}]"