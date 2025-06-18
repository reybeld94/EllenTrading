from django.urls import path
from monitoring import views

urlpatterns = [
    path("logs/", views.get_logs, name="get_logs"),
]
