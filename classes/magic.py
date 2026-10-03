import random
class Spell:
    def __init__(self, name, cost, dmg, type, cooldown=0):
        self.name = name
        self.cost = cost
        self.dmg = dmg
        self.type = type
        self.cooldown = cooldown

    def generate_damage(self, rng=None):
        low = self.dmg - 15
        high = self.dmg + 15
        return (rng or random).randrange(low, high)
