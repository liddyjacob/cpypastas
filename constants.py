OUR_KINGDOM_ID = 0

WSIZE = 96
HWSIZE = 48

WANDER_DIST = 7

# For stationing archers and stuff
BORDER_DISTANCE = 11
BORDER_EDGE = 2

LOGFILE = open("log.txt", "a")

DIRECTIONS = {
    'UP': [0,-1],
    'LEFT': [-1, 0],
    'DOWN': [0, 1],
    'RIGHT': [1, 0],
    'UP_LEFT': [-1, -1],
    'UP_RIGHT': [1, -1],
    'DOWN_LEFT': [-1,1],
    'DOWN_RIGHT': [1,1]
}

BUILD_NAMES = {
    'TOWNHALL': 'w',
    'BARRACKS': 'b',
    'RANGE': 'r',
    'STABLE': 's',
    'HOUSE': 'h'
}

BUILD_NAMES = {
    'TOWNHALL': 200,
    'BARRACKS': 50,
    'RANGE': 70,
    'STABLE': 90,
    'HOUSE': 40
}

BUILD_STORAGE = {
    'TOWNHALL': 9,
    'BARRACKS': 0,
    'RANGE': 0,
    'STABLE': 0,
    'HOUSE': 4  
}

POSSIBLE_MOVES = [v for v in DIRECTIONS.values()]

QASTAR_LIMIT = 80