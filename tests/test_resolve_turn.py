import io
import json
import os
import random
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classes.game import Person, resolve_turn
from classes.magic import Spell


class FixedRng:
    """Deterministic stand-in for the random module used by resolve_turn."""

    def __init__(self, randrange_values=None, random_value=1.0):
        self.randrange_values = list(randrange_values or [])
        self.random_value = random_value

    def randrange(self, low, high=None):
        if high is None:
            high, low = low, 0
        if self.randrange_values:
            return self.randrange_values.pop(0)
        return low

    def random(self):
        return self.random_value


def make_person(name="actor", hp=1000, mp=100, atk=110, df=0,
                magic=None, items=None, crit_chance=0.0, crit_multiplier=2.0):
    return Person(name, hp, mp, atk, df, magic or [], items or [],
                  crit_chance=crit_chance, crit_multiplier=crit_multiplier)


class ResolveTurnTests(unittest.TestCase):

    def test_hp_never_goes_negative(self):
        attacker = make_person(atk=2010)  # atkl == 2000
        target = make_person("Imp", hp=50, df=0)
        rng = FixedRng(randrange_values=[2000], random_value=1.0)

        result = resolve_turn(attacker, [target], rng=rng)

        self.assertTrue(result["ok"])
        self.assertEqual(result["hits"][0]["damage"], 2000)
        self.assertEqual(result["hits"][0]["hp_after"], 0)
        self.assertEqual(target.get_hp(), 0)
        self.assertGreaterEqual(target.get_hp(), 0)

    def test_defense_is_applied_before_critical_hit(self):
        attacker = make_person(atk=110, crit_chance=1.0, crit_multiplier=2.0)
        target = make_person("Imp", hp=10000, df=30)
        rng = FixedRng(randrange_values=[100], random_value=0.0)

        result = resolve_turn(attacker, [target], rng=rng)

        hit = result["hits"][0]
        self.assertTrue(hit["crit"])
        # base 100 - defense 30 = 70, then x2 crit = 140.
        # (crit-before-defense would produce 170.)
        self.assertEqual(hit["damage"], 140)

    def test_defense_never_produces_negative_damage_or_heals(self):
        attacker = make_person(atk=110, crit_chance=1.0, crit_multiplier=2.0)
        target = make_person("Imp", hp=500, df=500)
        rng = FixedRng(randrange_values=[100], random_value=0.0)

        result = resolve_turn(attacker, [target], rng=rng)

        self.assertEqual(result["hits"][0]["damage"], 0)
        self.assertEqual(target.get_hp(), 500)

    def test_spell_cooldown_blocks_recasts_and_recovers(self):
        spell = Spell("Fire", 10, 100, "black", cooldown=2)
        attacker = make_person(mp=100, magic=[spell])
        target = make_person("Imp", hp=10000)
        rng = FixedRng(randrange_values=[100], random_value=1.0)

        first = resolve_turn(attacker, [target], spell=spell, rng=rng)
        self.assertTrue(first["ok"])
        self.assertEqual(attacker.get_mp(), 90)
        self.assertEqual(attacker.cooldowns["Fire"], 2)

        second = resolve_turn(attacker, [target], spell=spell, rng=rng)
        self.assertFalse(second["ok"])
        self.assertEqual(second["reason"], "on_cooldown")
        self.assertEqual(second["hits"], [])
        self.assertEqual(attacker.get_mp(), 90)

        third = resolve_turn(attacker, [target], spell=spell, rng=rng)
        self.assertEqual(third["reason"], "on_cooldown")

        fourth = resolve_turn(attacker, [target], spell=spell, rng=FixedRng([100]))
        self.assertTrue(fourth["ok"])
        self.assertEqual(attacker.get_mp(), 80)
        self.assertEqual(target.get_hp(), 9800)

    def test_not_enough_mp_is_rejected_without_side_effects(self):
        spell = Spell("Meteor", 50, 100, "black", cooldown=3)
        attacker = make_person(mp=10, magic=[spell])
        target = make_person("Imp", hp=10000)

        result = resolve_turn(attacker, [target], spell=spell, rng=FixedRng())

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "not_enough_mp")
        self.assertEqual(attacker.get_mp(), 10)
        self.assertNotIn("Meteor", attacker.cooldowns)
        self.assertEqual(target.get_hp(), 10000)

    def test_empty_targets_is_a_deterministic_noop(self):
        spell = Spell("Fire", 10, 100, "black", cooldown=2)
        attacker = make_person(mp=50, magic=[spell])
        rng = random.Random(2024)
        state_before = rng.getstate()
        mp_before = attacker.get_mp()

        first = resolve_turn(attacker, [], spell=spell, rng=rng)
        second = resolve_turn(attacker, None, spell=spell, rng=rng)

        self.assertFalse(first["ok"])
        self.assertEqual(first["reason"], "no_targets")
        self.assertEqual(first, second)
        self.assertEqual(attacker.get_mp(), mp_before)
        self.assertEqual(attacker.cooldowns, {})
        self.assertEqual(rng.getstate(), state_before)
        json.dumps(first)  # result must be a stable, serializable value

    def test_all_dead_targets_counts_as_no_targets(self):
        attacker = make_person()
        dead = make_person("Ghost", hp=100)
        dead.take_damage(100)

        result = resolve_turn(attacker, [dead], rng=random.Random(7))

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "no_targets")
        self.assertEqual(dead.get_hp(), 0)

    def test_repeated_calls_return_identical_results_with_same_seed(self):
        def run_once():
            spell = Spell("Fire", 10, 100, "black", cooldown=1)
            actor = make_person(mp=200, magic=[spell], atk=110,
                                crit_chance=0.5, crit_multiplier=2.0)
            victims = [make_person("Imp1", hp=10000, df=20),
                       make_person("Imp2", hp=10000, df=20)]
            rng = random.Random(4242)
            attack = resolve_turn(actor, victims, rng=rng)
            cast = resolve_turn(actor, victims, spell=spell, rng=rng)
            blocked = resolve_turn(actor, victims, spell=spell, rng=rng)
            return attack, cast, blocked

        run_a = run_once()
        run_b = run_once()
        self.assertEqual(run_a, run_b)

    def test_white_magic_heals_and_clamps_at_max_hp(self):
        cure = Spell("Cure", 10, 100, "white", cooldown=1)
        healer = make_person(name="Priest", hp=50, mp=100, magic=[cure])
        healer.take_damage(20)  # hp == 30
        rng = FixedRng(randrange_values=[85])  # 100 - 15

        result = resolve_turn(healer, [], spell=cure, rng=rng)

        self.assertTrue(result["ok"])
        self.assertEqual(result["heals"][0]["amount"], 85)
        self.assertEqual(result["heals"][0]["hp_after"], 50)
        self.assertEqual(healer.get_hp(), 50)

    def test_killed_target_is_flagged(self):
        attacker = make_person(atk=210)  # atkl == 200
        target = make_person("Imp", hp=100)
        rng = FixedRng(randrange_values=[200], random_value=1.0)

        result = resolve_turn(attacker, [target], rng=rng)

        self.assertTrue(result["hits"][0]["killed"])
        self.assertEqual(result["hits"][0]["hp_after"], 0)


class TargetSelectionTests(unittest.TestCase):

    def test_choose_target_maps_living_index_into_full_list(self):
        alive = make_person("Alive", hp=100)
        dead = make_person("Dead", hp=100)
        dead.take_damage(100)
        actor = make_person()

        with mock.patch("builtins.input", return_value="1"), redirect_stdout(io.StringIO()):
            choice = actor.choose_target([dead, alive])

        self.assertEqual(choice, 1)  # not 0, which points at the dead enemy

    def test_choose_target_without_living_enemies_returns_minus_one(self):
        actor = make_person()

        with redirect_stdout(io.StringIO()):
            choice = actor.choose_target([])

        self.assertEqual(choice, -1)

    def test_choose_enemy_spell_returns_after_recursing(self):
        cheap = Spell("Fire", 5, 100, "black")
        expensive = Spell("Meteor", 999, 100, "black")
        enemy = make_person(mp=10, magic=[expensive, cheap])

        with mock.patch("classes.game.random") as patched_random:
            patched_random.randrange.side_effect = [0, 1]
            patched_random.choice.side_effect = lambda seq: seq[0]
            spell, damage = enemy.choose_enemy_spell()

        self.assertIs(spell, cheap)
        self.assertIsInstance(damage, int)

    def test_choose_enemy_spell_returns_none_when_nothing_castable(self):
        expensive = Spell("Meteor", 999, 100, "black")
        enemy = make_person(mp=10, magic=[expensive])

        self.assertIsNone(enemy.choose_enemy_spell())


if __name__ == "__main__":
    unittest.main()
