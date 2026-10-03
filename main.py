from classes.game import Person, bcolor, resolve_turn, battle_status
from classes.magic import Spell
from classes.inventory import Item
import random

# Create Black Magic
fire = Spell("Fire", 25, 600, "black")
thunder = Spell("Thunder", 25, 600, "black")
blizzard = Spell("Blizzard", 25, 600, "black")
meteor = Spell("Meteor", 40, 1200, "black")
quake = Spell("Quake", 14, 140, "black")

# Create White Magic
cure = Spell("Cure", 25, 620, "white")
cura = Spell("Cura", 32, 1500, "white")
curaga = Spell("Curaga", 50, 6000, "white")

# Create some Items
potion = Item("Potion", "potion", "Heals 50 HP", 50)
hipotion = Item("Hi-Potion", "potion", "Heals 100 HP", 100)
superpotion = Item("Super Potion", "potion", "Heals 1000 HP", 1000)
elixer = Item("Elixer", "elixer", "Fully restoes HP/MP of one party member", 9999)
hielixer = Item("MegeElixer", "elixer", "Fully restoes party's HP/MP", 9999)
grenade = Item("Grenade", "attack", "Deals 500 damage", 500)

player_spells = [fire, thunder, blizzard, meteor,quake, cure, cura]
enemy_spells = [fire, meteor, curaga]
player_items = [{"item": potion,"quantity": 15}, {"item": hipotion, "quantity": 5},
                {"item": superpotion,"quantity": 5}, {"item": elixer,"quantity": 5},
                {"item": hielixer,"quantity": 2}, {"item": grenade,"quantity": 5}]

# Instatiate People
player1 = Person("Valos:", 3260, 132, 300, 34, player_spells, player_items)
player2 = Person("Nick :", 4160, 188, 311, 34, player_spells, player_items)
player3 = Person("Robot:", 3089, 174, 288, 34, player_spells, player_items)


enemy1 = Person("Imp  ", 1250, 130, 560, 325, enemy_spells, [])
enemy2 = Person("Magus", 11200, 701, 525, 25, enemy_spells, [])
enemy3 = Person("Imp  ", 1250, 130, 560, 325, enemy_spells, [])

players = [player1, player2, player3]
enemies = [enemy1, enemy2, enemy3]

running = True

print(bcolor.FAIL + bcolor.BOLD + "AN ENEMY ATTACK!" + bcolor.ENDC)
while running:
    print("===========================")
    print("\n\n")
    print("NAME                 HP                                    MP")
    for player in players:
        player.get_status()
    print("\n")
    for enemy in enemies:    
        enemy.get_enemy_status()

    for player in players:
        if player.get_hp() == 0:
            continue
        if battle_status(players, enemies) != "ongoing":
            break

        player.choose_action()
        choice = input("    Choose action: ")
        index = int(choice) - 1
        if index == 0:
            enemy = player.choose_target(enemies)
            result = resolve_turn(player, enemies, enemy)
            dmg = result["damage"]
            print("You attacked " + enemies[result["target_index"]].name.replace(" ","") + " for", dmg, "points of damage.")


            if result["died"]:
                print(enemies[result["target_index"]].name.replace(" ","") + " has died.")
                del enemies[result["target_index"]]
        elif index == 1:
            player.choose_magic()
            magic_choice = int(input("    Choose magic: ")) - 1
            if magic_choice == -1:
                continue
            spell = player.magic[magic_choice]
            magic_dmg = spell.generate_damage()
            current_mp = player.get_mp()
            if spell.cost > current_mp:
                print(bcolor.FAIL + "\nNot enough MP\n" + bcolor.ENDC)
                continue
            if player.on_cooldown(spell):
                print(bcolor.FAIL + "\n" + spell.name + " is on cooldown\n" + bcolor.ENDC)
                continue
            player.reduce_mp(spell.cost)
            player.set_cooldown(spell)
            if spell.type == "white":
                player.heal(magic_dmg)
                print(bcolor.OKBLUE + "\n" + spell.name + " heals for", str(magic_dmg), "HP." + bcolor.ENDC)
            elif spell.type == "black":

                enemy = player.choose_target(enemies)
                result = resolve_turn(player, enemies, enemy, damage=magic_dmg)
               
                print(bcolor.OKBLUE + "\n" + spell.name + " deals", str(result["damage"]), "points of damage to " + enemies[result["target_index"]].name.replace(" ","") + bcolor.ENDC)
                if result["died"]:
                    print(enemies[result["target_index"]].name.replace(" ","") + " has died.")
                    del enemies[result["target_index"]]
        elif index == 2:
            player.choose_item()
            item_choice = int(input("    Choose item: ")) - 1
            if item_choice == -1:
                continue

            item = player.items[item_choice]["item"]
            if player.items[item_choice]["quantity"] == 0:
                print(bcolor.FAIL + "\n" + "None left..." + bcolor.ENDC)
                continue
            player.items[item_choice]["quantity"] -= 1        
            if item.type == "potion":
                player.heal(item.prop)
                print(bcolor.OKGREEN + "\n" + item.name + " heals for", str(item.prop), "HP" + bcolor.ENDC)
            elif item.type == "elixer":
                if item.name == "MegeElixer":
                    for i in players:
                         i.hp = i.maxhp
                         i.mp = i.maxmp
                else:
                    player.hp = player.maxhp
                    player.mp = player.maxmp
                print(bcolor.OKGREEN + "\n" + item.name + " fully restores HP/MP" + bcolor.ENDC)
            elif item.type == "attack":
                enemy = player.choose_target(enemies)
                result = resolve_turn(player, enemies, enemy, damage=item.prop)
                print(bcolor.FAIL + "\n" + item.name + " deals", str(result["damage"]), "point of damage to " + enemies[result["target_index"]].name + bcolor.ENDC)
                if result["died"]:
                    print(enemies[result["target_index"]].name.replace(" ","") + " has died.")
                    del enemies[result["target_index"]]
    # Check if battle is over
    status = battle_status(players, enemies)

    # Check if Player won
    if status == "win":
        print(bcolor.OKGREEN + "You win!" + bcolor.ENDC)
        running = False

    # Check if Enemy won
    elif status == "lose":
        print(bcolor.FAIL + "Your enemies have defeated you!" + bcolor.ENDC)
        running = False

    if not running:
        break

    print("\n")
    
    # Enemy attack phase
    for enemy in enemies:
        if battle_status(players, enemies) != "ongoing":
            break
        enemy_choice = random.randrange(0, 2)
        spell = None
        magic_dmg = 0
        if enemy_choice == 1:
            spell_result = enemy.choose_enemy_spell()
            if spell_result is not None:
                spell, magic_dmg = spell_result
        if spell is None:
            # Choose attack
            target = random.randrange(0, len(players))
            result = resolve_turn(enemy, players, target)
            print(enemy.name.replace(" ", "") + " attacks " + players[result["target_index"]].name.replace(" ", "")  + " for", result["damage"])
        else:
            enemy.reduce_mp(spell.cost)
            enemy.set_cooldown(spell)
            if spell.type == "white":
                enemy.heal(magic_dmg)
                print(bcolor.OKBLUE + spell.name + " heals " + enemy.name.replace(" ", "") + " for", str(magic_dmg), "HP." + bcolor.ENDC)
            elif spell.type == "black":

                target = random.randrange(0, len(players))
                result = resolve_turn(enemy, players, target, damage=magic_dmg)
               
                print(bcolor.OKBLUE + "\n" + enemy.name.replace(" ", "") + "'s " + spell.name + " deals", str(result["damage"]), "points of damage to " + players[result["target_index"]].name.replace(" ","") + bcolor.ENDC)
                if result["died"]:
                    print(players[result["target_index"]].name.replace(" ","") + " has died.")
                    del players[result["target_index"]]

            # print("Enemy choose", spell, "damage is", magic_dmg)

    # Cooldowns tick down at the end of each round
    for person in players + enemies:
        person.tick_cooldowns()

    # Check if the enemy phase ended the battle
    if battle_status(players, enemies) == "lose":
        print(bcolor.FAIL + "Your enemies have defeated you!" + bcolor.ENDC)
        running = False

    

    





    
    
