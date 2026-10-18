import math

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
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


def score_lands(commander, cards):
    """Return [(card, score)] for lands sorted by descending synergy with the commander."""
    commander_colors = {c.strip() for c in commander.color_identity.split(",") if c.strip()}
    scored = []
    for card in cards:
        text = card.oracle_text or ""
        lowered = text.lower()
        score = 0.3

        basic_subtypes = {"Plains", "Island", "Swamp", "Mountain", "Forest"}
        

        # Dual/tri lands with basic land types fix mana and are fetchable.

        score += 0.15 * len(_subtypes(card) & basic_subtypes)

        if "Basic" in (card.type_line or ""):
            score += 0.2

        if "enters tapped" in lowered or "enters the battlefield tapped" in lowered:
            if "unless" in lowered:
                score -= 0.05
            else:
                score -= 0.15

        if "any color" in lowered:
            score += 0.25
        else:
            produced = sum(1 for c in commander_colors if "{%s}" % c in text)
            if commander_colors:
                score += 0.3 * produced / len(commander_colors)

        if "scry" in lowered or "surveil" in lowered:
            score += 0.1

        if "search your library" in lowered:
            score += 0.1

        if "spend this only" in lowered:
            score -= 0.1

        scored.append((card, round(min(max(score, 0.0), 1.0), 3)))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def score_with_lands(commander, cards):
    """Score cards by synergy; lands get 30% synergy score and 70% land score."""
    
    cards = list(cards)

    land_rate = 0.65
    synergy_rate = 0.35

    synergy = score_synergy(commander, cards)
    lands = [card for card, _ in synergy if "Land" in (card.type_line or "").split()]
    land_scores = dict(score_lands(commander, lands))
    blended = [
        (card, round(synergy_rate * score + land_rate * land_scores[card], 3)) if card in land_scores else (card, score)
        for card, score in synergy
    ]
    blended.sort(key=lambda item: item[1], reverse=True)
    return blended


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

DECK_GROUP_LIMITS = {
    "Creatures": 32,
    "Artifacts": 8,
    "Enchantments": 5,
    "Instants": 10,
    "Sorceries": 5,
    "Planeswalkers": 3,
    "Lands": 36,
}

def deck_builder(request):
    return render(request, "decks/deck_builder.html")

def build_deck(request):
    return render(request, "decks/build_deck.html")

def _group_cards(scored_cards, limits=None):
    grouped_cards = {group_name: [] for group_name, _ in CARD_TYPE_GROUPS}
    for card, score in scored_cards:
        card_types = (card.type_line or "").split()
        for group_name, card_type in CARD_TYPE_GROUPS:
            if card_type in card_types:
                grouped_cards[group_name].append({"card": card, "score": score})
                break
    groups = [
        {"name": name, "cards": cards[:limits.get(name, 0)] if limits is not None else cards}
        for name, cards in grouped_cards.items()
    ]
    return [group for group in groups if group["cards"]]

def signup(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("home")
    return render(request, "registration/signup.html", {"form": form})

@login_required
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
        deck = Deck.objects.create(name=name[:100], commander=commander, owner_id=request.user.pk)
        Deck_Cards.objects.bulk_create([Deck_Cards(deck=deck, card_id=pk) for pk in card_pks])
    return redirect("deck_detail", deck_id=deck.pk)

@login_required
def saved_decks(request):
    decks = Deck.objects.filter(owner_id=request.user.pk).order_by("name")
    return render(request, "decks/saved_decks.html", {"decks": decks})

@login_required
@require_POST
def delete_deck(request, deck_id):
    deck = get_object_or_404(Deck, pk=deck_id, owner_id=request.user.pk)
    deck.delete()
    return redirect("saved_decks")

@login_required
def deck_detail(request, deck_id):
    deck = get_object_or_404(Deck, pk=deck_id, owner_id=request.user.pk)
    cards_qs = Card.objects.using(CARD_DATABASE_ALIAS).select_related("role", "archetype")
    commander = cards_qs.get(pk=deck.commander_id)
    card_ids = list(Deck_Cards.objects.filter(deck=deck).values_list("card_id", flat=True))
    return render(request, "decks/deck_detail.html", {
        "deck": deck,
        "commander": commander,
        "card_groups": _group_cards(score_synergy(commander, cards_qs.filter(pk__in=card_ids))),
    })

def get_valid_cards(request):

    query = request.GET.get("q", "").strip()
    valid_cards = []
    card_groups = []
    error = ""
    commander = None
    if not query:
        error = "Please enter a commander."
    else:
        commander = (
            Card.objects.using(CARD_DATABASE_ALIAS)
            .select_related("role", "archetype")
            .filter(name__icontains=query)
            .first()
        )

    if error:
        pass
    elif not commander:
        error = "Commander not found."
    elif commander.type_line and "Legendary" in commander.type_line and (
        "Creature" in commander.type_line or "Artifact" in commander.type_line
    ):
        commander_identity = {
            color.strip()
            for color in commander.color_identity.split(",")
            if color.strip()
        }
        valid_cards = score_with_lands(
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

        card_groups = _group_cards(valid_cards, limits=DECK_GROUP_LIMITS)

    else:
        error = "Invalid commander. Choose a legendary creature or artifact."

    return render(request, "decks/build_deck.html", {
        "query": query,
        "valid_cards": valid_cards,
        "commander": commander if card_groups else None,
        "card_groups": card_groups,
        "error": error,
    })



