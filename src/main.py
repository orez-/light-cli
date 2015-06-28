# -*- coding: utf8 -*-

import collections
import enum
import os

import bidict

import get_key
import los


ab = '\x1b[48;5;{}m'
af = '\x1b[38;5;{}m'
clear = '\x1b[0m'

darkest = 8
brightest = 23


class GettableEnum(enum.Enum):
    @classmethod
    def get(cls, value, default=None):
        try:
            return cls(value)
        except ValueError:
            return default


class TTYColor(enum.IntEnum):
    yellow = 3
    green = 2
    black = 16


class Direction(enum.Enum):
    up = (-1, 0)
    right = (0, 1)
    down = (1, 0)
    left = (0, -1)

    def __radd__(self, coord):
        return (coord[0] + self.value[0], coord[1] + self.value[1])

    def __rsub__(self, coord):
        return (coord[0] - self.value[0], coord[1] - self.value[1])


class Terrain(GettableEnum):
    wall = '#'
    floor = '.'
    fog = '~'
    glass = '▢'
    gravel = '…'

    @property
    def is_transparent(self):
        return self in {
            Terrain.floor,
            Terrain.glass,
            Terrain.gravel,
        }


class EntityType(GettableEnum):
    source_right = '◐'
    source_left = '◑'
    source_up = '◒'
    source_down = '◓'

    mirror_block_down_right = '◸'
    mirror_block_down_left = '◹'
    mirror_block_up_right = '◺'
    mirror_block_up_left = '◿'

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
            EntityType.source_up: {Direction.up: Direction.up},
            EntityType.source_right: {Direction.right: Direction.right},
            EntityType.source_down: {Direction.down: Direction.down},
            EntityType.source_left: {Direction.left: Direction.left},
            EntityType.player: TRANSPARENT,
        }.get(self, {})

    def can_pass(self, terrain):
        return terrain in {
            EntityType.player: {
                Terrain.floor,
                Terrain.fog,
                Terrain.gravel,
            },
            EntityType.mirror_block_up_left: {
                Terrain.floor,
                Terrain.fog,
            },
            EntityType.mirror_block_up_right: {
                Terrain.floor,
                Terrain.fog,
            },
            EntityType.mirror_block_down_left: {
                Terrain.floor,
                Terrain.fog,
            },
            EntityType.mirror_block_down_right: {
                Terrain.floor,
                Terrain.fog,
            },
        }.get(self, {})

    def can_push(self, other):
        return other in {
            EntityType.player: {
                EntityType.mirror_block_up_left,
                EntityType.mirror_block_up_right,
                EntityType.mirror_block_down_left,
                EntityType.mirror_block_down_right,
            },
        }.get(self, [])

    @property
    def luminescence(self):
        return 0
        # return {
        #     EntityType.player: 3,
        # }.get(self)


class FloorEntityType(GettableEnum):
    grate = '◍'
    exit = '⇲'

    @property
    def is_transparent(self):
        return self in {
            Terrain.floor,
            Terrain.glass,
            Terrain.gravel,
        }


class Level(object):
    def __init__(self):
        self.terrain = [[]]
        self.entities = {}
        self.floor_entities = {}
        self.light_map = [[]]

    @classmethod
    def from_string(cls, string):
        level = cls()
        lvl = [
            row.strip()
            for row in string.split('\n')
            if row.strip()
        ]
        level.terrain = [
            [
                Terrain.get(elem, Terrain.floor)
                for elem in row
            ] for row in lvl
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
        if entity.can_pass(level.terrain[r][c]):
            pushed_entity = level.entities.get((r, c))
            if pushed_entity:
                if not (entity.can_push(pushed_entity) and self._move((r, c), direction)):
                    return False

            del self.entities[coord]
            self.entities[coord + direction] = entity
            return True
        return False

    @property
    def all_grates_lit(self):
        return all(
            self.light_map[r][c] == brightest and
            not self.entities.get((r, c))
            for (r, c), entity in self.floor_entities.items()
            if entity == FloorEntityType.grate
        )

    @property
    def is_won(self):
        return (
            self.floor_entities.get(level.player) == FloorEntityType.exit and
            self.all_grates_lit
        )

    def calculate_light(self):
        self.light_map = [[darkest] * self.width for _ in range(self.height)]
        for e_coord, entity in self.entities.items():
            # Source blocks emit light in a direction
            if entity.is_source:
                r, c = e_coord
                direction = entity.direction
                while self.terrain[r][c].is_transparent:
                    next_entity = self.entities.get((r, c))
                    if next_entity:
                        direction = next_entity.light_direction.get(direction)
                        if not direction:
                            break
                    self.light_map[r][c] = 23
                    r, c = (r, c) + direction

            # Natural omni-directional glowing
            if entity.luminescence:
                q = collections.deque([(e_coord, entity.luminescence)])
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

    def tile_color(self, r, c):
        floor_entity = self.floor_entities.get((r, c))
        light = self.light_map[r][c]
        entity = self.entities.get((r, c))
        if floor_entity == FloorEntityType.grate and light == brightest and not entity:
            return TTYColor.yellow
        elif floor_entity == FloorEntityType.exit and self.all_grates_lit:
            return TTYColor.green
        return TTYColor.black


def _display_tile(brightness, char, color):
    return ''.join([
        af.format(color),
        ab.format(sorted([darkest, brightness, brightest])[1] + 232),
        str(char),
        ab.format(0),
    ])


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def display(level):
    clear_screen()
    width = level.width
    height = level.height
    print('\n'.join(
        ''.join(
            _display_tile(
                level.light_map[r][c],
                level.tile_char(r, c),
                level.tile_color(r, c),
            )
            for c in range(width)
        ) for r in range(height)
    ))
    print(clear)


def main(level):
    display(level)

    key = None
    while key != u'\u0003':
        key = get_key.getch()
        direction = {
            'w': Direction.up,
            'a': Direction.left,
            's': Direction.down,
            'd': Direction.right,
        }.get(key)
        if direction:
            level.move_player(direction)

        if level.is_won:
            print("You win!")
            break

        display(level)


if __name__ == '__main__':
    level_map = """
        ################
        #……………………………………#
        #…............…#
        #….◸..▢▢▢.....…#
        #…....~~~.◹...…#
        #…....~~~.…...…#
        #….....0...◑..…#
        #…....◺◿......…#
        #….◒.....◍..⇲.…#
        #……………………………………#
        ################
    """

    level = Level.from_string(level_map)

    main(level)
