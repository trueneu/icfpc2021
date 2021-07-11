from drawing import Coords, Circle, Line, Polygon, Tags, Edge, Vertex, EntityTypes
import json

PROBLEMS_PATH = './problems'


class Problem:
    def __init__(self, json_contents):
        self.epsilon = json_contents['epsilon']
        self.hole = []
        for pt in json_contents['hole']:
            self.hole.append(Coords(pt[0], pt[1]))
        self.figure = {}
        self.figure['edges'] = json_contents['figure']['edges']
        self.figure['vertices'] = []
        for pt in json_contents['figure']['vertices']:
            self.figure['vertices'].append(Coords(pt[0], pt[1]))

    def draw_problem(self, canvas, entities, scale=1, addx=0, addy=0):
        scaling_function = lambda c: c * scale
        moving_function = lambda c: c + (addx, addy)
        scaled_hole = list(map(scaling_function, self.hole))
        scaled_hole = list(map(moving_function, scaled_hole))

        p = Polygon(canvas, scaled_hole, tag='hole')
        p.draw()
        entities.add_entity(p)

        scaled_vertices = list(map(scaling_function, self.figure['vertices']))
        scaled_vertices = list(map(moving_function, scaled_vertices))
        vertices_ids = []
        for vertex in scaled_vertices:
            v = Vertex(canvas, vertex, 3)
            v.draw()
            vertices_ids.append(v.id)
            entities.add_entity(v)

        for pt1, pt2 in self.figure['edges']:
            e = Edge(canvas,
                     scaled_vertices[pt1],
                     scaled_vertices[pt2],
                     vertices_ids[pt1],
                     vertices_ids[pt2],
                     epsilon=self.epsilon,
                     tag=Tags.FIGURE_EDGE)
            e.draw()
            entities.add_entity(e)

def save_solution(entities, num_problem, scale=1, addx=0, addy=0):
    SOLUTIONS_PATH = './solutions'
    filename = '{}.solution'.format(num_problem)
    filepath = '{}/{}'.format(SOLUTIONS_PATH, filename)
    vertices = []
    for v_id in entities.ids_by_type[EntityTypes.VERTEX]:
        v = entities.data[v_id]
        x, y = v.center.x, v.center.y
        x -= addx
        y -= addy
        x = round(x / scale)
        y = round(y / scale)
        vertices.append([int(x), int(y)])
    with open(filepath, 'w') as f:
        json.dump({'vertices': vertices}, f)


def read_problem_json(problem_number: int):
    with open('{}/{}.problem'.format(PROBLEMS_PATH, problem_number), mode='r') as f:
        contents = json.load(f)
    return contents
