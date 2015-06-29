import enum


class GettableEnum(enum.Enum):
    @classmethod
    def get(cls, value, default=None):
        try:
            return cls(value)
        except ValueError:
            return default


class Direction(enum.Enum):
    up = (-1, 0)
    right = (0, 1)
    down = (1, 0)
    left = (0, -1)

    def __radd__(self, coord):
        return (coord[0] + self.value[0], coord[1] + self.value[1])

    def __rsub__(self, coord):
        return (coord[0] - self.value[0], coord[1] - self.value[1])
