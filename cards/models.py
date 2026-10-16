from django.db import models

from .classifiers import ARCHETYPE_NAMES, ROLE_NAMES


class Card(models.Model):
    scryfall_id = models.CharField(max_length=36, unique=True)
    oracle_id = models.CharField(max_length=36, null=True, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    mana_cost = models.CharField(max_length=100, null=True, blank=True)
    cmc = models.FloatField(null=True, blank=True)
    type_line = models.CharField(max_length=255, null=True, blank=True)
    keywords = models.TextField(blank=True, default="")
    oracle_text = models.TextField(null=True, blank=True)
    power = models.CharField(max_length=10, null=True, blank=True)
    toughness = models.CharField(max_length=10, null=True, blank=True)
    colors = models.CharField(max_length=20, blank=True, default="")
    color_identity = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        db_table = "card"

    def __str__(self):
        return self.name


class Tag(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    slug = models.CharField(max_length=255, null=True, blank=True)
    label = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    parent_ids = models.TextField(blank=True, default="")
    child_ids = models.TextField(blank=True, default="")
    aliases = models.TextField(blank=True, default="")

    class Meta:
        db_table = "tag"

    def __str__(self):
        return self.label or self.id


class Tagging(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="taggings")
    oracle_id = models.CharField(max_length=36, db_index=True)
    weight = models.CharField(max_length=50, null=True, blank=True)
    annotation = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "tagging"


class Role(models.Model):
    card = models.OneToOneField(Card, on_delete=models.CASCADE, related_name="role")

    # One 0.0-1.0 score field per name in ROLE_NAMES.
    for _name in ROLE_NAMES:
        locals()[_name] = models.FloatField(default=0.0)
    del _name

    class Meta:
        db_table = "role"

    def __str__(self):
        return f"Role scores for {self.card}"


class Archetype(models.Model):
    card = models.OneToOneField(Card, on_delete=models.CASCADE, related_name="archetype")

    # One 0.0-1.0 score field per name in ARCHETYPE_NAMES.
    for _name in ARCHETYPE_NAMES:
        locals()[_name] = models.FloatField(default=0.0)
    del _name

    class Meta:
        db_table = "archetype"

    def __str__(self):
        return f"Archetype scores for {self.card}"
