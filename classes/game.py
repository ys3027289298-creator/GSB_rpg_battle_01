import random
from .magic import Spell
import pprint

CRITICAL_CHANCE = 0.1
CRITICAL_MULTIPLIER = 2


def resolve_turn(attacker, targets, target_index=0, damage=None, critical=None, rng=None):
    """Resolve a single attack against a list of targets.

    Unified order of operations:
      1. raw damage (given, or rolled from the attacker)
      2. critical hit multiplier
      3. flat defense subtraction
      4. clamp damage at 0, then apply (HP clamps at 0)

    Returns a plain dict; identical inputs always produce identical results.
    An empty (or fully defeated) target list is a no-op that reports
    battle_over instead of raising.
    """
    if rng is None:
        rng = random
    result = {
        "attacker": attacker.name,
        "target_index": None,
        "target": None,
        "damage": 0,
        "critical": False,
        "died": False,
        "battle_over": True,
    }
    alive_indices = [i for i, target in enumerate(targets) if target.get_hp() > 0]
    if not alive_indices:
        return result
    if target_index not in alive_indices:
        target_index = alive_indices[0]
    target = targets[target_index]
    if damage is None:
        damage = attacker.generate_damage()
    if critical is None:
        critical = rng.random() < CRITICAL_CHANCE
    dealt = damage * (CRITICAL_MULTIPLIER if critical else 1) - target.df
    dealt = max(0, dealt)
    target.take_damage(dealt)
    result.update({
        "target_index": target_index,
        "target": target.name,
        "damage": dealt,
        "critical": critical,
        "died": target.get_hp() == 0,
        "battle_over": all(t.get_hp() == 0 for t in targets),
    })
    return result


def battle_status(players, enemies):
    """Return "win", "lose" or "ongoing" for the current combatants."""
    if not any(enemy.get_hp() > 0 for enemy in enemies):
        return "win"
    if not any(player.get_hp() > 0 for player in players):
        return "lose"
    return "ongoing"


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

    def __init__(self, name, hp, mp, atk, df, magic, items):
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
        self.cooldowns = {}

    def generate_damage(self):
        return random.randrange(self.atkl,self.atkh)


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
        self.mp -= cost
        if self.mp < 0:
            self.mp = 0

    def on_cooldown(self, spell):
        return self.cooldowns.get(spell.name, 0) > 0

    def set_cooldown(self, spell):
        if spell.cooldown > 0:
            self.cooldowns[spell.name] = spell.cooldown

    def tick_cooldowns(self):
        for name in list(self.cooldowns):
            self.cooldowns[name] = max(0, self.cooldowns[name] - 1)

    
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
        i = 1
        valid = []
        print("\n" + bcolor.FAIL + bcolor.BOLD + "    TARGET:" + bcolor.ENDC)
        for index, enemy in enumerate(enemies):
            if enemy.get_hp() != 0:
                print("        " + str(i) + ".", enemy.name)
                valid.append(index)
                i += 1
        choice = int(input("    Choose target:")) - 1
        if 0 <= choice < len(valid):
            return valid[choice]
        return valid[0] if valid else 0
            

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
        for _ in range(len(self.magic) * 2):
            magic_choice = random.randrange(0, len(self.magic))
            spell = self.magic[magic_choice]
            if self.mp < spell.cost or self.on_cooldown(spell):
                continue
            if spell.type == "white" and pct > 50:
                continue
            return spell, spell.generate_damage()
        return None
           





    

