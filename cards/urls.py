from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("card_search/", views.card_search, name="card_search"),
    path("get_card_info/", views.get_card_info, name="get_card_info"),
]