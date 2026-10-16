import gzip
import json

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cards import classifiers
from cards.db_router import CARD_DATABASE_ALIAS
from cards.models import Archetype, Card, Role, Tag, Tagging

HEADERS = {"User-Agent": "MTG-DeckBuilder/1.0", "Accept": "application/json"}
BATCH = 2000


def fetch_bulk(bulk_type):
    info = requests.get("https://api.scryfall.com/bulk-data", headers=HEADERS, timeout=60)
    info.raise_for_status()
    entry = next((b for b in info.json()["data"] if b["type"] == bulk_type), None)
    if entry is None:
        raise CommandError(f"Could not find '{bulk_type}' bulk data")

    response = requests.get(entry["jsonl_download_uri"], headers=HEADERS, timeout=600)
    response.raise_for_status()
    content = response.content
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
    text = content.decode("utf-8")

    # The file may be a single JSON array or JSONL.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def bulk_insert(model, objects):
    manager = model.objects.db_manager(CARD_DATABASE_ALIAS)
    for i in range(0, len(objects), BATCH):
        manager.bulk_create(objects[i:i + BATCH])


class Command(BaseCommand):
    help = "Rebuild the card, tag, role and archetype tables from Scryfall bulk data."

    def handle(self, *args, **options):
        self.stdout.write("Downloading Scryfall oracle cards...")
        scryfall_cards = fetch_bulk("oracle_cards")
        self.stdout.write("Downloading Scryfall oracle tags...")
        scryfall_tags = fetch_bulk("oracle_tags")

        card_rows = []
        for card in scryfall_cards:
            # Stickers are not played in decklists; only Commander-legal cards are kept.
            if card.get("type_line") == "Stickers":
                continue
            if card.get("legalities", {}).get("commander") != "legal":
                continue
            card_rows.append({
                "scryfall_id": card["id"],
                "oracle_id": card.get("oracle_id"),
                "name": card["name"],
                "mana_cost": card.get("mana_cost"),
                "cmc": card.get("cmc"),
                "type_line": card.get("type_line"),
                "keywords": ",".join(card.get("keywords", [])),
                "oracle_text": card.get("oracle_text"),
                "power": card.get("power"),
                "toughness": card.get("toughness"),
                "colors": ",".join(card.get("colors", [])),
                "color_identity": ",".join(card.get("color_identity", [])),
            })

        tag_objects = []
        tagging_objects = []
        tags_by_oracle_id = {}
        for tag in scryfall_tags:
            label = tag.get("label") or ""
            if label.startswith("cycle-"):
                continue
            tag_objects.append(Tag(
                id=tag["id"],
                slug=tag.get("slug"),
                label=label,
                description=tag.get("description"),
                parent_ids=",".join(tag.get("parent_ids") or []),
                child_ids=",".join(tag.get("child_ids") or []),
                aliases=",".join(tag.get("aliases") or []),
            ))
            for tagging in tag.get("taggings", []):
                oracle_id = tagging.get("oracle_id")
                if not oracle_id:
                    continue
                tagging_objects.append(Tagging(
                    tag_id=tag["id"],
                    oracle_id=oracle_id,
                    weight=tagging.get("weight"),
                    annotation=tagging.get("annotation"),
                ))
                tags_by_oracle_id.setdefault(oracle_id, set()).add(label)

        with transaction.atomic(using=CARD_DATABASE_ALIAS):
            for model in (Tagging, Tag, Role, Archetype, Card):
            model.objects.using(CARD_DATABASE_ALIAS).all().delete()

            bulk_insert(Card, [Card(**row) for row in card_rows])
            bulk_insert(Tag, tag_objects)
            bulk_insert(Tagging, tagging_objects)

            ids = dict(Card.objects.using(CARD_DATABASE_ALIAS).values_list("scryfall_id", "id"))
            roles, archetypes = [], []
            for row in card_rows:
                tag_set = tags_by_oracle_id.get(row["oracle_id"], set())
                card_pk = ids[row["scryfall_id"]]

                role_scores = classifiers.combine(
                    classifiers.classify_tag_role(tag_set),
                    classifiers.classify_card_role(row),
                    classifiers.ROLE_NAMES,
                )
                roles.append(Role(card_id=card_pk, **role_scores))

                archetype_scores = classifiers.combine(
                    classifiers.classify_tag_archetype(tag_set),
                    classifiers.classify_card_archetype(row),
                    classifiers.ARCHETYPE_NAMES,
                )
                archetypes.append(Archetype(card_id=card_pk, **archetype_scores))

            bulk_insert(Role, roles)
            bulk_insert(Archetype, archetypes)

        self.stdout.write(self.style.SUCCESS(
            f"Built {len(card_rows)} cards, {len(tag_objects)} tags, "
            f"{len(tagging_objects)} taggings, roles and archetypes."
        ))
