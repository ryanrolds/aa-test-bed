"""App URLs"""

# Django
from django.urls import path

# Wanderer Leaderboard
from wanderer_leaderboard import views

app_name: str = "wanderer_leaderboard"

urlpatterns = [
    path("", views.index, name="index"),
]
