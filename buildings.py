class Building:
    def __init__(self, obj):
        self.team = obj["team"]
        self.x = obj['x']
        self.y = obj['y']
        self.move_stack = []
        self.id = obj['id']
        self.hp = obj['hp']
        self.island_ids = set()
        self.travel_ban = True

    def execute(self, cws):
        from ai.cpypastas.moves import Produce, Upgrade
        from ai.cpypastas.utils import upgrade_over_build
        from ai.cpypastas.units import Infantry, Archer, Calvary

        typeof = None
        if type(self) == Range:
            typeof = Archer
        if type(self) == Barracks:
            typeof = Infantry
        if type(self) == Stable:
            typeof = Calvary
        
        if upgrade_over_build(cws, typeof):
            return Upgrade().apply(self)
        
        return Produce().apply(self)

    def __eq__(self, other):
        if not issubclass(type(other), Building):
            return False
        return self.id == other.id

    def __hash__(self):
        return self.id

    @staticmethod 
    def turnsToProduce():
        return 15

    @staticmethod 
    def size():
        return (3,3)

class Townhall(Building):
    def __init__(self, obj):
        super().__init__(obj)

    @staticmethod
    def buildcost():
        return((200,0))

    @staticmethod
    def producecost():
        return((0,10))


    @staticmethod
    def housing():
        return 9

    @staticmethod
    def max_health():
        return 80

    @staticmethod
    def rep():
        return 'w'

class Barracks(Building):
    def __init__(self, obj):
        super().__init__(obj)

    @staticmethod
    def buildcost():
        return((50,0))

    @staticmethod
    def producecost():
        return((0,20))

    @staticmethod
    def housing():
        return 0

    @staticmethod
    def max_health():
        return 60

    @staticmethod
    def rep():
        return 'b'

class Range(Building):
    def __init__(self, obj):
        super().__init__(obj)

    @staticmethod
    def buildcost():
        return((70,0))

    @staticmethod
    def producecost():
        return((10,10))

    @staticmethod
    def housing():
        return 0

    @staticmethod
    def max_health():
        return 60

    @staticmethod
    def rep():
        return 'r'


class Stable(Building):
    def __init__(self, obj):
        super().__init__(obj)

    @staticmethod
    def buildcost():
        return((90,0))

    @staticmethod
    def producecost():
        return((0,40))

    @staticmethod
    def housing():
        return 0

    @staticmethod
    def max_health():
        return 60

    @staticmethod
    def rep():
        return 's'

class House(Building):
    def __init__(self, obj):
        super().__init__(obj)

    def execute(self, cws):
        return {}

    @staticmethod
    def buildcost():
        return((30,0))

    @staticmethod
    def producecost():
        return((0,0))
    
    def produces():
        return None

    @staticmethod
    def housing():
        return 4

    @staticmethod
    def max_health():
        return 40

    @staticmethod
    def rep():
        return 'h'

    @staticmethod 
    def size():
        return (2,2)