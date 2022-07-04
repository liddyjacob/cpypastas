from ai.cpypastas.buildings import Townhall, Barracks, Range, Stable, House

class Move:
    def __init__(self, direction):
        self.direction = direction

    def apply(self, unit):
        return {"id": unit.id, "command":"m", "arg":[self.direction[0], self.direction[1]]}

    def __str__(self):
        return f"move: {self.direction}"

class Build:
    def __init__(self, type, location):
        self.location = location
        self.type = type
        self.rep = type.rep()

    def apply(self, unit):
        return {"id": unit.id, "command":self.rep, "arg":[self.location[0], self.location[1]]}

    def __str__(self):
        return f"build: {self.rep} - {self.direction}"    

class Attack:
    def __init__(self, target):
        self.target = target
        self.target_id = target.id

    def apply(self, unit):
        return {"id": unit.id, "command":'k', "arg":self.target_id}

    def __str__(self):
        return f"attacking: {self.target} - {self.target_id}"            

class Repair:
    def __init__(self, bld):
        self.bld_id = bld.id
        self.bld = bld
    
    def apply(self, unit):
        return {"id": unit.id, "command":'f', "arg":self.bld_id}

    def __str__(self):
        return f"repair: {self.bld_id} at {self.bld.x}, {self.bld.y}"    

class Produce:
    def __init__(self):
        pass
    
    def apply(self, bld):
        return {"id": bld.id, "command":'p', "arg": None}

    def __str__(self):
        return f"Produced"    


class Upgrade:
    def __init__(self):
        pass
    
    def apply(self, bld):
        return {"id": bld.id, "command":'u', "arg": None}

    def __str__(self):
        return f"Produced"   

class DoNothing:
    def __init__(self):
        pass
    
    def apply(self, bld):
        return {}

    def __str__(self):
        return f"Did Nothing."   
 