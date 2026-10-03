import random
import unittest
from unittest.mock import patch

from classes.game import Person, resolve_turn, battle_status, CRITICAL_MULTIPLIER
from classes.magic import Spell


def make_person(name="Hero", hp=1000, mp=100, atk=100, df=20, magic=None, items=None):
    return Person(name, hp, mp, atk, df, magic if magic is not None else [],
                  items if items is not None else [])


class ResolveTurnTests(unittest.TestCase):
    def test_empty_targets_returns_deterministic_result(self):
        attacker = make_person()
        first = resolve_turn(attacker, [])
        second = resolve_turn(attacker, [])
        self.assertEqual(first, second)
        self.assertIsNone(first["target"])
        self.assertEqual(first["damage"], 0)
        self.assertTrue(first["battle_over"])
        self.assertEqual(attacker.get_hp(), 1000)

    def test_all_dead_targets_behave_like_empty(self):
        attacker = make_person()
        dead = make_person("Dead", hp=100)
        dead.take_damage(100)
        result = resolve_turn(attacker, [dead])
        self.assertIsNone(result["target"])
        self.assertEqual(result["damage"], 0)
        self.assertTrue(result["battle_over"])

    def test_repeated_calls_are_deterministic(self):
        results = []
        for _ in range(2):
            attacker = make_person()
            defender = make_person("Foe", df=20)
            results.append((resolve_turn(attacker, [defender], 0, damage=100,
                                         critical=False), defender.get_hp()))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0]["damage"], 80)
        self.assertEqual(results[0][1], 920)

    def test_seeded_rng_repeated_calls_are_deterministic(self):
        outcomes = []
        for _ in range(2):
            random.seed(1234)
            attacker = make_person()
            defender = make_person("Foe")
            outcomes.append((resolve_turn(attacker, [defender], 0,
                                          rng=random.Random(1234)),
                             defender.get_hp()))
        self.assertEqual(outcomes[0], outcomes[1])

    def test_hp_never_goes_negative(self):
        attacker = make_person()
        defender = make_person("Foe", hp=50, df=0)
        result = resolve_turn(attacker, [defender], 0, damage=99999,
                              critical=False)
        self.assertEqual(defender.get_hp(), 0)
        self.assertTrue(result["died"])
        self.assertTrue(result["battle_over"])

    def test_crit_applies_before_defense_is_subtracted(self):
        attacker = make_person()
        defender = make_person("Foe", df=30)
        result = resolve_turn(attacker, [defender], 0, damage=100, critical=True)
        self.assertEqual(result["damage"], 100 * CRITICAL_MULTIPLIER - 30)
        self.assertTrue(result["critical"])
        self.assertEqual(defender.get_hp(), 1000 - (100 * CRITICAL_MULTIPLIER - 30))

    def test_no_crit_subtracts_defense_only(self):
        attacker = make_person()
        defender = make_person("Foe", df=30)
        result = resolve_turn(attacker, [defender], 0, damage=100, critical=False)
        self.assertEqual(result["damage"], 70)
        self.assertFalse(result["critical"])

    def test_damage_clamped_at_zero_after_defense(self):
        attacker = make_person()
        defender = make_person("Foe", df=500)
        result = resolve_turn(attacker, [defender], 0, damage=10, critical=False)
        self.assertEqual(result["damage"], 0)
        self.assertEqual(defender.get_hp(), 1000)

    def test_dead_target_falls_back_to_first_alive(self):
        attacker = make_person()
        dead = make_person("Dead", hp=100)
        dead.take_damage(100)
        alive = make_person("Alive", df=0)
        result = resolve_turn(attacker, [dead, alive], 0, damage=50,
                              critical=False)
        self.assertEqual(result["target_index"], 1)
        self.assertEqual(result["target"], "Alive")
        self.assertEqual(alive.get_hp(), 950)

    def test_out_of_range_index_falls_back_deterministically(self):
        attacker = make_person()
        defender = make_person("Foe", df=0)
        result = resolve_turn(attacker, [defender], 99, damage=50, critical=False)
        self.assertEqual(result["target_index"], 0)
        self.assertEqual(defender.get_hp(), 950)


class BattleStatusTests(unittest.TestCase):
    def test_empty_enemy_list_is_win(self):
        self.assertEqual(battle_status([make_person()], []), "win")

    def test_empty_player_list_is_lose(self):
        self.assertEqual(battle_status([], [make_person()]), "lose")

    def test_ongoing_battle(self):
        self.assertEqual(battle_status([make_person()], [make_person()]),
                         "ongoing")

    def test_dead_enemies_in_list_still_counts_as_win(self):
        dead = make_person("Dead", hp=100)
        dead.take_damage(100)
        self.assertEqual(battle_status([make_person()], [dead]), "win")

    def test_dead_players_in_list_still_counts_as_lose(self):
        dead = make_person("Dead", hp=100)
        dead.take_damage(100)
        self.assertEqual(battle_status([dead], [make_person()]), "lose")


class CooldownTests(unittest.TestCase):
    def test_spell_not_on_cooldown_by_default(self):
        person = make_person()
        spell = Spell("Fire", 25, 600, "black")
        self.assertFalse(person.on_cooldown(spell))

    def test_cooldown_blocks_and_ticks_down(self):
        person = make_person()
        spell = Spell("Meteor", 40, 1200, "black", cooldown=2)
        person.set_cooldown(spell)
        self.assertTrue(person.on_cooldown(spell))
        person.tick_cooldowns()
        self.assertTrue(person.on_cooldown(spell))
        person.tick_cooldowns()
        self.assertFalse(person.on_cooldown(spell))

    def test_zero_cooldown_spell_never_blocks(self):
        person = make_person()
        spell = Spell("Fire", 25, 600, "black")
        person.set_cooldown(spell)
        self.assertFalse(person.on_cooldown(spell))

    def test_enemy_spell_selection_returns_none_without_mp(self):
        spells = [Spell("Fire", 25, 600, "black")]
        enemy = make_person(mp=0, magic=spells)
        self.assertIsNone(enemy.choose_enemy_spell())
        self.assertIsNone(enemy.choose_enemy_spell())

    def test_enemy_spell_selection_skips_cooldown(self):
        spells = [Spell("Meteor", 40, 1200, "black", cooldown=3)]
        enemy = make_person(mp=100, magic=spells)
        enemy.set_cooldown(spells[0])
        self.assertIsNone(enemy.choose_enemy_spell())

    def test_enemy_spell_selection_returns_affordable_spell(self):
        spells = [Spell("Fire", 25, 600, "black")]
        enemy = make_person(mp=100, magic=spells)
        spell, dmg = enemy.choose_enemy_spell()
        self.assertIs(spell, spells[0])
        self.assertGreater(dmg, 0)

    def test_reduce_mp_never_goes_negative(self):
        person = make_person(mp=10)
        person.reduce_mp(40)
        self.assertEqual(person.get_mp(), 0)


class TargetSelectionTests(unittest.TestCase):
    def test_choose_target_maps_displayed_index_to_real_index(self):
        dead = make_person("Dead", hp=100)
        dead.take_damage(100)
        alive_a = make_person("A")
        alive_b = make_person("B")
        enemies = [dead, alive_a, alive_b]
        with patch("builtins.input", return_value="2"):
            self.assertEqual(make_person().choose_target(enemies), 2)

    def test_choose_target_first_alive(self):
        dead = make_person("Dead", hp=100)
        dead.take_damage(100)
        alive = make_person("A")
        with patch("builtins.input", return_value="1"):
            self.assertEqual(make_person().choose_target([dead, alive]), 1)


if __name__ == "__main__":
    unittest.main()
