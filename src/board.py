import collections

from . import util
from .util import Direction

darkest = 8
brightest = 23


class FloorEntityType(util.GettableEnum):
    grate = '◍'
    exit = '⇲'
    torch = '¡'

    @property
    def luminescence(self):
        return {
            FloorEntityType.torch: 4,
        }.get(self)


class Terrain(util.GettableEnum):
    wall = '#'
    floor = '.'
    fog = '~'
    glass = '▢'
    gravel = '…'
    void = ' '

    @property
    def is_transparent(self):
        return self in {
            Terrain.floor,
            Terrain.glass,
            Terrain.gravel,
        }


class EntityType(util.GettableEnum):
    source_right = '◐'
    source_left = '◑'
    source_up = '◒'
    source_down = '◓'

    mirror_block_down_right = '◸'
    mirror_block_down_left = '◹'
    mirror_block_up_right = '◺'
    mirror_block_up_left = '◿'
    mirror_block_slash = '/'
    mirror_block_backslash = '\\'

    splitter_up = '△'
    splitter_right = '▷'
    splitter_down = '▽'
    splitter_left = '◁'

    player = '0'

    @property
    def is_source(self):
        return self in {
            EntityType.source_right,
            EntityType.source_left,
            EntityType.source_up,
            EntityType.source_down,
        }

    @property
    def direction(self):
        return {
            EntityType.source_right: Direction.right,
            EntityType.source_left: Direction.left,
            EntityType.source_up: Direction.up,
            EntityType.source_down: Direction.down,
        }.get(self, None)

    @property
    def light_direction(self):
        TRANSPARENT = {
            Direction.up: Direction.up,
            Direction.right: Direction.right,
            Direction.down: Direction.down,
            Direction.left: Direction.left,
        }
        return {
            EntityType.mirror_block_up_left: {
                Direction.down: Direction.left,
                Direction.right: Direction.up,
            },
            EntityType.mirror_block_up_right: {
                Direction.down: Direction.right,
                Direction.left: Direction.up,
            },
            EntityType.mirror_block_down_left: {
                Direction.up: Direction.left,
                Direction.right: Direction.down,
            },
            EntityType.mirror_block_down_right: {
                Direction.up: Direction.right,
                Direction.left: Direction.down,
            },
            EntityType.mirror_block_slash: {
                Direction.up: Direction.right,
                Direction.left: Direction.down,
                Direction.down: Direction.left,
                Direction.right: Direction.up,
            },
            EntityType.mirror_block_backslash: {
                Direction.down: Direction.right,
                Direction.left: Direction.up,
                Direction.up: Direction.left,
                Direction.right: Direction.down,
            },
            EntityType.source_up: {Direction.up: Direction.up},
            EntityType.source_right: {Direction.right: Direction.right},
            EntityType.source_down: {Direction.down: Direction.down},
            EntityType.source_left: {Direction.left: Direction.left},
            EntityType.splitter_up: {
                Direction.down: [Direction.left, Direction.right],
                Direction.left: Direction.up,
                Direction.right: Direction.up,
            },
            EntityType.splitter_right: {
                Direction.left: [Direction.up, Direction.down],
                Direction.up: Direction.right,
                Direction.down: Direction.right,
            },
            EntityType.splitter_down: {
                Direction.up: [Direction.left, Direction.right],
                Direction.left: Direction.down,
                Direction.right: Direction.down,
            },
            EntityType.splitter_left: {
                Direction.right: [Direction.up, Direction.down],
                Direction.up: Direction.left,
                Direction.down: Direction.left,
            },
            EntityType.player: TRANSPARENT,
        }.get(self, {})

    def can_pass(self, terrain):
        BLOCK_FLOORS = {
            Terrain.floor,
            Terrain.fog,
        }
        return terrain in {
            EntityType.player: {
                Terrain.floor,
                Terrain.fog,
                Terrain.gravel,
            },
            EntityType.mirror_block_up_left: BLOCK_FLOORS,
            EntityType.mirror_block_up_right: BLOCK_FLOORS,
            EntityType.mirror_block_down_left: BLOCK_FLOORS,
            EntityType.mirror_block_down_right: BLOCK_FLOORS,
            EntityType.mirror_block_slash: BLOCK_FLOORS,
            EntityType.mirror_block_backslash: BLOCK_FLOORS,
            EntityType.splitter_up: BLOCK_FLOORS,
            EntityType.splitter_right: BLOCK_FLOORS,
            EntityType.splitter_down: BLOCK_FLOORS,
            EntityType.splitter_left: BLOCK_FLOORS,
        }.get(self, {})

    def can_push(self, other):
        return other in {
            EntityType.player: {
                EntityType.mirror_block_up_left,
                EntityType.mirror_block_up_right,
                EntityType.mirror_block_down_left,
                EntityType.mirror_block_down_right,
                EntityType.mirror_block_slash,
                EntityType.mirror_block_backslash,
                EntityType.splitter_up,
                EntityType.splitter_right,
                EntityType.splitter_down,
                EntityType.splitter_left,
            },
        }.get(self, [])

    @property
    def luminescence(self):
        return {
            EntityType.player: 4,
        }.get(self)


class Level(object):
    def __init__(self):
        self.terrain = [[]]
        self.entities = {}
        self.floor_entities = {}
        self.light_map = [[]]

    @classmethod
    def from_string(cls, string):
        level = cls()
        lvl = string.split('\n')
        width = max(map(len, lvl))
        level.terrain = [
            [
                Terrain.get(elem, Terrain.floor)
                for elem in row
            ] + [Terrain.void] * (width - len(row))
            for row in lvl
        ]
        level.entities = {
            (r, c): EntityType(elem)
            for r, row in enumerate(lvl)
            for c, elem in enumerate(row)
            if EntityType.get(elem)
        }
        level.floor_entities = {
            (r, c): FloorEntityType(elem)
            for r, row in enumerate(lvl)
            for c, elem in enumerate(row)
            if FloorEntityType.get(elem)
        }
        level.player = next(c for c, e in level.entities.items() if e == EntityType.player)
        level.calculate_light()
        return level

    def move_player(self, direction):
        if self._move(self.player, direction):
            self.player += direction
            self.calculate_light()

    def _move(self, coord, direction):
        entity = self.entities[coord]

        r, c = coord + direction
        if entity.can_pass(self.terrain[r][c]):
            pushed_entity = self.entities.get((r, c))
            if pushed_entity:
                if not (entity.can_push(pushed_entity) and self._move((r, c), direction)):
                    return False

            del self.entities[coord]
            self.entities[coord + direction] = entity
            return True
        return False

    def is_lit(self, r, c):
        return self.light_map[r][c] >= brightest

    @property
    def all_grates_lit(self):
        return all(
            self.is_lit(r, c) and
            not self.entities.get((r, c))
            for (r, c), entity in self.floor_entities.items()
            if entity == FloorEntityType.grate
        )

    @property
    def is_won(self):
        return (
            self.floor_entities.get(self.player) == FloorEntityType.exit and
            self.all_grates_lit
        )

    def calculate_light(self):
        self.light_map = [
            [darkest if elem != Terrain.void else -8 for elem in row]
            for row in self.terrain
        ]
        # light_points prevents infinite loops
        light_points = set()
        for e_coord, entity in self.entities.items():
            # Source blocks emit light in a direction
            if entity.is_source:
                row, col = e_coord
                light_paths = [(row, col, entity.direction)]
                for r, c, direction in light_paths:
                    print(r, c, direction)
                    while self.terrain[r][c].is_transparent:
                        next_entity = self.entities.get((r, c))
                        if next_entity:
                            if (r, c, direction) in light_points:
                                break
                            light_points.add((r, c, direction))
                            direction = next_entity.light_direction.get(direction)
                            if not direction:
                                break
                            if not isinstance(direction, Direction):
                                light_paths.extend(
                                    (r, c, d) for (r, c), d in (
                                        ((r, c) + d, d) for d in direction[1:]
                                    )
                                )
                                direction = direction[0]
                        self.light_map[r][c] = 23
                        r, c = (r, c) + direction

            if entity.luminescence:
                self.luminesce(e_coord, entity.luminescence)

        for e_coord, entity in self.floor_entities.items():
            if entity.luminescence:
                self.luminesce(e_coord, entity.luminescence)


    def luminesce(self, coord, luminescence):
        # Natural omni-directional glowing
        q = collections.deque([(coord, luminescence)])
        seen = set()
        while q:
            (r1, c1), l1 = q.popleft()
            self.light_map[r1][c1] = max(self.light_map[r1][c1], darkest + l1 * 3)
            seen.add((r1, c1))

            # TODO: obey mirrors, LOS.
            q.extend(
                ((r1, c1) + d, l1 - 1)
                for d in Direction
                if (r1, c1) + d not in seen and
                l1 > 1 and
                self.terrain[r1][c1].is_transparent
            )

    @property
    def width(self):
        return len(self.terrain[0])

    @property
    def height(self):
        return len(self.terrain)

    def tile_char(self, r, c):
        entity = self.entities.get((r, c))
        if entity:
            return entity.value
        floor_entity = self.floor_entities.get((r, c))
        if floor_entity:
            return floor_entity.value
        return self.terrain[r][c].value
