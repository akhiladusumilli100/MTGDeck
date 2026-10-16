from django.shortcuts import render

from .models import Card, Tagging

RESULT_LIMIT = 50


def home(request):
    return render(request, "cards/home.html")

def card_search(request):
    query = request.GET.get("q", "").strip()
    cards = []
    truncated = False
    if query:
        name_results = list(
            Card.objects.filter(name__icontains=query).order_by("name")[: RESULT_LIMIT + 1]
        )
        text_limit = RESULT_LIMIT + 1 - len(name_results)
        text_results = []
        if text_limit > 0:
            text_results = list(
                Card.objects.filter(oracle_text__icontains=query)
                .exclude(name__icontains=query)
                .order_by("name")[:text_limit]
            )
        results = name_results + text_results
        truncated = len(results) > RESULT_LIMIT
        cards = results[:RESULT_LIMIT]
    return render(request, "cards/card_search.html", {"query": query, "cards": cards, "truncated": truncated})

def get_card_info(request):
    query = request.GET.get("q", "").strip()
    card_id = request.GET.get("id", "").strip()
    card = None
    if card_id:
        card = Card.objects.filter(scryfall_id=card_id).first()
    elif query:
        card = Card.objects.filter(name__iexact=query).order_by("scryfall_id").first()
    tags = []
    if card and card.oracle_id:
        tags = sorted(
            {
                tagging.tag.label or tagging.tag.slug or tagging.tag.id
                for tagging in Tagging.objects.filter(oracle_id=card.oracle_id).select_related("tag")
            }
        )
    return render(request, "cards/card_info.html", {"query": query, "card": card, "tags": tags})