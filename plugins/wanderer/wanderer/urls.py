from django.urls import path

from . import views

app_name = "wanderer"

urlpatterns = [
    path("", views.index, name="index"),
]
