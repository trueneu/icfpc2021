import enum
import math
import tkinter
from typing import List, Tuple
from abc import ABC, abstractmethod
from itertools import chain


class Coords:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __mul__(self, scale: int):
        return Coords(self.x * scale, self.y * scale)

    def __add__(self, other: Tuple[int]):
        return Coords(self.x + other[0], self.y + other[1])

    def __repr__(self):
        return "X: {}, Y: {}".format(self.x, self.y)


class Delta:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Tags(enum.Enum):
    HOLE = 'hole'
    FIGURE_VERTEX = 'figure_vertex'
    FIGURE_EDGE = 'figure_edge'


def distance(p1: Coords, p2: Coords):
    return math.sqrt(
        (p1.x - p2.x) ** 2
        +
        (p1.y - p2.y) ** 2
    )


class EntityTypes(enum.Enum):
    OVAL = 1
    CIRCLE = 2
    LINE = 3
    VERTEX = 4
    EDGE = 5
    POLYGON = 6


class CanvasShape(ABC):
    def __init__(self, canvas: tkinter.Canvas):
        self.id = None
        self.canvas = canvas
        self.type = None

    @abstractmethod
    def coords_inside(self, c: Coords):
        pass

    @abstractmethod
    def draw(self):
        pass

    @abstractmethod
    def move(self, coords: Coords):
        pass

    @abstractmethod
    def snapshot_save(self):
        pass

    @abstractmethod
    def snapshot_load(self, snapshot):
        pass

    def change_fill(self, color):
        self.fill = color
        self.canvas.itemconfig(self.id, fill=color)

    def change_outline(self, color):
        self.outline = color
        self.canvas.itemconfig(self.id, outline=color)

    def change_width(self, color):
        self.width = color
        self.canvas.itemconfig(self.id, width=color)


class Circle(CanvasShape):
    def __init__(self, canvas: tkinter.Canvas, center: Coords, radius: int, outline='black', fill='', width=1,
                 tag='circle'):
        super().__init__(canvas)
        self.center = center
        self.radius = radius
        self.type = EntityTypes.CIRCLE
        self.canvas = canvas
        self.outline = outline
        self.fill = fill
        self.id = None
        self.width = width
        self.tag = tag
        self.top_left_coords, self.bottom_right_coords = Circle.TLBR_from_center_radius(self.center, self.radius)

    @staticmethod
    def TLBR_from_center_radius(center: Coords, radius: int):
        return (Coords(center.x - radius, center.y - radius),
                Coords(center.x + radius, center.y + radius))

    def coords_inside(self, c: Coords):
        return distance(c, self.center) <= self.radius

    def draw(self):
        self.id = self.canvas.create_oval(
            self.top_left_coords.x, self.top_left_coords.y,
            self.bottom_right_coords.x, self.bottom_right_coords.y,
            tag=self.tag,
            width=self.width,
            fill=self.fill
        )

    def move(self, new_center: Coords):
        delta = Delta(new_center.x - self.center.x, new_center.y - self.center.y)

        self.canvas.move(self.id, delta.x, delta.y)
        self.center.x += delta.x
        self.center.y += delta.y
        self.top_left_coords, self.bottom_right_coords = Circle.TLBR_from_center_radius(self.center, self.radius)

    def snapshot_save(self):
        return [
            self.center,
            self.radius
        ]

    def snapshot_load(self, snapshot):
        old_center, old_radius = self.center, self.radius
        self.center, self.radius = snapshot

        delta = Delta(self.center.x - old_center.x, self.center.y - old_center.y)
        self.canvas.move(self.id, delta.x, delta.y)
        self.top_left_coords, self.bottom_right_coords = Circle.TLBR_from_center_radius(self.center, self.radius)


class Vertex(Circle):
    def __init__(self, canvas: tkinter.Canvas, center: Coords, radius: int, outline='black', fill='', width=1,
                 tag=Tags.FIGURE_VERTEX, vertices_ids=None, edges_ids=None):
        super().__init__(canvas, center, radius, outline, fill, width, tag)
        self.type = EntityTypes.VERTEX
        if not vertices_ids:
            self.vertices_ids = []
        else:
            self.vertices_ids = vertices_ids
        if not edges_ids:
            self.edges_ids = []
        else:
            self.edges_ids = edges_ids

    def move(self, new_center: Coords):
        super().move(new_center)

    def add_vertex_id(self, vertex_id):
        self.vertices_ids.append(vertex_id)

    def add_edge_id(self, edge_id):
        self.edges_ids.append(edge_id)


class Line(CanvasShape):
    def __init__(self, canvas: tkinter.Canvas, p1: Coords, p2: Coords, outline='black', width=1,
                 tag='line'):
        super().__init__(canvas)
        self.type = EntityTypes.LINE
        self.canvas = canvas
        self.outline = outline
        self.id = None
        self.width = width
        self.tag = tag
        self.p1, self.p2 = p1, p2

    def coords_inside(self, c: Coords):
        # fixme
        return False
        # return distance(c, self.center) <= self.radius

    def draw(self):
        self.id = self.canvas.create_line(
            self.p1.x, self.p1.y,
            self.p2.x, self.p2.y,
            tag=self.tag,
            width=self.width
        )

    def move(self, new_p2: Coords):
        self.canvas.coords(self.id, self.p1.x, self.p1.y, new_p2.x, new_p2.y)
        self.p2 = new_p2

    def change_outline(self, color):
        pass

    def snapshot_save(self):
        pass

    def snapshot_load(self, snapshot):
        pass


class Edge(Line):
    def __init__(self, canvas: tkinter.Canvas, p1: Coords, p2: Coords, v1_id: Vertex, v2_id: Vertex, epsilon: int, outline='black',
                 width=3, tag=Tags.FIGURE_EDGE):
        super().__init__(canvas, p1, p2, outline, width, tag)
        self.original_length = distance(p1, p2)
        self.v1_id = v1_id
        self.v2_id = v2_id
        self.type = EntityTypes.EDGE
        self.epsilon = epsilon

    def move(self, new_p: Coords):
        d1 = distance(self.p1, new_p)
        d2 = distance(self.p2, new_p)
        if d1 < d2:
            self.canvas.coords(self.id, new_p.x, new_p.y, self.p2.x, self.p2.y)
            self.p1 = new_p
        else:
            self.canvas.coords(self.id, self.p1.x, self.p1.y, new_p.x, new_p.y)
            self.p2 = new_p
        self.change_fill(self.calc_color_based_on_length())

    def parallel_move(self, dx, dy):
        self.canvas.coords(self.id, self.p1.x + dx, self.p1.y + dy, self.p2.x + dx, self.p2.y + dy)
        self.p1 = Coords(self.p1.x + dx, self.p1.y + dy)
        self.p2 = Coords(self.p2.x + dx, self.p2.y + dy)
        self.change_fill(self.calc_color_based_on_length())

    def length_if_moved(self, new_p: Coords):
        d1 = distance(self.p1, new_p)
        d2 = distance(self.p2, new_p)
        if d1 < d2:
            return distance(new_p, self.p2)
        else:
            return distance(self.p1, new_p)

    def snapshot_save(self):
        return [
            self.p1, self.p2, self.epsilon
        ]

    def snapshot_load(self, snapshot):
        self.p1, self.p2, self.epsilon = snapshot
        self.canvas.coords(self.id, self.p1.x, self.p1.y, self.p2.x, self.p2.y)

    def calc_color_based_on_length(self):
        original_length = self.original_length
        new_length = distance(self.p1, self.p2)
        color_range = 128
        color_offset = 128
        margin = 2

        if abs(new_length / original_length - 1) > (self.epsilon / 1_000_000):
            if new_length > original_length:
                red_amount = int(color_offset + \
                             min((new_length / original_length - 1), (margin - 1)) * (color_range - 1))
                color = '#{:02x}0000'.format(red_amount)
                return color
            else:
                blue_amount = int(color_offset + \
                             min((original_length / new_length - 1), (margin - 1)) * (color_range - 1))
                color = '#0000{:02x}'.format(blue_amount)
                return color
        else:
            return 'black'



class Polygon(CanvasShape):
    def __init__(self, canvas: tkinter.Canvas, pts: List[Coords], outline='black', width=1,
                 tag='polygon', fill=''):
        super().__init__(canvas)
        self.type = EntityTypes.POLYGON
        self.canvas = canvas
        self.outline = outline
        self.id = None
        self.width = width
        self.tag = tag
        self.pts = pts
        self.fill = fill

    def coords_inside(self, c: Coords):
        # fixme
        return False

    def draw(self):
        flat_points = []
        for pt in self.pts:
            flat_points.append(pt.x)
            flat_points.append(pt.y)

        self.id = self.canvas.create_polygon(
            flat_points,
            fill=self.fill,
            tag=self.tag,
            width=self.width,
            outline=self.outline,
        )

    def move(self, new_p2: Coords):
        pass

    def change_outline(self, color):
        pass

    def snapshot_save(self):
        return [self.pts]

    def snapshot_load(self, snapshot):
        pts = snapshot[0]
        getx = lambda e: e.x
        gety = lambda e: e.y
        pts_flat = list(chain.from_iterable((getx(e), gety(e)) for e in pts))
        self.canvas.coords(self.id, *pts_flat)
        self.pts = pts

