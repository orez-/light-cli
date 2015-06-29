# -*- coding: utf8 -*-

import collections
import enum
import os

from . import board
from .board import brightest
from .board import darkest
from . import get_key
from . import los
from . import util


ab = '\x1b[48;5;{}m'
af = '\x1b[38;5;{}m'
clear = '\x1b[0m'


class TTYColor(enum.IntEnum):
    green = 2
    yellow = 3
    black = 16


def tile_color(level, r, c):
    floor_entity = level.floor_entities.get((r, c))
    entity = level.entities.get((r, c))
    if floor_entity == board.FloorEntityType.grate and level.is_lit(r, c) and not entity:
        return TTYColor.yellow
    elif floor_entity == board.FloorEntityType.exit and level.all_grates_lit:
        return TTYColor.green
    return TTYColor.black


def _display_tile(brightness, char, color):
    return ''.join([
        af.format(color),
        ab.format(sorted([0, brightness, brightest])[1] + 232),
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
                tile_color(level, r, c),
            )
            for c in range(width)
        ) for r in range(height)
    ))
    print(clear)


keymap = {
    'w': util.Direction.up,
    'a': util.Direction.left,
    's': util.Direction.down,
    'd': util.Direction.right,

    '\x1b[A': util.Direction.up,
    '\x1b[C': util.Direction.right,
    '\x1b[B': util.Direction.down,
    '\x1b[D': util.Direction.left,
}


def game_loop(level):
    display(level)

    key = None
    while key != u'\u0003':
        key = get_key.getch()

        direction = keymap.get(key)
        if direction:
            level.move_player(direction)

        if level.is_won:
            display(level)
            print("You win!")
            get_key.getch()
            return False

        display(level)
    return True


def main():
    level_set = 'alpha'
    with open('data/{}/_level_map'.format(level_set)) as f:
        level_map = [line.strip() for line in f]

    for level_name in level_map:
        with open('data/{}/{}.skb'.format(level_set, level_name), 'r') as f:
            level_map = f.read().rstrip()
        level = board.Level.from_string(level_map)

        if game_loop(level):
            return
