from pickle import FALSE
import random
from ai.cpypastas.buildings import Building, Townhall, Barracks, Range, Stable, House
from ai.cpypastas.moves import Move, Build, Repair, Attack, DoNothing
from ai.cpypastas.utils import quick_path_a_star, wander_goal, get_nearest_enemy, get_nearest_enemy_building, get_step
from ai.cpypastas.resources import Gold, Resource, Tree
from random import shuffle


def BuildThing(unit, cws, typeof):

    if cws.villager_can_build[typeof.size()]:
        # If this villager was destin to build, then this would not be none
        if unit.build_loc.get(typeof.size()) is not None:
            return Build(typeof, unit.build_loc[typeof.size()])

    else:

    # If no one can build, send 3 guys to explore PER BUILD TYPE
        if cws.num_vils_exploring[typeof] < 2:
            cws.num_vils_exploring[typeof] += 1
            return Wander(unit, cws)

        if (unit.id % 4 == 0):
            return Wander(unit, cws)

        return None


# todo move these nearby algorithms into 
# cws
def RepairNearby(unit, cws):
    for i in range(-1,2):
        for j in range(-1,2):
            # no corners!
            if min(abs(i),abs(j)) == 1:
                next
            obj = cws.get_coord((unit.x + i, unit.y + j))
            if obj in cws.gatherCity():
                if obj.hp != obj.max_health():
                    return Repair(obj)

    return None

def AttackNearbyResource(unit, cws, typeof=Resource):
    for dx in range(-1,2):
        for dy in range(-1,2):
            obj = cws.get_coord((unit.x + dx, unit.y + dy))
            if issubclass(type(obj), typeof):
                if obj.reserved == False:
                    return Attack(obj)

    return None

def GetNearbyResource(unit, cws, typeof):
    # get lowest resource in kingdom:
    target = cws.get_corner_resource(typeof)

    if target is None:
        return None

    # gold is attainable, find it  
    start = (unit.x, unit.y)

    next_move = GetDirectMove(unit, target, cws)

    return next_move

# Become the bodyguard of a villager. 
def Bodyguard(unit, otherUnit, cws):
    # island intersection - see if the villager is even accessable.
    island_intersect = unit.island_ids.intersection(otherUnit.island_ids)
    if len(island_intersect) == 0:
        return None

    # First, check if we are within 12 units of the villager. If so, we can attack.
    # we can do this by checking to see if the closest enemy to this one is within
    # range.
    distance_to_other = max(abs(unit.x - otherUnit.x), abs(unit.y - otherUnit.y))


    if distance_to_other <= 12:
        if len(cws.gatherEnemyEmpire()) != 0:
            nearest_enemy = get_nearest_enemy(unit, cws)

            if nearest_enemy is not None:
                if unit.within_range((nearest_enemy.x, nearest_enemy.y)):
                    return Attack(nearest_enemy)

                # if they are not within range, but are still within 12 units, attack them.
                if max(abs(otherUnit.x - nearest_enemy.x), abs(otherUnit.y - nearest_enemy.y)):
                    return GetDirectMove(unit, (otherUnit.x, otherUnit.y), cws)

    # if we are within 3 units, do nothing.
    if distance_to_other <= 3:
        return DoNothing()

    # If we are not within 12 units, then we should move back to the villager
    return GetDirectMove(unit, (otherUnit.x, otherUnit.y), cws)

def BodyguardBasic(unit, otherUnit, cws):
   # island intersection - see if the villager is even accessable.
    island_intersect = unit.island_ids.intersection(otherUnit.island_ids)
    if len(island_intersect) == 0:
        return None

    # First, check if we are within 12 units of the villager. If so, we can attack.
    # we can do this by checking to see if the closest enemy to this one is within
    # range.
    distance_to_other = max(abs(unit.x - otherUnit.x), abs(unit.y - otherUnit.y))


    if distance_to_other <= 12:
        if len(cws.gatherEnemyEmpire()) != 0:
            nearest_enemy = get_nearest_enemy(unit, cws)

            if nearest_enemy is not None:
                if unit.within_range((nearest_enemy.x, nearest_enemy.y)):
                    return Attack(nearest_enemy)

                # if they are not within range, but are still within 12 units, attack them.
                if max(abs(otherUnit.x - nearest_enemy.x), abs(otherUnit.y - nearest_enemy.y)):
                    if len(unit.island_ids.intersection(nearest_enemy.island_ids)) != 0:
                        step = get_step((unit.x, unit.y), (nearest_enemy.x, nearest_enemy.y))
                        return Move([step[0], step[1]])

    # if we are within 3 units, do nothing.
    if distance_to_other <= 3:
        return DoNothing()

    # If we are not within 12 units, then we should move back to the villager
    step = get_step((unit.x, unit.y), (otherUnit.x, otherUnit.y))
    return Move([step[0], step[1]])


def GuardInPlace(unit, cws):
    return None

def GetDirectMove(unit, wp, cws, attackFriend=True):

    if (unit.x, unit.y) == (wp[0], wp[1]):
        return DoNothing()

    direct_step = quick_path_a_star(cws, (unit.x, unit.y), wp)
    if direct_step is None:
        direct_step = get_step((unit.x, unit.y), wp)

    if cws.is_traversable((unit.x + direct_step[0], unit.y + direct_step[1])):
        return Move(direct_step)

    else:
        # Check if it is a friendly building. if it is, go around it using
        # direct_step[x] or direct_step[y]

        wp_obj = cws.get_coord((unit.x + direct_step[0], unit.y + direct_step[1]))
        circle_of_directions = [(1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0, -1), (1, -1)]
        index_of = circle_of_directions.index(direct_step)
        try_these = [circle_of_directions[index_of - 1], 
        circle_of_directions[(index_of + 1) % len(circle_of_directions)]]
        shuffle(try_these)

        for dir in try_these:
            if cws.is_traversable((unit.x + dir[0], unit.y + dir[1])):
                return Move(dir)

        try_more = [circle_of_directions[index_of - 1],
        circle_of_directions[index_of], 
        circle_of_directions[(index_of + 1) % len(circle_of_directions)]]
        
        random.Random(unit.id).shuffle(try_more)


        # do not attack city if possible.
        for dir in try_more:
            obj = cws.get_coord((unit.x + dir[0], unit.y + dir[1]))
            if obj not in cws.gatherEmpire():
                if obj is not None:
                    if obj.team == cws.team_id and attackFriend==False:
                        return Move(dir)
                    return Attack(obj) 

        if wp_obj is not None:
            return Attack(wp_obj)
        else:
            return DoNothing()




def ExploreFoliage(unit, cws):
    # Discover foliage if there is foliage to discover
    if len(cws.fexplore_waypoints) == 0:
        return None
    
    wp = cws.fexplore_waypoints[0]
    return GetDirectMove(unit, wp, cws)
    
    return None

# archers require non-archers to approach before attacking.
#def ApproachArcher()


def AttackInPlace(unit, cws):
    nearest_enemy = get_nearest_enemy(unit, cws)
    if nearest_enemy is not None:
        if unit.within_range((nearest_enemy.x, nearest_enemy.y)):
            return Attack(nearest_enemy)

    nearest_bld = get_nearest_enemy_building(unit, cws)
    if nearest_bld is not None:
        if unit.within_range((nearest_bld.x, nearest_bld.y)):
                return Attack(nearest_bld)
    
    return None

def Scatter(unit, cws):
    pos = cws.get_scatter_position(unit.id)

    if pos is None:
        return None
        
    return GetDirectMove(unit, pos, cws, attackFriend=False)


# Send the unit to the boarder, if they are at the boarder
def BoarderPatrol(unit, cws):
    # always try attacking if there is something to attack
    turn = AttackInPlace(unit, cws)
    if turn is not None:
        return turn

    pos = cws.get_guard_position(unit.guard_id)

    if pos is None:
        return None

    nearest_bld = get_nearest_enemy_building(unit, cws)

    if nearest_bld is not None:
        if max(abs(pos[0]-nearest_bld.x), abs(pos[1] - nearest_bld.y)) <= 8:
            return GetDirectMove(unit, (nearest_bld.x, nearest_bld.y), cws)
            
    from ai.cpypastas.units import Archer
    nearest_archer = get_nearest_enemy(unit, cws, Archer)
    if nearest_archer is not None:
        if nearest_archer.within_range((unit.x, unit.y)):
            return GetDirectMove(unit, (nearest_archer.x, nearest_archer.y), cws, attackFriend=False)

    return GetDirectMove(unit, pos, cws, attackFriend=False)

def BoarderPatrolBasic(unit, cws):
    # always try attacking if there is something to attack
    turn = AttackInPlace(unit, cws)
    if turn is not None:
        return turn

    pos = cws.get_guard_position(unit.id)

    if pos is None:
        return None

    from ai.cpypastas.units import Archer
    nearest_archer = get_nearest_enemy(unit, cws, Archer)
    if nearest_archer is not None:
        if nearest_archer.within_range((unit.x, unit.y)):
            if len(nearest_archer.island_ids.intersection(unit.island_ids)) != 0:
                step = get_step((unit.x, unit.y), pos)
                return Move([step[0], step[1]])

    if pos is not None:
        step = get_step((unit.x, unit.y), pos)
        return Move([step[0], step[1]])

    return None

def ExploreGeneral(unit, cws):
    from ai.cpypastas.units import Villager

    # Discover foliage if there is foliage to discover
    start = (unit.x, unit.y)

    # We should kill any villagers of the enemy.
    nearest_enemy = get_nearest_enemy(unit, cws, Villager)
    if nearest_enemy is not None:
        if unit.within_range((nearest_enemy.x, nearest_enemy.y)):
            return Attack(nearest_enemy)

        if max(abs(nearest_enemy.x - unit.x), abs(nearest_enemy.y - unit.y)) < 6:
            return GetDirectMove(unit, (nearest_enemy.x, nearest_enemy.y), cws)


    if len(cws.pois) != 0:
        return GetDirectMove(unit, cws.pois[0], cws)



def Wander(unit, cws):
    wgoal = wander_goal(cws)

    if wgoal is None:
        return None

    return GetDirectMove(unit, wgoal, cws)

def WanderBasic(unit, cws):
    wgoal = wander_goal(cws)

    if wgoal is None:
        return None

    for dx in [-1,0,1]:
        for dy in [-1,0,1]:
            if cws.get_island_id(wgoal) == cws.get_island_id((unit.x + dx, unit.y + dy)):
                step = get_step((unit.x, unit.y), wgoal)
                return Move([step[0], step[1]])

    return None