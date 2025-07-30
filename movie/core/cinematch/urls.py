from django.urls import path
from .views import dashboard_metrics

urlpatterns = [
    path("metrics/", dashboard_metrics, name="dashboard-metrics"),
]
