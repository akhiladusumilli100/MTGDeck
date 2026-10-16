import math

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cards.classifiers import ARCHETYPE_NAMES, ROLE_NAMES
from cards.db_router import CARD_DATABASE_ALIAS
from cards.models import Card, Tagging

from .models import Deck, Deck_Cards

SUBTYPE_BONUS = 0.25
TYPAL_PREFIX = "typal-"


def _typal_types(card):
    slugs = (
        Tagging.objects.using(CARD_DATABASE_ALIAS)
        .filter(oracle_id=card.oracle_id, tag__slug__startswith=TYPAL_PREFIX)
        .values_list("tag__slug", flat=True)
    )
    return {slug[len(TYPAL_PREFIX):].lower() for slug in slugs} if card.oracle_id else set()

def _matches_typal(card, typal_types):
    if not typal_types:
        return False
    if "changeling" in (card.keywords or "").lower():
        return True
    return bool(typal_types & {s.lower() for s in _subtypes(card)})


def _vector(card, relation, names):
    related = getattr(card, relation, None)
    return [getattr(related, name, 0.0) if related else 0.0 for name in names]


def _cosine(a, b):
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if not norm:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / norm

def _subtypes(card):
    type_line = card.type_line or ""
    if "—" not in type_line:
        return set()
    return set(type_line.split("—", 1)[1].split())

def score_synergy(commander, cards):
    """Return [(card, score)] sorted by descending synergy with the commander.

    Score = mean of role and archetype cosine similarities, plus SUBTYPE_BONUS
    if the commander has a typal-<type> tag and the card has that subtype or changeling.
    """
    cmd_roles = _vector(commander, "role", ROLE_NAMES)
    cmd_archetypes = _vector(commander, "archetype", ARCHETYPE_NAMES)
    typal_types = _typal_types(commander)

    scored = []
    for card in cards:
        score = 0
        score += 0.45 * _cosine(cmd_roles, _vector(card, "role", ROLE_NAMES)) 
        score += 0.55 * _cosine(cmd_archetypes, _vector(card, "archetype", ARCHETYPE_NAMES))
        
        if _matches_typal(card, typal_types):
            score += SUBTYPE_BONUS
        scored.append((card, round(score, 3)))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored

CARD_TYPE_GROUPS = (
    ("Creatures", "Creature"),
    ("Instants", "Instant"),
    ("Sorceries", "Sorcery"),
    ("Artifacts", "Artifact"),
    ("Enchantments", "Enchantment"),
    ("Planeswalkers", "Planeswalker"),
    ("Battles", "Battle"),
    ("Lands", "Land"),
)

def deck_builder(request):
    return render(request, "decks/deck_builder.html")

def build_deck(request):
    return render(request, "decks/build_deck.html")

def _group_cards(scored_cards, limit=None):
    grouped_cards = {group_name: [] for group_name, _ in CARD_TYPE_GROUPS}
    for card, score in scored_cards:
        card_types = (card.type_line or "").split()
        for group_name, card_type in CARD_TYPE_GROUPS:
            if card_type in card_types:
                grouped_cards[group_name].append({"card": card, "score": score})
                break
    return [
        {"name": group_name, "cards": group_cards[:limit]}
        for group_name, group_cards in grouped_cards.items()
        if group_cards
    ]

@require_POST
def save_deck(request):
    name = request.POST.get("deck_name", "").strip()
    commander = Card.objects.using(CARD_DATABASE_ALIAS).filter(pk=request.POST.get("commander_id")).first()
    if not name or not commander:
        return redirect("build_deck")

    card_pks = Card.objects.using(CARD_DATABASE_ALIAS).filter(
        pk__in=request.POST.getlist("card_ids")
    ).values_list("pk", flat=True)
    with transaction.atomic():
        deck = Deck.objects.create(name=name[:100], commander=commander)
        Deck_Cards.objects.bulk_create([Deck_Cards(deck=deck, card_id=pk) for pk in card_pks])
    return redirect("deck_detail", deck_id=deck.pk)

def saved_decks(request):
    return render(request, "decks/saved_decks.html", {"decks": Deck.objects.order_by("name")})

@require_POST
def delete_deck(request, deck_id):
    deck = get_object_or_404(Deck, pk=deck_id)
    deck.delete()
    return redirect("saved_decks")

def deck_detail(request, deck_id):
    deck = get_object_or_404(Deck, pk=deck_id)
    cards_qs = Card.objects.using(CARD_DATABASE_ALIAS).select_related("role", "archetype")
    commander = cards_qs.get(pk=deck.commander_id)
    card_ids = list(Deck_Cards.objects.filter(deck=deck).values_list("card_id", flat=True))
    return render(request, "decks/deck_detail.html", {
        "deck": deck,
        "commander": commander,
        "card_groups": _group_cards(score_synergy(commander, cards_qs.filter(pk__in=card_ids))),
    })

def get_valid_cards(request):

    query = request.GET.get("q", "")
    valid_cards = []
    card_groups = []
    error = ""
    commander = (
        Card.objects.using(CARD_DATABASE_ALIAS)
        .select_related("role", "archetype")
        .filter(name__icontains=query)
        .first()
    )

    if not commander:
        error = "Commander not found."
    elif commander.type_line and "Legendary" in commander.type_line and (
        "Creature" in commander.type_line or "Artifact" in commander.type_line
    ):
        commander_identity = {
            color.strip()
            for color in commander.color_identity.split(",")
            if color.strip()
        }
        valid_cards = score_synergy(
            commander,
            [
                card
                for card in Card.objects.using(CARD_DATABASE_ALIAS)
                .select_related("role", "archetype")
                .iterator()
                if {
                    color.strip()
                    for color in card.color_identity.split(",")
                    if color.strip()
                }.issubset(commander_identity) and card != commander
            ],
        )

        card_groups = _group_cards(valid_cards, limit=15)

    else:
        error = "Invalid commander. Choose a legendary creature or artifact."

    return render(request, "decks/build_deck.html", {
        "query": query,
        "valid_cards": valid_cards,
        "commander": commander if card_groups else None,
        "card_groups": card_groups,
        "error": error,
    })



