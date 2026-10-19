from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from .views import SUBTYPE_BONUS, score_synergy


class TypalScoringTests(SimpleTestCase):
	def test_mismatched_typal_tag_subtracts_bonus(self):
		commander = SimpleNamespace(role=None, archetype=None, oracle_id="commander")
		card = SimpleNamespace(
			role=None,
			archetype=None,
			oracle_id="card",
			keywords="",
			type_line="Creature — Elf",
		)

		typal_types = {"commander": {"dragon"}, "card": {"elf"}}
		with patch("decks.views._typal_types_for_oracle_ids", return_value=typal_types):
			scored_cards = score_synergy(commander, [card])

		self.assertEqual(scored_cards[0][1], -SUBTYPE_BONUS)

	def test_choose_typal_tag_gets_bonus(self):
		commander = SimpleNamespace(role=None, archetype=None, oracle_id="commander")
		card = SimpleNamespace(
			role=None,
			archetype=None,
			oracle_id="card",
			keywords="",
			type_line="Creature — Elf",
		)

		typal_types = {"commander": {"dragon"}, "card": {"choose"}}
		with patch("decks.views._typal_types_for_oracle_ids", return_value=typal_types):
			scored_cards = score_synergy(commander, [card])

		self.assertEqual(scored_cards[0][1], SUBTYPE_BONUS)
