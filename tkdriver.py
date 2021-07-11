import os.path
from collections import defaultdict
import tkinter
import enum
from drawing import Coords, Delta, CanvasShape, Circle, Line, Polygon, EntityTypes, Vertex, Edge, Tags
import problems
import pickle
from typing import Dict
import copy


class Labels(enum.IntEnum):
    PROBLEM_NAME = 1
    STATE_NAME = 2
    COORDS = 3


class Modifiers(enum.IntEnum):
    SHIFT = 1
    CAPSLOCK = 2
    CONTROL = 4
    LEFTALT = 8
    NUMLOCK = 16
    RIGHTALT = 0x0080
    MOUSEBTN1 = 0x0100
    MOUSEBTN2 = 0x0200
    MOUSEBTN3 = 0x0400


class Modes(enum.Enum):
    DEFAULT = 0
    CREATE_CIRCLE = 1
    CREATE_LINE = 2
    CREATE_POLYGON = 3


class States(enum.Enum):
    DEFAULT = 0
    CREATING_CIRCLE = 1
    CREATING_LINE = 2


Mode = Modes.DEFAULT
State = States.DEFAULT
Moving_Entity_Id = None
Making_Move = False
Epsilon = 0

class Entities:
    def __init__(self):
        self.data : Dict[CanvasShape] = {}
        # fixme: is it really needed?
        self.vertex_to_edge = defaultdict(set)
        self.last_added = None
        self.ids_by_type = defaultdict(list)
        self.vertices_id_to_order = {}
        pass

    def add_entity(self, entity: CanvasShape):
        self.data[entity.id] = entity
        self.last_added = entity.id
        if entity.type == EntityTypes.EDGE:
            self.vertex_to_edge[entity.v1_id].add(entity.id)
            self.vertex_to_edge[entity.v2_id].add(entity.id)

            v1 = self.data[entity.v1_id]
            v2 = self.data[entity.v2_id]

            v1.add_edge_id(entity.id)
            v2.add_edge_id(entity.id)

            v1.add_vertex_id(entity.v2_id)
            v2.add_vertex_id(entity.v1_id)
        elif entity.type == EntityTypes.VERTEX:
            self.vertices_id_to_order[entity.id] = len(self.ids_by_type[EntityTypes.VERTEX])

        self.ids_by_type[entity.type].append(entity.id)



class UndoHistory:
    def __init__(self, entities: Entities):
        self.entities = entities
        self.undodata = []

    def make_snapshot(self):
        snapshot = []
        for e_id in self.entities.data:
            e = self.entities.data[e_id]
            entity_snapshot = copy.deepcopy(e.snapshot_save())
            snapshot.append({'id': e_id, 'snapshot': entity_snapshot})
        self.undodata.append(snapshot)

    # 01: {'id': 2, 'snapshot': [X: 404, Y: 479, 3]}
    def rollback(self):
        if self.undodata:
            snapshot = self.undodata.pop()
            for snapshot_element in snapshot:
                e_id, entity_snapshot = snapshot_element['id'], snapshot_element['snapshot']
                e = self.entities.data[e_id]
                e.snapshot_load(entity_snapshot)


def save_state(entities, filename):
    global Epsilon

    STATES_PATH = './states'
    filepath = '{}/{}'.format(STATES_PATH, filename)
    savedata = {EntityTypes.POLYGON: [],
                EntityTypes.VERTEX: [],
                EntityTypes.EDGE: [],
                'epsilon': Epsilon}

    for p_id in entities.ids_by_type[EntityTypes.POLYGON]:
        p = entities.data[p_id]
        savedata[EntityTypes.POLYGON].append({
            'pts': p.pts,
            'outline': p.outline,
            'width': p.width,
            'tag': p.tag,
            'fill': p.fill
        })

    edges = set()
    for v_id in entities.ids_by_type[EntityTypes.VERTEX]:
        v = entities.data[v_id]
        savedata[EntityTypes.VERTEX].append({
            'center': v.center,
            'radius': v.radius,
            'outline': v.outline,
            'width': v.width,
            'tag': v.tag,
            'fill': v.fill
        })
        for adjacent_v_id in v.vertices_ids:
            v1_order = entities.vertices_id_to_order[v.id]
            v2_order = entities.vertices_id_to_order[adjacent_v_id]
            edges.add(tuple(sorted([v1_order, v2_order])))

    savedata[EntityTypes.EDGE].extend(edges)

    with open(filepath, 'wb') as f:
        pickle.dump(savedata, f)


def remove_state(filename):
    STATES_PATH = './states'
    filepath = "{}/{}".format(STATES_PATH, filename)
    if os.path.exists(filepath):
        os.remove(filepath)

# todo: color coding: vertex doesn't fit the hole
# todo: rotation
# todo: zoom?

# 1st prio
# todo: turn off hard epsilon check
# todo: color coding: edge too short / too long
# todo: solution export, solution save button
# todo: bonuses appearance
# todo: bonuses graph



def load_state(canvas, entities, filename):
    global Epsilon

    STATES_PATH = './states'
    filepath = '{}/{}'.format(STATES_PATH, filename)
    if not os.path.isfile(filepath):
        return False

    with open(filepath, 'rb') as f:
        loaddata = pickle.load(f)

    for p_data in loaddata[EntityTypes.POLYGON]:
        # p = Polygon(canvas, p_data['pts'], p_data['outline'], p_data['width'],
        #             p_data['tag'], p_data['fill'])
        p = Polygon(canvas, **p_data)
        p.draw()
        entities.add_entity(p)

    vertices_ids = []
    for v_data in loaddata[EntityTypes.VERTEX]:
        v = Vertex(canvas, **v_data)
        v.draw()
        entities.add_entity(v)
        vertices_ids.append(v.id)

    for pt1, pt2 in loaddata[EntityTypes.EDGE]:
        e = Edge(canvas,
                 entities.data[vertices_ids[pt1]].center,
                 entities.data[vertices_ids[pt2]].center,
                 vertices_ids[pt1],
                 vertices_ids[pt2],
                 tag=Tags.FIGURE_EDGE)
        e.draw()
        entities.add_entity(e)

    Epsilon = loaddata['epsilon']

    return True


def make_mouse_button1_press_handler(entities: Entities, canvas: tkinter.Canvas):
    def handler(event):
        global Mode, State

        if Mode == Modes.CREATE_CIRCLE:
            c = Circle(canvas, Coords(event.x, event.y), 20, width=3)
            c.draw()
            entities.add_entity(c)

        if Mode == Modes.CREATE_LINE:
            l = Line(canvas, Coords(event.x, event.y), Coords(event.x, event.y))
            l.draw()
            entities.add_entity(l)
            State = States.CREATING_LINE

        if Mode == Modes.CREATE_POLYGON:
            p = Polygon(canvas, [Coords(event.x, event.y),
                                 Coords(event.x - 10, event.y - 20),
                                 Coords(event.x + 30, event.y - 20),
                                 Coords(event.x + 10, event.y + 50),
                                 Coords(event.x - 20, event.y + 40)])
            p.draw()
            entities.add_entity(p)

    return handler


def make_mouse_button2_press_handler(entities: Entities):
    def handler(event):
        p = Coords(event.x, event.y)
        for entity_id, entity in entities.data.items():
            if entity.coords_inside(p):
                entity.change_fill('red')

    return handler


def delete_object(event):
    event.widget.children['!canvas'].delete('point')


def make_mouse_motion_handler(entities: Entities, canvas: tkinter.Canvas, coords_label: tkinter.Label, undo_history: UndoHistory):
    prev_mouse_pos = None
    def handler(event):
        global State, Moving_Entity_Id, Epsilon, Making_Move
        nonlocal prev_mouse_pos

        p = Coords(event.x, event.y)
        mousebtn1 = False
        if event.state | Modifiers.MOUSEBTN1 == event.state:
            mousebtn1 = True

        shift = False
        if event.state | Modifiers.SHIFT == event.state:
            shift = True

        if State == States.DEFAULT:
            if mousebtn1:
                if shift:
                    if prev_mouse_pos:
                        if not Making_Move:
                            undo_history.make_snapshot()
                        dx = p.x - prev_mouse_pos.x
                        dy = p.y - prev_mouse_pos.y
                        for vertex_id in entities.ids_by_type[EntityTypes.VERTEX]:
                            entity = entities.data[vertex_id]
                            entity.move(Coords(entity.center.x + dx, entity.center.y + dy))
                        for edge_id in entities.ids_by_type[EntityTypes.EDGE]:
                            entity = entities.data[edge_id]
                            entity.parallel_move(dx, dy)
                        Making_Move = True

                else:
                    if not Moving_Entity_Id:
                        for entity_id, entity in entities.data.items():
                            if entity.coords_inside(p):
                                Moving_Entity_Id = entity_id

                    if Moving_Entity_Id:
                        if not Making_Move:
                            undo_history.make_snapshot()

                        entity = entities.data[Moving_Entity_Id]
                        if entity.type == EntityTypes.VERTEX:
                            move_is_legal = True

                            for edge_id in entity.edges_ids:
                                edge = entities.data[edge_id]
                                original_length = edge.original_length
                                new_length = edge.length_if_moved(p)
                                if abs(new_length / original_length - 1) > (Epsilon / 1_000_000):
                                    move_is_legal = False
                            if move_is_legal:
                                for edge_id in entity.edges_ids:
                                    edge = entities.data[edge_id]
                                    edge.move(p)
                                entity.move(p)
                        else:
                            entity.move(p)
                        Making_Move = True

            for entity_id, entity in entities.data.items():
                if entity.coords_inside(p):
                    entity.change_outline('red')
                else:
                    entity.change_outline('black')

        elif State == States.CREATING_LINE:
            if mousebtn1:
                line_id = entities.last_added
                line = entities.data[line_id]
                line.move(p)
            else:
                State = States.DEFAULT

        refresh_coords_label(coords_label, p)
        prev_mouse_pos = p
    return handler


def make_button1_release_handler(undo_history: UndoHistory):
    def handler(event):
        global Moving_Entity_Id, Making_Move
        Moving_Entity_Id = None
        if Making_Move:
            Making_Move = False

    return handler


def make_quitter(rootwidget, entities, filename=None):
    def handler(event):
        if filename:
            save_state(entities, filename)
        rootwidget.destroy()

    return handler


def make_change_mode_handler(target_mode):
    def handler(_):
        global Mode
        Mode = target_mode

    return handler


def create_labels(canvas: tkinter.Canvas):
    font = ("DejaVu Sans Mono", 8)
    y = 0
    dy = 25
    problem_label = tkinter.Label(canvas, text='problem: ', font=font)
    problem_label.place(x=0, y=y)

    y += dy
    state_label = tkinter.Label(canvas, text='statefile: ', font=font)
    state_label.place(x=0, y=y)

    y += dy
    coords_label = tkinter.Label(canvas, text='coords: ', font=font)
    coords_label.place(x=0, y=y)

    return {Labels.PROBLEM_NAME: problem_label,
            Labels.STATE_NAME: state_label,
            Labels.COORDS: coords_label}


def refresh_problem_label(label: tkinter.Label, num_problem):
    label.configure(text='problem: {}'.format(num_problem))


def refresh_state_label(label: tkinter.Label, filename):
    label.configure(text='statefile: {}'.format(filename))


def refresh_coords_label(label: tkinter.Label, coords):
    label.configure(text='coords: {}'.format(coords))


def run_tk():
    global Epsilon

    root = tkinter.Tk()
    canvas = tkinter.Canvas(root, bg="white", height=2000, width=3000)

    entities = Entities()
    undo_history = UndoHistory(entities)

    num_problem = 1

    # p1 = Coords(10, 10)
    # p2 = Coords(20, 20)


    labels = create_labels(canvas)
    statefile = '{}.state'.format(num_problem)
    if not load_state(canvas, entities, statefile):
        p = problems.Problem(problems.read_problem_json(1))
        p.draw_problem(canvas, entities, scale=15, addx=100)
        Epsilon = p.epsilon

    undo_history.make_snapshot()

    # v1 = Vertex(canvas, Coords(100, 100), 30)
    # v2 = Vertex(canvas, Coords(300, 300), 30)
    # v1.draw()
    # v2.draw()
    # e = Edge(canvas, Coords(100, 100), Coords(300, 300),
    #          v1.id, v2.id)
    # e.draw()
    # for entity in (v1, v2, e):
    #     entities.add_entity(entity)



    refresh_problem_label(labels[Labels.PROBLEM_NAME], num_problem)
    refresh_state_label(labels[Labels.STATE_NAME], statefile)

    canvas.bind('<Button-1>', make_mouse_button1_press_handler(entities, canvas))
    canvas.bind('<Button-3>', make_mouse_button2_press_handler(entities))
    canvas.bind('<Motion>', make_mouse_motion_handler(entities, canvas, labels[Labels.COORDS], undo_history))
    canvas.bind('<ButtonRelease-1>', make_button1_release_handler(undo_history))
    canvas.bind_all('<c>', make_change_mode_handler(Modes.CREATE_CIRCLE))
    canvas.bind_all('<l>', make_change_mode_handler(Modes.CREATE_LINE))
    canvas.bind_all('<p>', make_change_mode_handler(Modes.CREATE_POLYGON))
    canvas.bind_all('<d>', make_change_mode_handler(Modes.DEFAULT))
    canvas.bind_all('<x>', lambda _: remove_state(statefile))
    canvas.bind_all('<q>', make_quitter(root, entities))
    canvas.bind_all('<z>', lambda _: undo_history.rollback())

    canvas.bind_all('<Escape>', make_quitter(root, entities, statefile))

    canvas.pack()
    root.mainloop()
