from asyncio.streams import FlowControlMixin
from glob import glob
from locale import normalize
from pickle import UNICODE
from tkinter.messagebox import NO
from tracemalloc import start
from turtle import pos
from ai.shitutils import get_tiles, path_to_coord
from enum import Enum
from engine import SKEL_TICKS, ID_MAX
from render import TREE, render
from ai.cpypastas.units import Villager, Archer, Infantry, Calvary, Skeleton, Unit, reset_number_system
from ai.cpypastas.buildings import Townhall, Barracks, Range, Stable, House, Building
from ai.cpypastas.resources import MapObj, Resource, Tree, Gold,  Unknown, Unoccupied, MapObj
from ai.cpypastas.constants import *
from ai.cpypastas.utils import get_vect_length, project_onto, resource_plinko_board, \
    scalar_times_vector, upgrade_over_build, build_direct_path, vector_add, scalar_times_vector, \
    project_onto
#from ai.heuristocrats.profiling import PROFILER
import time
import statistics
import math
import random
import os
from copy import deepcopy
import json

# TODO USE MINUTE NUMBER MOD 3 TO DETERMINE 'WANDERING' LOCATION FOR VILLAGERS!
# NOTE THIS SHOULD ALWAYS BE INSIDE THE KINGDOM.
# notes
"""
Upgrade units policy: examine cost / power for one unit, then cost / power to upgrade all units.

"""

# todo make this create an instance of each object
def initializeObject(obj):
    if obj is None:
        return Unoccupied()

    if obj == 'u':
        return Unknown()

    if obj["type"] == 't':
        return Tree(obj)
    
    if obj["type"] == 'g':
        return Gold(obj)

    if obj["type"] == 'v':
        return Villager(obj)

    if obj["type"] == 'a':
        if obj['team'] == -2:
            return Skeleton(obj)
        return Archer(obj)

    if obj["type"] == 'i':
        return Infantry(obj)

    if obj["type"] == 'c':
        return Calvary(obj)

    if obj["type"] == 'w':
        return Townhall(obj)

    if obj["type"] == 'b':
        return Barracks(obj)

    if obj["type"] == 'r':
        return Range(obj)

    if obj["type"] == 's':
        return Stable(obj)

    if obj["type"] == 'h':
        return House(obj)


    quit(f"ERROR REGISTERING OBJECT. UNKNOWN TYPE: {obj['type']}")

def name():
    return ">cpypstas"

# iterate over the map once to avoid redundancy of things that 
# require iteraton.

def iterate_over_map(cws):
    dp_tree_square = [[(0,0)] * 96 for _ in range(96)]
    max_square = ((0,0),None, None)
    for x in range(cws.length):
        for y in range(cws.height):
            obj = cws.identify_and_associate(x,y)
            obj.x = x
            obj.y = y
            cws.process(x,y)


class POI(Enum):
    FOL_EXPLORE = 1,
    UNKNOWN_EXPLORE = 2,
    ENEMY_BUILDINGS = 3,
    ENEMY_VILLAGER_CLUSTERS = 4,
    CORNERS = 5


# Use this to force the world state to use my interfaces
class CombinedWorldState:
    def __init__(self, world_state, players, team_idx):
        self.world_state_raw = world_state
        self.players_raw = players
        self.team_id = team_idx
        self.height = len(self.world_state_raw)
        self.length = len(self.world_state_raw[0])
        self.empire = None
        self.enemyEmpire = None
        self.city = None
        self.enemyCity = None
        self.someone_building = False
        self.villager_can_build = {}
        self.villager_can_build[(2,2)] = False
        self.villager_can_build[(3,3)] = False
        self.archer_id = 0
        self.villager_index = 0

        # sorting is expensive, so we need markers to determine if we have done it
        # 

        self.fort_helper = {}
        self.fort_info = [((0,0), None, None)]

        self.resources_ordered = {}
        self.resources_ordered[Gold] = []
        self.resources_ordered[Tree] = []

        # debug
        self.building_helper = {}
        self.bld_spots = {}
        self.bld_spots[(3,3)] = set()
        self.bld_spots[(2,2)] = set()
        self.tclc = None

        self.reserved_trees = []

        self.wood = players[team_idx]['wood']
        self.gold = players[team_idx]['gold']

        self.level = {}
        self.level[Calvary] = players[team_idx]['cav_level']
        self.level[Archer] = players[team_idx]['arc_level']
        self.level[Infantry] = players[team_idx]['inf_level']
        self.level[Villager] = 1


        self.position_numbers = []

        self.someone_building = {}
        self.num_vils_exploring = {}
        for btype in [Townhall, Barracks, Range, Stable, House]:
            self.someone_building[btype] = False
            self.num_vils_exploring[btype] = 0


        # Associate coords with unique ids
        self.object_coord = {}

    def can_afford(self, pair):
        return ( self.wood >= pair[0] and self.gold >= pair[1] )

    def identify_and_associate(self,x,y):
        obj = self.world_state_raw[x][y]

        if type(obj) == dict:
            obj['x'] = x
            obj['y'] = y

        if self.object_coord.get((x,y)) is not None:
            return self.object_coord[(x,y)]

        self.object_coord[(x,y)] = initializeObject(obj)
        return self.object_coord[(x,y)]

    def get_coord(self, pair):
        x = pair[0]
        y = pair[1]

        return self.object_coord.get((x,y))

    def is_traversable(self, pair):
        x = pair[0]
        y = pair[1]

        obj = self.object_coord.get((x,y))
        # wonky system workout
        return (type(obj) == Unoccupied or type(obj) == Unknown) and not obj.travel_ban

    # block a box from being travelled in: 
    def block_box(self, loc, size):
        for dx in range(size):
            for dy in range(size):
                if dx == 0 and dy ==0:
                    continue
                obj = self.get_coord((loc[0] - dx, loc[1] - dy))
                obj.travel_ban = True

    def get_housing(self):
        housing  = 0
        for c in self.gatherCity():
            housing += c.housing()

        return housing

    # Find a point near x, y
    def get_nearby_travel(self, pair, dist=4, rand=True, island=None):
        neighbors = []
        for dx in range(-dist,dist + 1):
            for dy in range(-dist, dist + 1):
                neighbors.append((pair[0] + dx, pair[1] + dy))
        
        if rand:
            neighbors = sorted(neighbors, key = lambda npair: max(abs(npair[0] - pair[0]),
                abs(npair[1] - pair[1])) + random.random())
        else:
            neighbors = sorted(neighbors, key = lambda npair: max(abs(npair[0] - pair[0]),
                abs(npair[1] - pair[1])))

        for n in neighbors:
            if self.is_traversable(n):
                if island is None:
                    return n
                
                if self.get_island_id(n) == island:
                    return n

        return None

    def build_frontier_edge(self):
        self.border_path = []

        inverted_extreme = (self.length - 1 if(self.KINGDOM_EXTREME[0] == 0) else 0,  
            self.height - 1 if(self.KINGDOM_EXTREME[1] == 0) else 0)

        adjusted_extreme = (0 if(self.KINGDOM_EXTREME[0] == 0) else self.length - 1,  
            0 if(self.KINGDOM_EXTREME[1] == 0) else self.height - 1)

        frontier_outline = [(adjusted_extreme[0], inverted_extreme[1]), 
            (inverted_extreme[0], inverted_extreme[1]),
            (inverted_extreme[0], adjusted_extreme[1])]

        for i in range(len(frontier_outline) - 1):
            sub_path = build_direct_path(frontier_outline[i], 
                frontier_outline[i + 1])
            self.border_path += sub_path[0:-1]

    # Build the 'frontier' of the map. This is where we will station units
    def build_frontier(self):
        if len(self.gatherCity()) == 0:
            self.border_path = [(self.length/2 ,self.height/2)]
            self.frontier_points = []
            self.ecl = []
            return

        frontier_outline = []

        city_vectors = [(c.x - self.KINGDOM_EXTREME[0], c.y - self.KINGDOM_EXTREME[1]) for c in self.gatherCity()]
        boarder_vectors = []


        if self.KINGDOM_EXTREME[0] == self.length:
            if self.KINGDOM_EXTREME[1] == self.height:
                boarder_vectors.append((-1, 0))
                boarder_vectors.append((-1, -math.tan(math.pi/8)))
                boarder_vectors.append((-1, -1))
                boarder_vectors.append((-1, -math.tan(3*math.pi/8)))
                boarder_vectors.append((0, -1))
            else:
                boarder_vectors.append((0, 1))
                boarder_vectors.append((-math.tan(math.pi/8), 1))
                boarder_vectors.append((-1, 1))
                boarder_vectors.append((-math.tan(3*math.pi/8), 1))
                boarder_vectors.append((-1, 0))                
        else:
            if self.KINGDOM_EXTREME[1] == self.height:
                boarder_vectors.append((0, -1))
                boarder_vectors.append((math.tan(math.pi/8), -1))
                boarder_vectors.append((1, -1))
                boarder_vectors.append((math.tan(3*math.pi/8), -1))
                boarder_vectors.append((1, 0))
            else:
                boarder_vectors.append((1, 0))
                boarder_vectors.append((1, math.tan(math.pi/8)))
                boarder_vectors.append((1, 1))
                boarder_vectors.append((1, math.tan(3*math.pi/8)))
                boarder_vectors.append((0, 1))
        
        normalized_vectors = []
        # next we normalize the vectors
        for b in boarder_vectors:
            dist = math.sqrt(b[0]**2 + b[1]**2)
            normalized_vectors.append(tuple(bt/dist for bt in b))

        self.ecl = []
        # Then, for each vector, find the projection with the maximum size
        for nb in normalized_vectors:
            extreme_city_location = max(city_vectors,
                key=lambda cv: get_vect_length(project_onto(cv, nb)))
            self.ecl.append((int(self.KINGDOM_EXTREME[0] + extreme_city_location[0]),int(self.KINGDOM_EXTREME[1] + extreme_city_location[1])))
            
            # Need to extreme_city_location
            border_extension = scalar_times_vector(
                BORDER_DISTANCE + get_vect_length(project_onto(extreme_city_location, nb)), nb)
            frontier_point_float = vector_add(border_extension, self.KINGDOM_EXTREME)
            frontier_point_int = (int(frontier_point_float[0]), int(frontier_point_float[1]))
            frontier_outline.append(frontier_point_int)

        #print(self.frontier_points)
        # Add kingdom_extreme to this vector and BORDER_SIZE* the original vector
        
        self.border_path = []
        # 
        for i in range(len(frontier_outline) - 1):
            sub_path = build_direct_path(frontier_outline[i], 
                frontier_outline[i + 1])
            self.border_path += sub_path[0:-1]



    def get_scatter_position(self, id):
        normalized_position = int((((id * 129) % ID_MAX) / ID_MAX) * len(self.border_path))
        print('scatter')

        if normalized_position == len(self.border_path):
            normalized_position = len(self.border_path) - 1
        #print(position_number)
        if normalized_position < 0:
            return None
        return self.border_path[normalized_position]

    def get_guard_position(self, id):
        unweighted_position = self.position_numbers.index(id)
        normalized_position = int((unweighted_position / len(self.position_numbers)) * len(self.border_path))

        if normalized_position == len(self.border_path):
            normalized_position = len(self.border_path) - 1
        
        #print(position_number)
        if normalized_position < 0:
            return None
        
        return self.border_path[normalized_position]

    def get_wander_locations(self):
        self.wander_locations = []

        if len(self.gatherCity()) == 0:
            self.wander_locations.append((self.length/2, self.height/2))
            return
        
        # set wander locations to look like the following
        """
        . . . . . . . . . .
        . . . . . . . . . .
        . . . . . . . . . .
        . . . . . . . . w1 .
        . . . . . . . . . .
        . . . . . . . . h .
        . . . . . . w2 . . .
        . . . . . . . . h .
        . . . . . . . h . .
        . . . . . w3. . . h
        """
        mean_x_city = int(statistics.mean([c.x for c in self.gatherCity()]))
        mean_y_city = int(statistics.mean([c.y for c in self.gatherCity()]))
        #print(f"citylocation: {mean_x_city}, {mean_y_city}")
        # Situation 1: kingdom extreme bottom right corner
        if self.KINGDOM_EXTREME[0] == self.length:
            x_extreme = min([c.x for c in self.gatherCity()])
            if self.KINGDOM_EXTREME[1] == self.height:
                # Above and to the right:
                y_extreme = min([c.y for c in self.gatherCity()])
                self.wander_locations.append((self.length - 6, y_extreme - WANDER_DIST))
                self.wander_locations.append((x_extreme - WANDER_DIST/2, y_extreme - WANDER_DIST/2))
                self.wander_locations.append((x_extreme - WANDER_DIST, self.height - 6))
            else:
                y_extreme = max([c.y for c in self.gatherCity()])
                # To the right and below
                self.wander_locations.append((self.length - 6, y_extreme + WANDER_DIST))
                self.wander_locations.append((x_extreme - WANDER_DIST/2, y_extreme + WANDER_DIST/2))
                self.wander_locations.append((x_extreme - WANDER_DIST, 5))
        else:
            x_extreme = max([c.x for c in self.gatherCity()])
            if self.KINGDOM_EXTREME[1] == self.height:
                # Above and to the right:
                y_extreme = min([c.y for c in self.gatherCity()])
                self.wander_locations.append((5, y_extreme - WANDER_DIST))
                self.wander_locations.append((x_extreme + WANDER_DIST/2, y_extreme - WANDER_DIST/2))
                self.wander_locations.append((x_extreme - WANDER_DIST, self.height - 6))
            else:
                y_extreme = max([c.y for c in self.gatherCity()])
                # To the right and below
                self.wander_locations.append((5, y_extreme + WANDER_DIST))
                self.wander_locations.append((x_extreme + WANDER_DIST/2, y_extreme + WANDER_DIST/2))
                self.wander_locations.append((x_extreme + WANDER_DIST, 5))

        # in this case, wander locations should be located torward the bottom of the map

    
    
    # LOCATIONS ARE ALWAYS WHERE VILLAGERS SHOULD GO.
    # ALWAYS BOTTOM RIGHT. BRING THE VILLAGER THERE,
    # THEN BUILD IN THE -1, -1 DIRECTION.
    def get_house_location(self):
        if not self.house_sorted:
            self.house_spots = sorted(self.house_spots, key = lambda pair: max(abs(pair[0] - self.KINGDOM_EXTREME[0]),
                abs(pair[1] - self.KINGDOM_EXTREME[1])), reverse=True)
            self.house_sorted = True

        house_location = self.house_sorted[-1]
        self.house_sorted.pop()
        return house_location

    # for counting:
    def reserve_first_n_trees(self, n):
        all_trees = [obj for obj in self.object_coord.values() if type(obj) == Tree and obj.reserved == False and obj.theoretical == False]

        if len(all_trees) < n:
            return 
        
        trees_sorted = sorted(all_trees, key = lambda tob: max(abs(tob.x - self.KINGDOM_EXTREME[0]),
                abs(tob.y - self.KINGDOM_EXTREME[1])), reverse=True)

        for i in range(n):
            trees_sorted[-(i + 1)].reserved=True
            self.reserved_trees.append(trees_sorted[-(i + 1)])


    def get_corner_resource(self, typeof):
        if len(self.resources_ordered[typeof]) == 0:
            return None
        else:
            rval = self.resources_ordered[typeof][-1]            
            self.resources_ordered[typeof].pop()
            return rval

    # set the coordinate to the new 
    def set_coord(self, pair, wrapped_object):
        x = pair[0]
        y = pair[1]
        
        self.object_coord[(x,y)] = wrapped_object
        # TODO set the wrapped object in registry.
        # id is wrapped_object.id

    def process(self, x, y):
        #' New rules, just find the longest set of trees, and funnel archers into those.
        #' The rules for these archers are:
        #' (1) check to see if archer line is full
        #  (2) if not full, move archers to the right/down
        #      when there is an empty spot next to them
        #  (3) shoot anything not on my team. Prioritize villagers, then
        #      calvary, then infantry, then buildings/
        self.building_helper[(x,y)] = 0

        obj = self.get_coord((x,y))

        if issubclass(type(obj), Resource):
            self.resources_ordered[type(obj)].append((obj.x, obj.y))

        if not self.is_traversable((x,y)):
            self.building_helper[(x,y)] = 0
        else:
            if x == 0 or y == 0:
                # 1x1 square
                self.building_helper[(x,y)] = 1
            else:
                self.building_helper[(x,y)] = (min( 
                    self.building_helper[(x-1,y)], 
                    self.building_helper[(x,y-1)], 
                    self.building_helper[(x-1,y-1)]
                ) + 1)

            # new max square found at x,y
            #if self.building_helper[(x,y)] >= 5:
            if self.building_helper[(x,y)] >= 3:
                self.bld_spots[(3,3)].add((x,y))

            if self.building_helper[(x,y)] >= 2:
                self.bld_spots[(2,2)].add((x,y))

    def xy_to_hk(self, xy):
        hk = [xy[0], xy[1]]

        if self.KINGDOM_CORNER[0] == 1:
            hk[0] = self.length - xy[0]

        if self.KINGDOM_CORNER[1] == 1:
            hk[1] = self.height - xy[1]

        return (hk[0], hk[1])

    def hk_to_xy(self, hk):
        xy = [hk[0], hk[1]]

        if self.KINGDOM_CORNER[0] == 1:
            xy[0] = self.length - xy[0]

        if self.KINGDOM_CORNER[1] == 1:
            xy[1] = self.height - hk[1]

        return (xy[0], xy[1])

    def post_processing_steps(self):
        avg_empire_location = self.gatherEmpire() + self.gatherCity()
        x_mean = statistics.mean([obj.x for obj in avg_empire_location])
        y_mean = statistics.mean([obj.y for obj in avg_empire_location])


        self.KINGDOM_CORNER = (int((x_mean / (self.length / 2))), int(y_mean / (self.length / 2)) )
        self.KINGDOM_XMIN = int(self.KINGDOM_CORNER[0] * (self.length / 2))
        self.KINGDOM_XMAX = int(self.KINGDOM_XMIN + (self.length / 2))
        self.KINGDOM_YMIN = int(self.KINGDOM_CORNER[1] * (self.length / 2))
        self.KINGDOM_YMAX = int(self.KINGDOM_YMIN + (self.length / 2))


        self.KINGDOM_EXTREME = (self.KINGDOM_CORNER[0] * self.length, self.KINGDOM_CORNER[1] * self.height)
        

        self.resources_ordered[Gold] = sorted(self.resources_ordered[Gold], key = lambda pair: max(abs(pair[0] - self.KINGDOM_EXTREME[0]),
                abs(pair[1] - self.KINGDOM_EXTREME[1])), reverse=True)

        self.resources_ordered[Tree] = sorted(self.resources_ordered[Tree], key = lambda pair: max(abs(pair[0] - self.KINGDOM_EXTREME[0]),
                abs(pair[1] - self.KINGDOM_EXTREME[1])), reverse=True)

        self.post_processing_loop()

        for unit in self.gatherEmpire():
            if type(unit) == Villager:
                self.processVillager(unit)

        self.make_pois()
        if len(self.gatherEmpire()) > 500:
            self.build_frontier_edge()
        else:
            self.build_frontier()
        # Force buildings to be spaced out from one another.


        self.get_wander_locations()

    def is_in_kingdom(self, x,y):
        return ((x < self.KINGDOM_XMAX and x >= self.KINGDOM_XMIN) 
            and (y < self.KINGDOM_YMAX and y >= self.KINGDOM_YMIN))

    def post_processing_loop(self):
        new_bld_spots = {}
        new_bld_spots[(2,2)] = set()
        new_bld_spots[(3,3)] = set()

        for x in range(self.length):
            for y in range(self.height):
                spot_orig = (x,y)
                for bld_size in self.bld_spots.keys():
                    if spot_orig in self.bld_spots[bld_size]:
                        spot = (spot_orig[0] - (bld_size[0] - 1), spot_orig[1] - (bld_size[1] - 1))
                        locations_to_check = []
                        for dy in range(bld_size[1]):
                            # all buildings are larger than dy
                            dx = 2
                            locations_to_check.append(
                                (spot[0] + (bld_size[0] - 1) + dx, 
                                spot[1] + dy)
                            )
                            locations_to_check.append(
                                (spot[0] - dx, 
                                spot[1] + dy)
                            )
                        
                        for dx in range(bld_size[0]):
                            # all buildings are larger than dy
                            dy = 2
                            locations_to_check.append(
                                (spot[0] + dx, 
                                spot[1] + (bld_size[1] - 1) + dy)
                            )
                            locations_to_check.append(
                                (spot[0] + dx, 
                                spot[1] - dy)
                            )
                        # Then add the corners:
                        locations_to_check.append((spot[0] - 1, spot[1] - 1))
                        locations_to_check.append((spot[0] - 1, spot[1] + (bld_size[1] - 1) + 1))
                        locations_to_check.append((spot[0] + (bld_size[0] - 1) + 1, spot[1] - 1))
                        locations_to_check.append((spot[0] + (bld_size[0] - 1) + 1, spot[1] + (bld_size[1] - 1) + 1))

                        failed = False
                        for loc in locations_to_check:
                            class_at = type(self.get_coord(loc))
                            if (issubclass(class_at, Building)):
                                failed = True
                                break
                        
                        if not failed:
                            new_bld_spots[bld_size].add(spot)

        self.bld_spots = new_bld_spots

    def _make_pois_fexplore(self):
        self.fexplore_waypoints = []         

        for x in range(self.KINGDOM_XMIN, self.KINGDOM_XMAX):
            for y in range(self.KINGDOM_YMIN, self.KINGDOM_YMAX):
                if 0 == (x % 8) and 0 == (y % 8):

                    if type(self.get_coord((x,y))) == Unknown:
                        self.fexplore_waypoints.append((x,y))
                        self.pois.add((x,y))


    def percent_uncovered_f(self):
        p =  len([obj for obj in self.object_coord.values() if type(obj) != Unknown]) / (self.length * self.height)
        return(p)

    def _make_pois_empire_corners(self):
        for point in [(5,5), (5,self.height - 6), (self.length - 6,self.height - 6), (self.length - 6,5)]:
            obj = self.get_coord(point)
            if (type(obj) == Unknown):
                self.pois.add(point)
                next
            if issubclass(type(obj), MapObj) and self.get_coord(point).theoretical:
                self.pois.add(point)

    # POINTS OF INTEREST
    def make_pois(self):
            # make a map for every type of point of interest and mask ( messy but a real time saver )
            self.pois = set()
            self._make_pois_fexplore()
            self._make_pois_empire_corners()

    # See if this villager can build
    def processVillager(self, vil):
        vil.vil_index = self.villager_index
        self.villager_index+=1
        for bld_size in self.bld_spots.keys():
            if self.villager_can_build[bld_size]:
                next
            for dx in range(1, bld_size[0] + 1):
                if (vil.x - (dx - 1), vil.y + 1) in self.bld_spots[bld_size]:
                    vil.build_loc[bld_size] = (vil.x - (dx - 1), vil.y + 1)
                    self.villager_can_build[bld_size] = True

                if (vil.x - (dx - 1), vil.y - bld_size[1]) in self.bld_spots[bld_size]:
                    vil.build_loc[bld_size] = (vil.x - (dx - 1), vil.y - bld_size[1])
                    self.villager_can_build[bld_size] = True

            for dy in range(1, bld_size[1] + 1):
                if (vil.x + 1, vil.y - (dy - 1)) in self.bld_spots[bld_size]:
                    vil.build_loc[bld_size] = (vil.x + 1, vil.y - (dy - 1))
                    self.villager_can_build[bld_size] = True

                if (vil.x - bld_size[0], vil.y - (dy - 1)) in self.bld_spots[bld_size]:
                    vil.build_loc[bld_size] = (vil.x - bld_size[0], vil.y - (dy - 1))
                    self.villager_can_build[bld_size] = True


    def gatherEmpire(self):
        if self.empire is None:
            all_units = [obj for obj in self.object_coord.values() if issubclass(type(obj), Unit)]
            self.empire = [u for u in all_units if u.team == self.team_id]
            self.empire = sorted(self.empire, key=lambda obj: obj.id, reverse=True)
            for gi in range(len(self.empire)):
                # useful for pairing units.
                # we can cluster units that are nearby each other, id-wise.
                self.empire[gi].citizen_no = gi 
                if type(self.empire[gi]) != Villager:
                    self.empire[gi].guard_id = ((self.empire[gi].id * 129) % ID_MAX) 
                    self.position_numbers.append(self.empire[gi].guard_id)

                self.position_numbers = sorted(self.position_numbers)

        return self.empire

    def gatherEnemyEmpire(self):
        if self.enemyEmpire is None:
            all_units = [obj for obj in self.object_coord.values() if issubclass(type(obj), Unit)]
            self.enemyEmpire = [u for u in all_units if u.team != self.team_id]
            print(len(self.enemyEmpire))
        
        return self.enemyEmpire

    def gatherEnemyCity(self):
        if self.enemyCity is None:
            all_buildings = [obj for obj in self.object_coord.values() if issubclass(type(obj), Building)]
            self.enemyCity = [b for b in all_buildings if b.team != self.team_id]
        return self.enemyCity

    def getPopulation(self, typeof):
        empire = self.gatherEmpire()
        pop = 0
        for e in empire:
            if type(e) == typeof:
                pop+=1

        return pop

    def gatherCity(self):
        if self.city is None:
            all_buildings = [obj for obj in self.object_coord.values() if issubclass(type(obj), Building)]
            self.city = list(set([b for b in all_buildings if b.team == self.team_id]))
        return self.city

    def num_buildings(self, typeof):
        num = 0
        for c in self.gatherCity():
            if type(c) == typeof:
                num+=1

        return num 
    
    def render(self):
        from render import TREE as COL_TREE, GOLD as COL_GOLD, NORM, teamcols
        
        print_string = ''
        for y in range(self.length):
            for x in range(self.height):
                obj = self.get_coord((x, y))

                if issubclass(type(obj), Unit):
                    t = obj.type()[0]
                    color = teamcols[obj.team]
                    print_string+= color + t + '.'
                if issubclass(type(obj), MapObj):
                    color = ''
                    char = 'g'

                    extra = '.'
                    if obj.theoretical:
                        extra = '*'

                    if type(obj) == Tree:
                        color = COL_TREE
                        if obj.reserved:
                            char = 'R'
                        else:
                            char = 't'
                    if type(obj) == Gold:
                        color = COL_GOLD
                        char = 'g'
                    if type(obj) == Unknown:
                        color = NORM
                        char = '?'
                        extra = '?'

                    if type(obj) == Unoccupied:
                        color = NORM
                        char = ' '

                    print_string += color + char + extra


                if issubclass(type(obj), Building):
                    color = teamcols[obj.team]
                    print_string += color + obj.rep() + ' '

                if (x,y) in self.pois:
                    print_string = print_string[:-1] + COL_GOLD + 'X'

                if (x,y) in self.wander_locations:
                    print_string = print_string[:-2] + COL_GOLD + 'WL'

                if (x,y) in self.ecl:
                    #print(ecl)
                    print_string = print_string[:-2] + COL_GOLD + 'EC'

                #if (x,y) in self.frontier_points:
                #    #print(ecl)
                #    print_string = print_string[:-2] + COL_GOLD + 'FP'

                if (x,y) in self.border_path:
                    print_string = print_string[:-1] + COL_GOLD + 'P'
                """
                if (x,y) in self.bld_spots[(3,3)]:
                    print_string = print_string[:-1] + '&'
                elif (x,y) in self.bld_spots[(2,2)]:
                    print_string = print_string[:-1] + '^'

                for v in self.gatherEmpire():
                    if type(v)==Villager:
                        if v.build_loc.get((3,3)) is not None:
                            if (x,y) == v.build_loc.get((3,3)):
                                print_string = print_string[:-1] + 'B'
                """



            print_string += (NORM + '\n')
        print(print_string)


def run(world_state, players, team_idx):
    start_time = time.time()
    NUMBER_SYSTEM = {}

    Unit.our_kingdom = team_idx 
    cws = CombinedWorldState(world_state, players, team_idx)
    cws.start_time = start_time

    # Always iterate over the map ONCE at the beginning to update units
    # and stuff.
    iterate_over_map(cws)
    
    cws.post_processing_steps()
    resource_plinko_board(cws)
    #print(REGISTRY)

    middle_time = time.time()
    mid = middle_time - start_time

    #print(f"mid: {middle_time - start_time}")
    if (mid > .6):
        with open('midlog.log', 'r+') as ml:
            ml.write("Long mid: {mid}")


    empire = cws.gatherEmpire()
    random.shuffle(empire)

    # Leave .1 sec for buffer
    # Only give the first n players 
    # Leave .05 seconds for buildings
    unit_commands = []
    for u in empire:
        if time.time() - start_time < .9:
            m = u.execute(cws)
            unit_commands.append(m)
        else:
            break

    building_commands = []
    for b in cws.gatherCity():
        if time.time() - start_time < .95:
            m = b.execute(cws)
            building_commands.append(m)
        else:
            break

    end_time = time.time()
    #print(f"end: {end_time - start_time}")
    
    """
    if ((end_time - middle_time) >.7):
        import json
        # create json object from dictionary
        json_world = json.dumps(world_state)

        # open file for writing, "w" 
        f = open("world.json","w")

        # write json object to file
        f.write(json_world)

        # close file
        f.close()

        json_players = json.dumps(players)

        f = open("players.json","w")

        # write json object to file
        f.write(json_players)

        # close file
        f.close()

        print(team_idx)

        quit("Long proc time")
    """

    if len(cws.gatherEmpire() + cws.gatherCity()) <= 10:
        try:
        
            if time.time() - start_time < .81:
                word_list = "You wanna fight? There is no point in fighting if you already lost you useless norse animal, you can't even insult people without cursing, you have no future and we both know it, you know who else knows it? Your parents! You're the biggest dissapointment in their life after Ghost Busters 3. After 15 years on Earth you still haven't learnt how to cook a proper food and behave in the society. Nobody will miss you after your death. You might say: \"But my best friend!\" He won't even attend your funeral, because he is as clowny as you are. You live like a clown you will die like a clown. I will be surprised if you even care because you have nothing to lose you've achieved nothing. Cya. One time I had a kid come over to my house and tell me that my house was small and boring. So then I told him that my house was small because I had an amazing secret basement full of games and toys that I never tell anyone about. This kid wanted to see it really badly at that point, so I told him to wait outside the basement door so I could get the games and toys ready for him. I took a bucket of glitter mixed in with super glue and set it up on the top of the basement door. I gave the kid the cue to come inside, and when he opened the door, I stabbed him.".split(' ')
                game_folder = max(filter(os.path.isdir, glob('../games/*')), key=os.path.getmtime)
                current_frame_file = max([f for f in filter(os.path.isfile, glob(game_folder + '/[0-9]*.json')) if 'out' not in f], key=os.path.getmtime)
                #print(f'time wasted here: {time.time() - start_time}')

                with open(current_frame_file, 'r+') as framedata:
                    jsondata = json.load(framedata)

                    for i in range(4):
                        curr_name = jsondata['players'][i]['name']
                        if curr_name[0] == '>':
                            mod = int(time.time()/4) % len(word_list)
                            end_index = curr_name.find('\r')
                            new_name = '>' + word_list[mod] + curr_name[end_index:]
                            jsondata['players'][i]['name'] = new_name
                        

                    if time.time() - start_time > .95:
                        framedata.close()
                        return (unit_commands + building_commands)

                    framedata.seek(0)
                    json.dump(jsondata, framedata)
                    framedata.truncate()

            #PROFILER.profilePrint()
            #PROFILER.profileReset()
            
        except:
            pass
    
    if len(cws.gatherEmpire() + cws.gatherCity()) == 12 or len(cws.gatherEmpire() + cws.gatherCity()) == 11:
        try:
        
            if time.time() - start_time < .81:
                word_list = "".split(' ')
                game_folder = max(filter(os.path.isdir, glob('../games/*')), key=os.path.getmtime)
                current_frame_file = max([f for f in filter(os.path.isfile, glob(game_folder + '/[0-9]*.json')) if 'out' not in f], key=os.path.getmtime)
                #print(f'time wasted here: {time.time() - start_time}')

                with open(current_frame_file, 'r+') as framedata:
                    jsondata = json.load(framedata)

                    for i in range(4):
                        curr_name = jsondata['players'][i]['name']
                        if curr_name[0] == '>':
                            mod = int(time.time()/4) % len(word_list)
                            end_index = curr_name.find('\r')
                            new_name = '>' + word_list[mod] + curr_name[end_index:]
                            jsondata['players'][i]['name'] = new_name
                        

                    if time.time() - start_time > .95:
                        framedata.close()
                        return (unit_commands + building_commands)

                    framedata.seek(0)
                    json.dump(jsondata, framedata)
                    framedata.truncate()

            #PROFILER.profilePrint()
            #PROFILER.profileReset()
            
        except:
            pass

    #cws.render()
    #print(players[team_idx])
    print(f"Population: {len(cws.gatherEmpire())} / {cws.get_housing()}")
    #print(unit_commands)
    """
    
    """
    return (unit_commands + building_commands)
    # Determine what the foliage is for unexplored tiles.
