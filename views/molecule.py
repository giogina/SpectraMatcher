import dearpygui.dearpygui as dpg
import math

radius = 5
phi = (1 + math.sqrt(5)) / 2
vertices = []
for s in [-1, 1]:
    for p in [-1, 1]:
        vertices.append((0, s*1, p*phi))
        vertices.append((s*1, p*phi, 0))
        vertices.append((p*phi, 0, s*1))


def distance(p, q):
    """Calculate the Euclidean distance between two 3D points."""
    return math.sqrt(sum((p_i - q_i) ** 2 for p_i, q_i in zip(p, q)))

faces = []
for u in vertices:
    for v in vertices:
        for w in vertices:
            if math.isclose(distance(v, w), 2) and math.isclose(distance(v, u), 2) and math.isclose(distance(u, w), 2):
                faces.append([u, v, w])   # figure out shading

with dpg.window(label="molecule", width=550, height=550):

    with dpg.drawlist(width=500, height=500):

        with dpg.draw_layer(tag="main pass", depth_clipping=True, perspective_divide=True, cull_mode=dpg.mvCullMode_Back):

            with dpg.draw_node(tag="icosahedron"):
                for face in faces:
                    dpg.draw_triangle(face[0], face[1], face[2], color=[0, 0, 0, 0], fill=[255, 255, 255*(1/3+face[0][0]/phi/3), 255*(1/3+face[0][0]/phi/3)])  #fill=[255*(2/3+face[0][0]/phi/3), 255*(2/3+face[0][0]/phi/3), 255*(2/3+face[0][0]/phi/3), 255]
