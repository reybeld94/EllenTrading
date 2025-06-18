from django.db import models

class SystemLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, default="INFO")  # INFO, ERROR, DEBUG, etc.
    source = models.CharField(max_length=100)  # 'backtest', 'runner', 'risk', etc.
    message = models.TextField()

    def __str__(self):
        return f"[{self.timestamp}] {self.level} - {self.source}: {self.message[:50]}"
