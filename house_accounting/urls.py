# from django.contrib import admin
# from django.urls import path
from django.contrib import admin
from django.urls import path, include

from charts.views import CurrentBalancesChartView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", CurrentBalancesChartView.as_view(), name="index"),
    path("export_action/", include("admin_export_action.urls", namespace="admin_export_action")),
]
