from django.contrib import admin
from .risk_settings import RiskSettings

@admin.register(RiskSettings)
class RiskSettingsAdmin(admin.ModelAdmin):
    list_display = ["name", "risk_pct", "min_notional", "conflict_threshold"]
