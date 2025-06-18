from django.http import JsonResponse
from monitoring.models import SystemLog
from django.utils.timezone import now, timedelta

def get_logs(request):
    limit = int(request.GET.get("limit", 200))
    source = request.GET.get("source")  # <-- 🚨 nuevo filtro por source

    since = now() - timedelta(hours=24)
    logs = SystemLog.objects.filter(timestamp__gte=since)

    if source:
        logs = logs.filter(source=source.lower())  # aseguramos que coincida en minúscula

    logs = logs.order_by("-timestamp")[:limit]

    data = [
        {
            "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "level": l.level,
            "source": l.source,
            "message": l.message
        }
        for l in logs
    ]

    return JsonResponse(data, safe=False)
