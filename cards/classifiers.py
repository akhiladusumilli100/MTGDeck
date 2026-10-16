import re

# Calculates the roles and archetype classifications for cards using tags dbs


ROLE_NAMES = [
    "ramp", "mana_fixing", "card_draw", "card_advantage", "card_selection", "tutor",
    "spot_removal", "board_wipe", "counterspell", "protection", "graveyard_hate",
    "recursion", "graveyard_filling",
    "sacrifice_outlet", "sacrifice_payoff", "death_payoff",
    "token_generator", "token_payoff",
    "blink", "etb_payoff",
    "discard_outlet", "discard_payoff",
    "counter_generator", "counter_payoff",
    "land_synergy", "artifact_synergy", "equipment_synergy",
    "enchantment_synergy", "creature_synergy", "spell_synergy",
    "win_condition", "finisher",
    "high_cmc", "low_cmc", "high_power", "low_power", "high_toughness", "low_toughness",
]

ARCHETYPE_NAMES = [
    "voltron", "tokens", "aggro", "midrange", "tribal",
    "reanimator", "aristocrats", "sacrifice", "spellslinger",
    "blink", "enchantress", "artifacts", "counters", "planeswalker",
    "landfall", "treasures", "clues", "food", "control", "stax",
    "group_hug", "combo",
]


def _matcher(text):
    def matches(*patterns):
        return any(re.search(pattern, text) for pattern in patterns)
    return matches


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_card_role(card):
    """Return a 0.0-1.0 score per role from a card's Oracle text and stats."""
    text = re.sub(r"\s+", " ", (card.get("oracle_text") or "").lower())
    type_line = (card.get("type_line") or "").lower()
    matches = _matcher(text)

    cmc = _number(card.get("cmc"))
    power = _number(card.get("power"))
    toughness = _number(card.get("toughness"))

    roles = {role: 0.0 for role in ROLE_NAMES}

    if matches(r"\badd\s+\{", r"\bproduce(s)?\s+\{", r"\bcreate(s)?\s+a treasure"):
        roles["ramp"] = 1.0
    if matches(r"\bsearch your library for\b[^.]*\b(basic )?land\b"):
        roles["ramp"] = max(roles["ramp"], 0.9)
    if matches(r"\btreasure tokens?\b"):
        roles["ramp"] = max(roles["ramp"], 0.8)

    if matches(r"\bany color\b", r"\bcolors? of your choice\b", r"\bchoose a color\b"):
        roles["mana_fixing"] = 1.0

    if matches(r"\bdraw\s+(a|one|one or more|two|three|four|five|six|seven|\d+) cards?\b", r"\bdraw cards?\b"):
        roles["card_draw"] = 1.0
    if matches(r"\bdraw\s+cards?\s+equal to\b", r"\bdraw\s+that many cards?\b"):
        roles["card_draw"] = 1.0

    if matches(r"\bscry\b"):
        roles["card_selection"] = 0.8
    if matches(r"\bsurveil\b"):
        roles["card_selection"] = 0.8
    if matches(r"\blook at the top\b", r"\breveal the top\b"):
        roles["card_selection"] = max(roles["card_selection"], 0.6)

    if matches(r"\bsearch your library for\b[^.]*\b(card|permanent|creature|artifact|enchantment|planeswalker|spell)\b"):
        roles["tutor"] = 1.0

    removal_patterns = ["destroy target", "exile target", "target creature gets -", "target permanent gets -"]
    if matches(*(re.escape(p) for p in removal_patterns), r"\btarget\b[^.]*\bgets?\s+-\d+/-\d+\b"):
        roles["spot_removal"] = 1.0

    wipe_patterns = ["destroy all", "exile all"]
    if matches(*(re.escape(p) for p in wipe_patterns), r"\b(each|all)\b[^.]*\b(creature|permanent|artifact|enchantment|opponent|player)s?\b[^.]*\b(sacrifice|destroy|exile|return|discard)\b"):
        roles["board_wipe"] = 1.0

    if matches(r"\bcounter target\b", r"\bcounter all\b"):
        roles["counterspell"] = 1.0

    protection_patterns = ["hexproof", "shroud", "indestructible", "protection from", "phase out", "can't be the target"]
    if matches(*(re.escape(p) for p in protection_patterns), r"\bgrant(s)?\b[^.]*\bhexproof\b", r"\bgrant(s)?\b[^.]*\bindestructible\b"):
        roles["protection"] = 1.0

    graveyard_hate_patterns = [
        "exile target card from a graveyard",
        "exile a card from a graveyard",
        "exile all cards from graveyards",
        "exile all graveyards",
    ]
    if matches(*(re.escape(p) for p in graveyard_hate_patterns), r"\bexile\b[^.]*\bgraveyard(s)?\b", r"\bgraveyard(s)?\b[^.]*\bexile\b"):
        roles["graveyard_hate"] = 1.0

    recursion_patterns = [
        "return target creature card from your graveyard",
        r"target creature card in (your|a|an opponent's) graveyard",
        "return target permanent card from your graveyard",
        "return target card from your graveyard",
        "put target creature card from your graveyard",
        r"return .* from your graveyard",
    ]
    if matches(*recursion_patterns):
        roles["recursion"] = 1.0

    if matches(r"\bmill(s|ed|ing)?\b", r"\bput the top\b[^.]*\bgraveyard\b"):
        roles["graveyard_filling"] = 1.0
    if matches(r"\bdiscard\b[^.]*\bcard(s)?\b"):
        roles["graveyard_filling"] = max(roles["graveyard_filling"], 0.5)
    if matches(r"\bsurveil\b"):
        roles["graveyard_filling"] = max(roles["graveyard_filling"], 0.5)

    if matches(r"\bsacrifice\b[^.:]*\b(creature|permanent|artifact|token)\b\s*:"):
        roles["sacrifice_outlet"] = 1.0
    if matches(r"\bwhenever\b[^.]*\byou sacrifice\b", r"\bwhenever\b[^.]*\bis sacrificed\b"):
        roles["sacrifice_payoff"] = 1.0
    if matches(r"\bwhenever\b[^.]*\b(creature|another creature|this creature)\b[^.]*\bdies\b"):
        roles["death_payoff"] = 1.0

    if matches(r"\bcreate(s)?\b[^.]*\btoken(s)?\b", r"\bput\b[^.]*\btoken(s)?\b onto the battlefield"):
        roles["token_generator"] = 1.0
    if matches(r"\btoken(s)? you control\b", r"\bwhenever\b[^.]*\btoken(s)?\b[^.]*\bgets?\b"):
        roles["token_payoff"] = 1.0

    if matches(r"\bexile\b[^.]*\b(return|returns)\b", r"\breturn\b[^.]*\bexile\b"):
        roles["blink"] = 1.0
    if matches(r"\b(enters|enter) the battlefield\b", r"\b(etb)\b"):
        roles["etb_payoff"] = 1.0

    if matches(r"\bdiscard\b[^.]*\bcard(s)?\b"):
        roles["discard_outlet"] = 1.0
    if matches(r"\bwhenever\b[^.]*\bdiscard(s|ed)?\b"):
        roles["discard_payoff"] = 1.0

    if matches(r"\bput\b[^.]*\bcounter(s)?\b", r"\bproliferate\b"):
        roles["counter_generator"] = 1.0
    if matches(r"\+1/\+1 counters?\b"):
        roles["counter_generator"] = max(roles["counter_generator"], 0.8)
    if matches(r"\bproliferate\b"):
        roles["counter_generator"] = max(roles["counter_generator"], 0.7)

    if matches(r"\blands?\b"):
        roles["land_synergy"] = 0.6
    if matches(r"\blandfall?\b"):
        roles["land_synergy"] = 1.0
    if matches(r"\bartifacts?\b"):
        roles["artifact_synergy"] = 0.8
    if matches(r"\bequipment\b", r"\bequip\b"):
        roles["equipment_synergy"] = 0.8
        roles["artifact_synergy"] = 0.3
    if matches(r"\benchantments?\b", r"\baura\b"):
        roles["enchantment_synergy"] = 0.8
    if matches(r"\bcreatures?\b", r"\btype\b"):
        roles["creature_synergy"] = 0.3
    if matches(r"\b(instants?|sorcer(y|ies))\b", r"\bprowess(s)?\b"):
        roles["spell_synergy"] = 0.8

    if matches("you win the game", "win the game", "loses the game"):
        roles["win_condition"] = 1.0
    if matches("each opponent loses", "deals damage to each opponent", "double your", "double the power"):
        roles["finisher"] = 0.7

    if cmc is not None:
        if cmc >= 4:
            roles["high_cmc"] = min(1.0, cmc / 10.0)
        elif cmc <= 3:
            roles["low_cmc"] = max(0.0, 1.0 - cmc / 4.0)

    if "creature" in type_line:
        if power is not None:
            if power >= 4:
                roles["high_power"] = min(1.0, power / 10.0)
            elif power <= 2:
                roles["low_power"] = max(0.0, 1.0 - power / 4.0)
        if toughness is not None:
            if toughness >= 5:
                roles["high_toughness"] = min(1.0, toughness / 10.0)
            elif toughness <= 2:
                roles["low_toughness"] = max(0.0, 1.0 - toughness / 4.0)

    return roles


# Tag label -> weight added to the role's score.
TAG_ROLE_WEIGHTS = {
    "ramp": {"ramp": 1.0, "land ramp": 1.0, "mana dork": 1.0, "utility mana rock": 1.0,
             "multi land ramp": 1.0, "adds multiple mana": 0.5, "tutor-land-to-battlefield": 0.8,
             "repeatable treasures": 0.8, "combat ramp": 0.5},
    "mana_fixing": {"tutor-land-basic": 0.6, "utility land": 0.3},
    "card_draw": {"pure draw": 1.0, "repeatable pure draw": 1.0, "draw engine": 1.0,
                  "burst draw": 1.0, "cantrip": 0.4, "force draw": 0.5, "repeatable loot": 0.5},
    "card_advantage": {"repeatable card advantage": 1.0, "repeatable impulsive draw": 0.7,
                       "repeatable impulse": 0.7, "life for cards": 0.5, "curiosity": 0.5},
    "card_selection": {"scry": 1.0, "surveil": 1.0, "repeatable scry": 1.0, "repeatable loot": 0.8},
    "tutor": {"tutor-to-hand": 1.0, "tutor-to-battlefield": 1.0, "tutor-land-basic": 0.5,
              "tutor-land-to-battlefield": 0.5},

    "spot_removal": {"spot removal": 1.0, "removal-creature": 1.0, "removal-nonland": 1.0,
                     "removal-exile": 1.0, "removal-destroy": 1.0, "removal-sacrifice": 0.8,
                     "removal-bounce": 0.6, "removal-toughness": 0.8, "removal-artifact": 0.8,
                     "removal-enchantment": 0.8, "removal-planeswalker": 0.8,
                     "removal-permanent": 0.8, "removal-land": 0.8, "removal-fight": 0.6,
                     "removal-tuck": 0.8, "repeatable removal": 1.0, "burn creature": 0.6,
                     "multi removal": 0.5, "one-sided fight": 0.6},
    "board_wipe": {"sweeper": 1.0, "sweeper-one-sided": 1.0, "group slug": 0.3},
    "counterspell": {"counterspell with set mechanic": 1.0},
    "protection": {"protects-creature": 1.0, "protects-all": 1.0, "gives hexproof": 0.8,
                   "gives indestructible": 0.8, "damage prevention": 0.4, "ward": 0.4},
    "graveyard_hate": {"hate-graveyard": 1.0},

    "recursion": {"reanimate-creature": 1.0, "reanimate-self": 0.6, "reanimate-cast": 1.0,
                  "regrowth-creature": 5.0, "regrowth-self": 0.3, "rescue-creature": 0.3},
    "graveyard_filling": {"mill-self": 1.0, "mill-any": 0.6, "mill-opponent": 0.3,
                          "repeatable loot": 0.4, "surveil": 0.5, "discard outlet": 0.5},

    "sacrifice_outlet": {"sacrifice outlet-creature": 8.0, "sacrifice outlet-artifact": 8.0,
                         "sacrifice outlet-land": 8.0, "repeatable sacrifice outlet": 1.0,
                         "free sacrifice outlet": 1.0},
    "death_payoff": {"death trigger": 1.0, "death trigger-self": 0.6},

    "token_generator": {"repeatable creature tokens": 1.0, "repeatable artifact tokens": 1.0,
                        "repeatable treasures": 0.5, "unique token": 0.2, "temporary token": 0.3},

    "discard_outlet": {"discard outlet": 1.0, "discard": 0.5, "repeatable loot": 0.4},
    "discard_payoff": {"discard with set's mechanic": 0.5},

    "counter_generator": {"gains pp counters": 0.5, "repeatable pp counters": 1.0,
                          "gives pp counters": 1.0, "gives pp counters to all": 1.0,
                          "gives mm counters": 0.5},
    "counter_payoff": {"pp counters matter": 1.0, "counters matter": 1.0},

    "land_synergy": {"landfall": 1.0, "land count matters": 0.7},
    "artifact_synergy": {"synergy-artifact": 1.0, "synergy-artifact-creature": 0.7},
    "equipment_synergy": {"synergy-equipment": 1.0},
    "creature_synergy": {"creature count matters": 0.6},
    "spell_synergy": {"synergy-instant": 0.8, "synergy-sorcery": 0.8, "synergy-noncreature": 0.6,
                      "cast trigger-you": 0.5, "copy-spell": 0.4, "copy-instant": 0.4,
                      "copy-sorcery": 0.4},

    "finisher": {"drain life": 0.5, "opponent loses life": 0.5, "burn player": 0.4},
}


def classify_tag_role(tag_set):
    """Return a 0.0-1.0 score per role from a card's tag labels."""
    roles = {role: 0.0 for role in ROLE_NAMES}
    for role, weights in TAG_ROLE_WEIGHTS.items():
        total = sum(weight for tag, weight in weights.items() if tag in tag_set)
        roles[role] = min(1.0, total)

    if any("typal" in tag for tag in tag_set):
        roles["creature_synergy"] = 1.0
    return roles


def classify_card_archetype(card):
    """Return 0.0-1.0 strategy scores from a card's Oracle text."""
    text = re.sub(r"\s+", " ", (card.get("oracle_text") or "").lower())
    type_line = (card.get("type_line") or "").lower()
    keywords = (card.get("keywords") or "").lower()
    matches = _matcher(text)

    archetypes = {name: 0.0 for name in ARCHETYPE_NAMES}

    if matches(r"\bequip\b", r"\baura\b", r"\bgets? \+\d+/\+\d+\b"):
        archetypes["voltron"] = 0.8
    if matches(r"\bcreate(s)?\b[^.]*\btoken(s)?\b", r"\btoken(s)? you control\b"):
        archetypes["tokens"] = 1.0
    if matches(r"\battack(s|ing)?\b", r"\bcombat damage\b", r"\bhaste\b"):
        archetypes["aggro"] = 0.5
    if "creature" in type_line and not matches(r"\bhaste\b"):
        archetypes["midrange"] = 0.3
    if matches(r"\bcreatures? you control\b", r"\bcreatures? of the same type\b", r"\btype\b"):
        archetypes["tribal"] = 0.5
    if matches(r"\breturn\b[^.]*\bgraveyard\b", r"\bfrom your graveyard\b"):
        archetypes["reanimator"] = 1.0
    if matches(r"\bwhenever\b[^.]*\b(creature|another creature)\b[^.]*\bdies\b", r"\bwhenever\b[^.]*\bsacrifice"):
        archetypes["aristocrats"] = 1.0
    if matches(r"\bsacrifice\b", r"\bsacrificed\b"):
        archetypes["sacrifice"] = 0.8
    if matches(r"\binstant(s)?\b", r"\bsorcer(y|ies)\b", r"\bspell(s)?\b"):
        archetypes["spellslinger"] = 0.5
    if matches(r"\bexile\b[^.]*\breturn\b", r"\breturn\b[^.]*\bexile\b", r"\bblink\b"):
        archetypes["blink"] = 1.0
    if matches(r"\b(enchantment|aura)s?\b", r"\bwhenever\b[^.]*\benchantment\b"):
        archetypes["enchantress"] = 0.8
    if matches(r"\bartifact(s)?\b", r"\btreasure(s)?\b", r"\bclue(s)?\b"):
        archetypes["artifacts"] = 0.5
    if matches(r"\+1/\+1 counter(s)?\b", r"\bproliferate\b", r"\bcounter(s)? on\b"):
        archetypes["counters"] = 0.8
    if "planeswalker" in type_line or matches(r"\bplaneswalker\b"):
        archetypes["planeswalker"] = 1.0
    if re.search(r"\blandfall\b", keywords) or matches(
        r"\blandfall\b",
        r"\blands? enters?\b",
        r"\bwhenever\b[^.]*\bland\b[^.]*\bunder your control\b",
    ):
        archetypes["landfall"] = 1.0
    if matches(r"\btreasure tokens?\b", r"\btreasure(s)?\b"):
        archetypes["treasures"] = 1.0
    if matches(r"\bclue tokens?\b", r"\bclue(s)?\b"):
        archetypes["clues"] = 1.0
    if matches(r"\bfood tokens?\b", r"\bfood(s)?\b"):
        archetypes["food"] = 1.0
    if matches(r"\bcounter target\b", r"\bdraw\b", r"\bexile target\b", r"\breturn target\b"):
        archetypes["control"] = 0.5
    if matches(r"\bcan't attack\b", r"\bcan't untap\b", r"\bskip your\b", r"\bplayers can't\b"):
        archetypes["stax"] = 0.9
    if matches(r"\beach player\b", r"\beach opponent\b", r"\bopponents? draw\b", r"\beach player may\b"):
        archetypes["group_hug"] = 0.7
    if matches(r"\binfinite\b", r"\bcombo\b", r"\byou win the game\b"):
        archetypes["combo"] = 1.0

    return archetypes


# Tag label -> weight added to the archetype's score.
TAG_ARCHETYPE_WEIGHTS = {
    "voltron": {"synergy-equipment": 1.0, "synergy-aura": 1.0, "quick equip": 0.5, "auto equip": 0.5,
                "auraify": 0.4, "gives pp counters": 0.2},
    "tokens": {"repeatable creature tokens": 1.0, "repeatable artifact tokens": 0.8,
               "repeatable noncreature tokens": 0.8, "synergy-token": 1.0,
               "synergy-token-creature": 1.0, "unique token": 0.3, "temporary token": 0.3},
    "aggro": {"attack trigger": 0.4, "attacking matters": 0.5, "attacking matters-self": 0.3,
              "gives haste": 0.4, "synergy-haste": 0.6, "force attacker": 0.2, "synergy-solo-attack": 0.5},
    "aristocrats": {"death trigger": 1.0, "death trigger-self": 0.4, "sacrifice outlet-creature": 0.5,
                    "your sacrifice matters": 1.0, "repeatable sacrifice outlet": 0.5},
    "sacrifice": {"sacrifice outlet-creature": 1.0, "sacrifice outlet-artifact": 1.0,
                  "sacrifice outlet-land": 1.0, "sacrifice outlet-enchantment": 1.0,
                  "sacrifice outlet-token": 1.0, "sacrifice outlet-universal": 1.0,
                  "repeatable sacrifice outlet": 1.0, "free sacrifice outlet": 1.0,
                  "your sacrifice matters": 1.0, "sacrifice self": 0.3},
    "reanimator": {"reanimate-creature": 1.0, "reanimate-cast": 1.0, "reanimate-from-any": 1.0,
                   "reanimate-permanent": 1.0, "mass reanimation": 1.0, "reanimate-from-opponent": 1.0,
                   "temporary reanimation": 0.8, "reanimate-self": 0.4, "reanimate-artifact": 0.6,
                   "reanimate-land": 0.4, "reanimate-enchantment": 0.4},
    "spellslinger": {"cast trigger-you": 0.7, "cast trigger": 0.5, "copy-spell": 0.6,
                     "second spell matters": 1.0, "synergy-instant": 1.0, "synergy-sorcery": 1.0,
                     "synergy-noncreature": 0.6},
    "blink": {"flicker-creature": 1.0, "flicker-slow": 0.7, "flicker-self": 0.4},
    "enchantress": {"synergy-enchantment": 1.0, "synergy-aura": 0.6, "enchantmentfall": 1.0,
                    "auraify": 0.4, "enchantmentize": 0.4},
    "artifacts": {"synergy-artifact": 1.0, "synergy-artifact-creature": 0.7, "artifactfall": 1.0,
                  "animate artifact": 0.4, "artifactify": 0.4, "repeatable artifact tokens": 0.5},
    "counters": {"pp counters matter": 1.0, "counters matter": 1.0, "repeatable pp counters": 0.8,
                 "gives pp counters": 0.4, "gains pp counters": 0.3, "gives pp counters to all": 0.8,
                 "gives mm counters": 0.4},
    "planeswalker": {"synergy-planeswalker": 1.0, "protects-planeswalker": 0.6},
    "landfall": {"landfall": 1.0, "landfall other": 1.0},
    "treasures": {"repeatable treasures": 1.0, "synergy-treasure": 1.0},
    "clues": {"repeatable clues": 1.0, "synergy-clue": 1.0},
    "food": {"repeatable food": 1.0, "synergy-food": 1.0},
    "control": {"counterspell": 0.7, "counterspell-reusable": 0.7, "counterspell-soft": 0.5,
                "counterspell with set mechanic": 0.5, "sweeper": 0.7, "sweeper-one-sided": 0.7,
                "spot removal": 0.3, "repeatable removal": 0.5, "removal-nonland": 0.3,
                "draw engine": 0.3, "pure draw": 0.2},
    "stax": {"prevent attack": 0.5, "restricted attacker": 0.4, "prevent blocker": 0.2,
             "tax attack": 0.8, "lockdown-creature": 0.4, "symmetrical": 0.3, "hate-attacker": 0.2},
    "group_hug": {"group hug": 1.0, "selective group hug": 1.0},
}


def classify_tag_archetype(tag_set):
    """Return 0.0-1.0 strategy scores from a card's tag labels."""
    archetypes = {name: 0.0 for name in ARCHETYPE_NAMES}
    for archetype, weights in TAG_ARCHETYPE_WEIGHTS.items():
        total = sum(weight for tag, weight in weights.items() if tag in tag_set)
        archetypes[archetype] = min(1.0, total)

    if any("typal" in tag for tag in tag_set):
        archetypes["tribal"] = 1.0
    return archetypes


def combine(tag_scores, text_scores, names):
    """Prefer the tag score; fall back to the oracle-text score when it is 0."""
    return {n: tag_scores[n] if tag_scores[n] > 0 else text_scores[n] for n in names}
