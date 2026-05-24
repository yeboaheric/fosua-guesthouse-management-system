from django.urls import path

from shifts.views import handover_create, handover_detail, handover_list

urlpatterns = [
    path("", handover_list, name="handover-list"),
    path("new/", handover_create, name="handover-create"),
    path("<int:pk>/", handover_detail, name="handover-detail"),
]
