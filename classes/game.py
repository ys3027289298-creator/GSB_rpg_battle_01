import random
from .magic import Spell
import pprint

class bcolor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Person:

    def __init__(self, name, hp, mp, atk, df, magic, items, crit_chance=0.0, crit_multiplier=1.5):
        self.maxhp = hp
        self.hp = hp
        self.maxmp = mp
        self.mp = mp
        self.atkl = atk - 10
        self.atkh = atk + 10
        self.df = df
        self.magic = magic
        self.items = items
        self.action = ["Attack", "Magic", "Items"]
        self.name = name
        self.crit_chance = crit_chance
        self.crit_multiplier = crit_multiplier
        self.cooldowns = {}

    def generate_damage(self, rng=None):
        return (rng or random).randrange(self.atkl, self.atkh)


    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp < 0:
            self.hp = 0
        return self.hp

    def heal(self, dmg):
        self.hp += dmg
        if self.hp > self.maxhp:
            self.hp = self.maxhp

    def get_hp(self):
        return self.hp
    
    def get_max_hp(self):
        return self.maxhp
    
    def get_mp(self):
        return self.mp

    def get_max_mp(self):
        return self.maxmp

    def reduce_mp(self, cost):
        self.mp = max(0, self.mp - cost)

    
    def choose_action(self):
        i = 1
        print("\n" + "    " + bcolor.BOLD + self.name + bcolor.ENDC)
        print(bcolor.OKBLUE + bcolor.BOLD + "    ACTIONS" + bcolor.ENDC)
        for item in self.action:
            print("        " + str(i) + ".",item)
            i += 1

    def choose_magic(self):
        i = 1
        
        print("\n" + bcolor.OKBLUE + bcolor.BOLD + "    MAGIC" + bcolor.ENDC)
        for spell in self.magic:
            print("        " + str(i) + ".", spell.name, "(cost:", str(spell.cost) + ")")
            i += 1

    def choose_item(self):
        i = 1
        print("\n" + bcolor.OKGREEN + bcolor.BOLD + "    ITEMS:" + bcolor.ENDC)
        for item in self.items:
            print("        " + str(i) + ":", item["item"].name + ":", item["item"].description, " (x" + str(item["quantity"]) + ")")
            i += 1

    def choose_target(self, enemies):
        print("\n" + bcolor.FAIL + bcolor.BOLD + "    TARGET:" + bcolor.ENDC)
        living = [enemy for enemy in enemies if enemy.get_hp() != 0]
        if not living:
            return -1
        i = 1
        for enemy in living:
            print("        " + str(i) + ".", enemy.name)
            i += 1
        choice = int(input("    Choose target:")) - 1
        return enemies.index(living[choice])
            

    def get_enemy_status(self):
        hp_bar = ""
        bar_ticks = (self.hp / self.maxhp) *100 / 2
        while bar_ticks > 0:
            hp_bar += "█"
            bar_ticks -= 1

        while len(hp_bar) < 50:
            hp_bar += " "

        hp_string = str(self.hp) + "/" + str(self.maxhp)
        current_hp = ""
        if len(hp_string) < 11:
            decreased = 11 - len(hp_string)
            while decreased > 0:
                current_hp += " " 
                decreased -= 1
            current_hp += hp_string
        else:
            current_hp = hp_string

        print("                    __________________________________________________ ")
        print(bcolor.BOLD + self.name + "  "
        + current_hp + " |" + bcolor.FAIL + hp_bar + bcolor.ENDC + "|")




    def get_status(self):
        hp_bar = ""
        bar_ticks = (self.hp / self.maxhp) * 100 / 4
        while bar_ticks > 0:
            hp_bar += "█"
            bar_ticks -= 1
        while len(hp_bar) < 25:
            hp_bar += " "
        mp_bar = ""
        mp_ticks = (self.mp / self.maxmp) * 100 / 10
        while mp_ticks > 0:
            mp_bar += "█"
            mp_ticks -= 1
        while len(mp_bar) < 10:
            mp_bar += " "

        hp_string = str(self.hp) + "/" + str(self.maxhp)
        current_hp = ""
        if len(hp_string) < 9:
            decreased = 9 - len(hp_string)
            while decreased > 0:
                current_hp += " " 
                decreased -= 1
            current_hp += hp_string
        else:
            current_hp = hp_string
        mp_string = str(self.mp) + "/" + str(self.maxmp)
        current_mp = "" 
        if len(mp_string) < 7:
            decreased = 7 - len(mp_string)
            while decreased > 0:
                current_mp += " "
                decreased -= 1
            current_mp += mp_string
        else:
            current_mp = mp_string
        print("                      _________________________             __________ ")
        print(bcolor.BOLD + self.name + "     "
        + current_hp + " |" + bcolor.OKGREEN + hp_bar + bcolor.ENDC + bcolor.BOLD + "|   " + 
        current_mp + " |" + bcolor.OKBLUE + mp_bar + bcolor.ENDC + "|")


    def choose_enemy_spell(self):
        pct = self.hp / self.maxhp * 100
        for _ in range(len(self.magic)):
            magic_choice = random.randrange(0, len(self.magic))
            spell = self.magic[magic_choice]
            if self.mp >= spell.cost and not (spell.type == "white" and pct > 50):
                return spell, spell.generate_damage()
        return None


def _tick_cooldowns(person):
    for name in list(person.cooldowns):
        person.cooldowns[name] = max(0, person.cooldowns[name] - 1)


def _resolve_hit(attacker, target, base_damage, rng):
    damage = max(0, base_damage - target.df)
    crit = rng.random() < attacker.crit_chance
    if crit:
        damage = int(round(damage * attacker.crit_multiplier))
    hp_after = target.take_damage(damage)
    return {
        "target": target.name,
        "damage": damage,
        "crit": crit,
        "killed": hp_after == 0,
        "hp_after": hp_after,
    }


def resolve_turn(attacker, targets=None, spell=None, rng=None):
    """Settle one combat turn and return a deterministic result dict.

    Settlement order is fixed: target selection -> cooldown -> MP cost ->
    damage formula -> defense -> critical hit -> HP clamp. Cooldowns tick
    once per turn with living targets, after the action resolves. A turn
    with no living targets is a pure no-op: no state changes, no rng use.
    """
    rng = rng or random
    targets = targets or []
    result = {
        "ok": False,
        "reason": "",
        "action": "spell" if spell is not None else "attack",
        "attacker": attacker.name,
        "spell": spell.name if spell is not None else None,
        "hits": [],
        "heals": [],
        "total_damage": 0,
        "cooldowns": dict(attacker.cooldowns),
    }

    living = [target for target in targets if target.get_hp() > 0]
    offensive = spell is None or spell.type != "white"
    if offensive and not living:
        result["reason"] = "no_targets"
        return result

    if spell is not None:
        if attacker.cooldowns.get(spell.name, 0) > 0:
            result["reason"] = "on_cooldown"
            _tick_cooldowns(attacker)
            result["cooldowns"] = dict(attacker.cooldowns)
            return result
        if spell.cost > attacker.get_mp():
            result["reason"] = "not_enough_mp"
            _tick_cooldowns(attacker)
            result["cooldowns"] = dict(attacker.cooldowns)
            return result
        attacker.reduce_mp(spell.cost)
        if spell.type == "white":
            amount = spell.generate_damage(rng)
            attacker.heal(amount)
            result["heals"].append({
                "target": attacker.name,
                "amount": amount,
                "hp_after": attacker.get_hp(),
            })
        else:
            base_damage = spell.generate_damage(rng)
            for target in living:
                result["hits"].append(_resolve_hit(attacker, target, base_damage, rng))
        _tick_cooldowns(attacker)
        if spell.cooldown > 0:
            attacker.cooldowns[spell.name] = spell.cooldown
    else:
        base_damage = attacker.generate_damage(rng)
        for target in living:
            result["hits"].append(_resolve_hit(attacker, target, base_damage, rng))
        _tick_cooldowns(attacker)

    result["total_damage"] = sum(hit["damage"] for hit in result["hits"])
    result["ok"] = True
    result["cooldowns"] = dict(attacker.cooldowns)
    return result
           





    

