from django.urls import path
from . import views

urlpatterns = [
    path("deck_builder/", views.deck_builder, name="deck_builder"),
    path("deck_builder/build_deck/", views.build_deck, name="build_deck"),
    path("deck_builder/build_deck/get_valid_cards/", views.get_valid_cards, name="get_valid_cards"),
    path("deck_builder/build_deck/save_deck/", views.save_deck, name="save_deck"),
    path("deck_builder/saved_decks/", views.saved_decks, name="saved_decks"),
    path("deck_builder/saved_decks/<int:deck_id>/delete/", views.delete_deck, name="delete_deck"),
    path("deck_builder/saved_decks/<int:deck_id>/", views.deck_detail, name="deck_detail"),
]
