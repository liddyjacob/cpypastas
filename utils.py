from copy import deepcopy
import multiprocessing
from operator import ne
from pickle import TRUE
from turtle import up
from ai.cpypastas.buildings import Barracks, Range, Townhall, Stable
from ai.cpypastas.constants import *
from ai.cpypastas.resources import Unknown
# Given size of Matrix
import heapq as heap
import math
import random
from random import shuffle
import time


def get_vect_length(vect):
    return math.sqrt(vect[0]**2 + vect[1]**2)

def dot_product(vec1, vec2):
    return sum([vec1[i] * vec2[i] for i in range(len(vec1))])

def project_onto(from_vec, onto_vec):
    multiplier = dot_product(from_vec, onto_vec) * dot_product(onto_vec, onto_vec)
    return (multiplier*onto_vec[0], multiplier*onto_vec[1])

def scalar_times_vector(scal, vect):
    return tuple(scal*v for v in vect)

def vector_add(vect1, vect2):
    return tuple(vect1[i] + vect2[i] for i in range(len(vect1)))


def reconstruct_path(cameFrom, current):
    total_path = [current]
    while current in cameFrom.keys():
        current = cameFrom[current]
        total_path.append(current)
    return total_path

def quick_path_a_star(cws, start, end):
    from ai.cpypastas.units import Unit
    
    openSet = set()
    openSet.add(start)

    cameFrom = {}
    gScore = {}
    gScore[start] = 0

    fScore = {}
    fScore[start] = (1)
    
    iterations = 0
    
    while len(openSet) != 0 and iterations < QASTAR_LIMIT:

        iterations += 1

        curr = min(openSet, key=fScore.get)
        if curr == end:
            point_of_interest = reconstruct_path(cameFrom, curr)[-2]
            return (point_of_interest[0] - start[0], point_of_interest[1] - start[1])

        openSet.remove(curr)

        moves = []

        shuffled_diff = [-1,0,1]
        shuffle(shuffled_diff)

        for xk in shuffled_diff: 
            for yk in shuffled_diff:
                if xk != 0 or  yk != 0:
                    moves.append((curr[0] + xk, curr[1] + yk))


        for neighbor in moves:
            if neighbor != end and not cws.is_traversable(neighbor):
                tentative_gScore = gScore[curr] + 100000
            else:
                tentative_gScore = gScore[curr] + 1 
            
            if gScore.get(neighbor) is None:
                gScore[neighbor] = math.inf
            if tentative_gScore < gScore[neighbor]:
                cameFrom[neighbor] = curr
                gScore[neighbor] = tentative_gScore
                randomness = 0
                randomness = random.random()/4
                
                heur_score = max(abs(neighbor[0] - end[0]), abs(neighbor[1] - end[1])) + randomness
                fScore[neighbor] = tentative_gScore + heur_score
                if neighbor not in openSet:
                    openSet.add(neighbor)
    return None

def get_path_a_star(cws, start, end, rand=True, time_limit = .025, passthrough_units = False):
    raise("stop...")
    # Only allow a select period of time for a* algorithm.
    from ai.cpypastas.units import Unit

    openSet = set()
    openSet.add(start)

    cameFrom = {}
    gScore = {}
    gScore[start] = 0

    fScore = {}
    fScore[start] = (1)

    start = time.time()

    while len(openSet) != 0:
        curr = min(openSet, key=fScore.get)
        if curr == end:
            return reconstruct_path(cameFrom, curr)
        
        if time.time() - start > time_limit:
            return reconstruct_path(cameFrom, curr)

        openSet.remove(curr)

        moves = []

        shuffled_diff = [-1,0,1]
        shuffle(shuffled_diff)

        for xk in shuffled_diff: 
            for yk in shuffled_diff:
                if xk != 0 or  yk != 0:
                    moves.append((curr[0] + xk, curr[1] + yk))


        for neighbor in moves:
            if neighbor != end and not cws.is_traversable(neighbor):
                if passthrough_units and issubclass(type(cws.get_coord(neighbor)), Unit):
                    tentative_gScore = gScore[curr] + 1
                else:
                    tentative_gScore = gScore[curr] + 100000
            else:
                tentative_gScore = gScore[curr] + 1 
            
            if gScore.get(neighbor) is None:
                gScore[neighbor] = math.inf
            if tentative_gScore < gScore[neighbor]:
                cameFrom[neighbor] = curr
                gScore[neighbor] = tentative_gScore
                randomness = 0
                if rand:
                    randomness = random.random()/4
                
                heur_score = max(abs(neighbor[0] - end[0]), abs(neighbor[1] - end[1])) + randomness
                fScore[neighbor] = tentative_gScore + heur_score
                if neighbor not in openSet:
                    openSet.add(neighbor)


def build_direct_path(start, goal):
    path = [start]

    while start != goal:
        step = get_step(start, goal)
        start = (start[0] + step[0], start[1] + step[1])
        path.append(start)
    
    return path

# only allow .025 seconds before returning
def get_path_a_star_any(cws, start, goal_type):
    raise("stop...")

    openSet = set()
    openSet.add(start)

    cameFrom = {}
    gScore = {}
    gScore[start] = 0

    fScore = {}
    fScore[start] = (1)

    while len(openSet) != 0:
        curr = min(openSet, key=fScore.get)
        if type(cws.get_coord(curr)) == goal_type:
            return reconstruct_path(cameFrom, curr)

        openSet.remove(curr)

        moves = []

        shuffled_diff = [-1,0,1]
        shuffle(shuffled_diff)

        for xk in shuffled_diff: 
            for yk in shuffled_diff:
                if xk != 0 or  yk != 0:
                    moves.append((curr[0] + xk, curr[1] + yk))


        for neighbor in moves:
            if not cws.is_traversable(neighbor):
                tentative_gScore = gScore[curr] + 100000
            else:
                tentative_gScore = gScore[curr] + 1 
            
            if gScore.get(neighbor) is None:
                gScore[neighbor] = math.inf
            if tentative_gScore < gScore[neighbor]:
                cameFrom[neighbor] = curr
                gScore[neighbor] = tentative_gScore
                heur_score = max(abs(neighbor[0] - 48), abs(neighbor[1] - 48))
                fScore[neighbor] = tentative_gScore + heur_score
                if neighbor not in openSet:
                    openSet.add(neighbor)

def get_step(from_pair, to_pair):
    x_dir = 0
    if from_pair[0] != to_pair[0]:
        x_dir = int(abs(to_pair[0] - from_pair[0])/(to_pair[0] - from_pair[0]))
    
    y_dir = 0
    if from_pair[1] != to_pair[1]:
        y_dir = int(abs(to_pair[1] - from_pair[1])/(to_pair[1] - from_pair[1]))
    
    return (x_dir, y_dir)
    

def valid_coordinate(x,y):
    return ((x >= 0) and x < WSIZE) and ((y >= 0) and y < WSIZE)

# get the nearby coordinates of x and y, and enforce them to 
# pass valid_coordinates(x,y)
# 
def get_nearby_coords(x,y):
    nearby_coords = [(x-1,y), (x, y-1), (x+1, y), (x, y+1)] 
    valid_coords = [(x,y) for (x,y) in nearby_coords if valid_coordinate(x,y)]
    
    return (valid_coords)


def multi_aggregate(exp_weight_map, num_aggregates):
    exp_weight_map = deepcopy(exp_weight_map)

    for i in range(num_aggregates):
        exp_weight_map = aggregate_weight(exp_weight_map)
    
    return exp_weight_map


# Get the gold per turn required to build units from 
# every building as fast as possible.
# Once we have villagers achiving the gold per turn amount,
# we can build villagers as fast as possible
def gold_per_turn_needed(cws):
    # Build up extra gold:
    gold_per_turn_needed = 1
    for building in cws.gatherCity():
        gold_per_turn_needed += building.producecost()[1] / building.turnsToProduce()

    return gold_per_turn_needed

def wood_per_turn_needed(cws):
    wood_per_turn_needed = 0
    for building in cws.gatherCity():
        wood_per_turn_needed += building.producecost()[0] / building.turnsToProduce()

    return wood_per_turn_needed

def handler(signum, frame):
   print('Did not finish in time: signum, frame')
   raise Exception("end of time")


# resource plinko: determine how much gold is needed, and how much wood is needed.
#
WOOD_LEVEL = 0 
def resource_plinko_board(cws):
    global WOOD_LEVEL
    from ai.cpypastas.units import Villager
    needed_gold = gold_per_turn_needed(cws)
    needed_wood = wood_per_turn_needed(cws)
    other = cws.getPopulation(Villager) - (needed_gold + needed_wood)

    if other > 0:
        needed_wood = needed_gold + other
    
    # Now we need to split into how many parts of 13 are needed for each resource.

    WOOD_LEVEL = math.floor(13 * (needed_wood / (needed_wood + needed_gold)))

def get_resource_from_id(id):
    from ai.cpypastas.resources import Tree, Gold

    hash = (17 * id) % 13

    if hash < WOOD_LEVEL:
        #print("getting tree")
        return Tree
    else:
        #print("getting gold")
        return Gold
    
# determine if it is more economical to upgrade a set of units or build a new one:
def upgrade_over_build(cws, typeof):
    if typeof is None:
        return False
    
    if cws.level[typeof] == 3:
        return False

    # if we are rich, upgrade.
    if cws.wood > 400 and cws.gold > 500:
        cws.wood -= (typeof.cost()[0] * 10) 
        cws.gold -= (typeof.cost()[1] * 10) 
        return True

    pop = cws.getPopulation(typeof)

    power_per_gold = typeof.power(cws.level[typeof]) / typeof.cost()[1]
    upgrade_per_gold = pop / (typeof.cost()[1] * 10) 

    # upgrade if power per gold is comparable(health benefits make up the rest)
    return power_per_gold < (upgrade_per_gold * 2)

def wander_goal(cws):
    if len(cws.wander_locations) == 0:
        return None

    mod_time = int(time.time()/10) % 12
    # return the corners of the empire, cycling on the mod_time value m
    if mod_time <= 5:
        return cws.wander_locations[0 % len(cws.wander_locations)]
    if mod_time <= 7:
        return cws.wander_locations[1 % len(cws.wander_locations)]
    
    return cws.wander_locations[2 % len(cws.wander_locations)]


def scatter_time():
    mod_time = int(time.time()/20) % 6
    return mod_time == 0

def get_next_building(cws):
    from ai.cpypastas.units import Archer
    # Always need 1 townhall
    if cws.num_buildings(Townhall) < 1:
        return Townhall

    # Then build a barracks, for guards:
    if cws.num_buildings(Barracks) < 1:
        return Barracks

    # Then another townhall
    if cws.num_buildings(Townhall) < 2:
        return Townhall

    # Then 2 archery ranges:
    if cws.num_buildings(Range) < 2:
        return Range

    # check if we need to reserve money for archery ranges:
    if upgrade_over_build(cws, Archer):
        return None

    if cws.num_buildings(Stable) < 2:
        return Stable

    # Finally, one more townhall
    if cws.num_buildings(Townhall) < 3:
        return Townhall

    return Range


def get_nearest_enemy(unit, cws, subclass = None):
    from ai.cpypastas.units import Unit
    if subclass is None:
        subclass = Unit

    relevant_enemies = [eu for eu in cws.gatherEnemyEmpire() if issubclass(type(eu), subclass)]
    if len(relevant_enemies) == 0:
        return None
    
    nearest_enemy = min(relevant_enemies, key=lambda eu: max(
        abs(eu.x - unit.x), 
        abs(eu.y - unit.y)))
    return nearest_enemy

def get_nearest_enemy_building(unit, cws, subclass = None):
    from ai.cpypastas.buildings import Building
    if subclass is None:
        subclass = Building

    relevant_blds = [eb for eb in cws.gatherEnemyCity() if issubclass(type(eb), subclass)]
    if len(relevant_blds) == 0:
        return None
    
    nearest_b = min(relevant_blds, key=lambda eb: max(
        abs(eb.x - unit.x), 
        abs(eb.y - unit.y)))
    return nearest_b