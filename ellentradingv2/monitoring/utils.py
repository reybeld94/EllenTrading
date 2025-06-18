from monitoring.models import SystemLog
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async

@sync_to_async
def log_event(message, source="core", level="INFO"):
    log = SystemLog.objects.create(message=message, source=source, level=level)

    channel_layer = get_channel_layer()
    payload = {
        "type": "send_log",
        "log": {
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "level": log.level,
            "source": log.source,
            "message": log.message
        }
    }
    async_to_sync(channel_layer.group_send)("log_stream", payload)


