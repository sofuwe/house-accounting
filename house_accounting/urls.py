# from django.contrib import admin
# from django.urls import path
from django.contrib import admin
from django.urls import path

from charts.views import CurrentBalancesChartView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", CurrentBalancesChartView.as_view(), name="index"),
]
