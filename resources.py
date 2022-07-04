
# Resources can be real or theoretical, 
# depending on if they are assumed from 
# reflection or observed.
class MapObj:
    def __init__(self, theoretical):
        self.theoretical = theoretical
        self.travel_ban = False
        self.alley = False
        self.team = -1

class Resource(MapObj):
    def __init__(self, obj, theoretical = False):
        super().__init__(theoretical)
        self.obj_raw = obj
        self.island_ids = set()
        self.travel_ban = True
        self.reserved = False

        if not self.theoretical:
            self.id = obj['id']
            self.x = obj['x']
            self.y = obj['y']
            self.hp = obj['hp']
        else:
            self.id = -1

class Tree(Resource):
    def __init__(self, obj, theoretical = False):
        super().__init__(obj, theoretical)

class Gold(Resource):
    def __init__(self, obj, theoretical = False):
        super().__init__(obj, theoretical)

class Unknown(MapObj):
    def __init__(self):
        super().__init__(True)
        self.id = -2

class Unoccupied(MapObj):
    def __init__(self, theoretical = False):
        super().__init__(theoretical)
        self.id = -3