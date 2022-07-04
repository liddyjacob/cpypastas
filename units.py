from pickle import GLOBAL
from socket import timeout
from threading import current_thread
from ai.cpypastas.moves import Move, Build, Repair, Attack
from ai.cpypastas.utils import gold_per_turn_needed, handler, get_resource_from_id, get_next_building, get_nearest_enemy_building, scatter_time
from ai.cpypastas.buildings import Townhall, Barracks, Range, Stable, House
from ai.cpypastas.resources import Gold, Resource, Tree
from ai.cpypastas.behaviors import *
import math
import signal
import threading
import time
#

class Unit:
    our_kingdom = 0

    def __init__(self, obj):
        global NUMBER_SYSTEM
        self.team = obj["team"]
        self.x = obj['x']
        self.y = obj['y']
        self.move_stack = []
        self.id = obj['id']
        self.team = obj['team']
        self.island_ids = set()
        self.turn = {}
        self.travel_ban = True

    def execute(self, cws):
        self.follow_behaviors(cws)

        #self.follow_behaviors(cws)
        return(self.turn)

    #  default behavior: just check if it is within one coord
    def within_range(self, pair):
        return max(abs(pair[0] - self.x), abs(pair[1] - self.y)) == 1

    # todo update health and stuff
    def update(self, obj):
        self.x = obj['x']
        self.y = obj['y']

    def __hash__(self):
        return hash(self.id)

class Villager(Unit):
    def __init__(self, obj):
        super().__init__(obj)
        self.build_loc = {} 

    @staticmethod
    def power(level):
        return 1
    
    def follow_behaviors(self, cws):
        # if that fails, attack an enemy
        nearest_enemy = get_nearest_enemy(self, cws)
        if nearest_enemy is not None:
            if self.within_range((nearest_enemy.x, nearest_enemy.y)):
                return Attack(nearest_enemy).apply(self)

        if len(cws.gatherCity()) == 0:
            # no purpose in building so early without gold:
            if cws.gold <= 10:
                turn = AttackNearbyResource(self, cws, Gold)
                if turn:
                    self.turn = turn.apply(self)
                    return

                turn = GetNearbyResource(self, cws, Gold)
                if turn:
                    self.turn = turn.apply(self)
                    return

            turn = BuildThing(self, cws, Townhall)
            if turn:
                self.turn = turn.apply(self)
                return

        # see if there are any buildings nearby to repair:
        turn = RepairNearby(self,cws)
        if turn:
            self.turn = turn.apply(self)
            return

        # scatter the villagers
        if scatter_time():
            turn = Scatter(self, cws)
            if turn:
                self.turn = turn.apply(self)
                return


        
        # build houses if a house is needed
        if cws.get_housing() < len(cws.gatherEmpire()) + 1.5 * len(cws.gatherCity()) - 1.5 * cws.num_buildings(House) + 4:
            if cws.can_afford(House.buildcost()):
                turn = BuildThing(self, cws, House)
                if turn:
                    self.turn = turn.apply(self)
                    return

        # lol build town halls everywhere
        buildingtype = get_next_building(cws)

        if buildingtype is not None:
            if cws.can_afford(buildingtype.buildcost()):
                turn = BuildThing(self, cws, buildingtype)
                if turn:
                    self.turn = turn.apply(self)
                    return

        #if high enough population, ignore villager shuffling when possible:
        if cws.getPopulation(Villager) > 8:
            if self.vil_index == 0:
                turn = Wander(self, cws)
                if turn:
                    self.turn = turn.apply(self)
                    return

            turn = AttackNearbyResource(self, cws, Gold)
            if turn:
                self.turn = turn.apply(self)
                return

            turn = AttackNearbyResource(self, cws, Tree)
            if turn:
                self.turn = turn.apply(self)
                return

        # also once we have 12 villagers, we should assign jobs by modulating id
        if cws.getPopulation(Villager) >= 13:
            rtype = get_resource_from_id(self.id)
            turn = GetNearbyResource(self, cws, rtype)
            if turn:
                self.turn = turn.apply(self)
                return
        
        else:
            gold_req = gold_per_turn_needed(cws)

            if self.vil_index <= math.ceil(gold_req):
                # first, see if there is any gold nearvy
                turn = AttackNearbyResource(self, cws, Gold)
                if turn:
                    self.turn = turn.apply(self)
                    return

                turn = GetNearbyResource(self, cws, Gold)
                if turn:
                    self.turn = turn.apply(self)
                    return

            # get trees from now on
            turn = AttackNearbyResource(self, cws, Tree)
            if turn:
                self.turn = turn.apply(self)
                return

            turn = GetNearbyResource(self, cws, Tree)
            if turn:
                self.turn = turn.apply(self)
                return

    # Time ran out, see if we can get a basic behavior in:
    def follow_basic_behaviors(self, cws):
        # Get Anything
        # if that fails, attack an enemy
        nearest_enemy = get_nearest_enemy(self, cws)
        if nearest_enemy is not None:
            if self.within_range((nearest_enemy.x, nearest_enemy.y)):
                return Attack(nearest_enemy).apply(self)

        # see if there are any buildings nearby to repair:
        turn = RepairNearby(self,cws)
        if turn:
            self.turn = turn.apply(self)
            return

        turn = AttackNearbyResource(self, cws, Resource)
        if turn:
            self.turn = turn.apply(self)
            return

            #if high enough population, ignore villager shuffling when possible:
        if cws.getPopulation(Villager) > 8:
            if self.vil_index == 0:
                turn = WanderBasic(self, cws)
                if turn:
                    self.turn = turn.apply(self)
                    return

        # if that fails, move a random direction
        turn = Move([random.randint(-1,1), random.randint(-1,1)])
        self.turn = turn.apply(self)
        

    @staticmethod
    def type():
        return 'Villager'


class Archer(Unit):
    def __init__(self, obj):
        super().__init__(obj)
        self.in_x_alley = False
        self.in_y_alley = False

    def follow_behaviors(self, cws):
        turn = AttackInPlace(self, cws)
        if turn is not None:
            self.turn = turn.apply(self)
            return

        turn = BoarderPatrol(self, cws)
        if turn:
            self.turn = turn.apply(self)
            return

        turn = GetNearbyResource(self, cws, Tree)
        if turn:
            self.turn = turn.apply(self)
            return


        self.turn = Move([0,0]).apply(self)
        return
        # r
        # only 1 explorer

    # Time ran out, see if we can get a basic behavior in:
    def follow_basic_behaviors(self, cws):
        turn = BoarderPatrolBasic(self, cws)
        if turn:
            self.turn = turn.apply(self)
            return

        nearest_enemy = get_nearest_enemy(self, cws, Villager)
        if nearest_enemy is not None:
            if self.within_range((nearest_enemy.x, nearest_enemy.y)):
                return Attack(nearest_enemy).apply(self)

        nearest_enemy = get_nearest_enemy(self, cws)
        if nearest_enemy is not None:
            if self.within_range((nearest_enemy.x, nearest_enemy.y)):
                return Attack(nearest_enemy).apply(self)

        nearest_building = get_nearest_enemy_building(self, cws)
        if nearest_building is not None:
            if self.within_range((nearest_building.x, nearest_building.y)):
                return Attack(nearest_building).apply(self)

        turn = Move([random.randint(-1,1), random.randint(-1,1)])
        self.turn = turn.apply(self)

    @staticmethod
    def type():
        return 'Archer'

    @staticmethod
    def power(i):
        if i == 1:
            return 1
        if i == 2:
            return 2
        if i == 3:
            return 3

    @staticmethod
    def cost():
        return((10,10))

    #  default behavior: just check if it is within one coord
    def within_range(self, pair):
        return abs(pair[0] - self.x) + abs(pair[1] - self.y) <= 8

class Infantry(Unit):
    def __init__(self, obj):
        super().__init__(obj)

    def follow_behaviors(self, cws):
        turn = AttackInPlace(self, cws)
        if turn is not None:
            self.turn = turn.apply(self)
            return

        turn = BoarderPatrol(self, cws)
        if turn:
            self.turn = turn.apply(self)
            return 

        return
        # r
        # only 1 explorer

    # Time ran out, see if we can get a basic behavior in:
    def follow_basic_behaviors(self, cws):
        turn = AttackInPlace(self, cws)
        if turn is not None:
            self.turn = turn.apply(self)
            return

        next_relevant_index = self.citizen_no + 1

        while len(cws.gatherEmpire()) > next_relevant_index:
            next_obj = cws.gatherEmpire()[next_relevant_index]
            if type(next_obj) == Villager:
                turn = BodyguardBasic(self, next_obj, cws)
                if turn:
                    self.turn = turn.apply(self)
                    return
                break

            if type(next_obj) == Infantry:
                # for anything that is not 
                break

            next_relevant_index+=1


        nearest_enemy = get_nearest_enemy(self, cws, Villager)
        if nearest_enemy is not None:
            if self.within_range((nearest_enemy.x, nearest_enemy.y)):
                return Attack(nearest_enemy).apply(self)

        nearest_enemy = get_nearest_enemy(self, cws)
        if nearest_enemy is not None:
            if self.within_range((nearest_enemy.x, nearest_enemy.y)):
                return Attack(nearest_enemy).apply(self)

        nearest_building = get_nearest_enemy_building(self, cws)
        if nearest_building is not None:
            if self.within_range((nearest_building.x, nearest_building.y)):
                return Attack(nearest_building).apply(self)

        turn = Move([random.randint(-1,1), random.randint(-1,1)])
        self.turn = turn.apply(self)

    @staticmethod
    def power(i):
        if i == 1:
            return 2
        if i == 2:
            return 3
        if i == 3:
            return 4

    @staticmethod
    def type():
        return 'Infantry'

    @staticmethod
    def cost():
        return((0,20))


class Calvary(Unit):
    def __init__(self, obj):
        super().__init__(obj)

    def follow_behaviors(self, cws):
        turn = AttackInPlace(self, cws)
        if turn is not None:
            self.turn = turn.apply(self)
            return

        turn = BoarderPatrol(self, cws)
        if turn:
            self.turn = turn.apply(self)
            return 

        turn = GetNearbyResource(self, cws, Tree)
        if turn:
            self.turn = turn.apply(self)
            return


        self.turn = Move([0,0]).apply(self)
        return
        # r
        # only 1 explorer

    # Time ran out, see if we can get a basic behavior in:
    def follow_basic_behaviors(self, cws):
        nearest_enemy = get_nearest_enemy(self, cws, Villager)
        if nearest_enemy is not None:
            if self.within_range((nearest_enemy.x, nearest_enemy.y)):
                return Attack(nearest_enemy).apply(self)

        nearest_enemy = get_nearest_enemy(self, cws)
        if nearest_enemy is not None:
            if self.within_range((nearest_enemy.x, nearest_enemy.y)):
                return Attack(nearest_enemy).apply(self)

        nearest_building = get_nearest_enemy_building(self, cws)
        if nearest_building is not None:
            if self.within_range((nearest_building.x, nearest_building.y)):
                return Attack(nearest_building).apply(self)

        turn = Move([random.randint(-1,1), random.randint(-1,1)])
        self.turn = turn.apply(self)

    @staticmethod
    def type():
        return 'Calvary'

    @staticmethod
    def power(i):
        if i == 1:
            return 3
        if i == 2:
            return 4
        if i == 3:
            return 5

    @staticmethod
    def cost():
        return((0,40))


class Skeleton(Archer):
    def __init__(self, obj):
        super().__init__(obj)

    @staticmethod
    def type():
        return 'Skeleton'


NUMBER_SYSTEM = {}
NUMBER_SYSTEM[Infantry] = 1
NUMBER_SYSTEM[Villager] = 1
NUMBER_SYSTEM[Calvary] = 1
NUMBER_SYSTEM[Archer] = 1

def reset_number_system():
    global NUMBER_SYSTEM
    global WOOD_TAKEN_CARE_OF
    global GOLD_TAKEN_CARE_OF
    NUMBER_SYSTEM = {}
    NUMBER_SYSTEM[Infantry] = 1
    NUMBER_SYSTEM[Villager] = 1
    NUMBER_SYSTEM[Calvary] = 1
    NUMBER_SYSTEM[Archer] = 1

    GOLD_TAKEN_CARE_OF = 0
    WOOD_TAKEN_CARE_OF = 0