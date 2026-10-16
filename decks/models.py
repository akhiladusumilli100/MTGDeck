from django.db import models

# Create your models here.
class Deck(models.Model):
    name = models.CharField(max_length=100)
    # Plain id: decks live in cards_db while auth.User lives in the default DB.
    owner_id = models.PositiveIntegerField(null=True, db_index=True)
    commander = models.ForeignKey('cards.Card', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
            db_table = "deck"

    def __str__(self):
        return self.name

class Deck_Cards(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE)
    card = models.ForeignKey('cards.Card', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "deck_cards"

    def __str__(self):
        return f"{self.deck_id} - {self.card_id} ({self.quantity})"