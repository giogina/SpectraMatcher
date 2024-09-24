import dearpygui.dearpygui as dpg
import math
import numpy as np


def calculate_normal(A, B, C):
    AB = B - A
    AC = C - A
    normal = np.cross(AB, AC)
    normal_normalized = normal / np.linalg.norm(normal)
    return normal_normalized


def calculate_light_intensity(normal, light_direction):
    light_intensity = np.dot(normal, light_direction)
    # Clamp the value between 0 and 1 for shading purposes
    light_intensity = max(0, light_intensity)
    return light_intensity


def distance(p, q):
    """Calculate the Euclidean distance between two 3D points."""
    return math.sqrt(sum((p_i - q_i) ** 2 for p_i, q_i in zip(p, q)))


def prepare_icosahedron():
    radius = 5
    phi = (1 + math.sqrt(5)) / 2
    vertices = []
    light_direction = np.array([1, 1, 1])
    light_direction = light_direction / np.linalg.norm(light_direction)

    for s in [-1, 1]:
        for p in [-1, 1]:
            vertices.append((0, s * 1, p * phi))
            vertices.append((s * 1, p * phi, 0))
            vertices.append((p * phi, 0, s * 1))

    faces = []
    for u in vertices:
        for v in vertices:
            for w in vertices:
                if math.isclose(distance(v, w), 2) and math.isclose(distance(v, u), 2) and math.isclose(distance(u, w), 2):

                    normal = calculate_normal(np.array(u), np.array(v), np.array(w))
                    light_intensity = calculate_light_intensity(normal, light_direction)
                    faces.append([u, v, w, normal, light_intensity])
    return faces


with dpg.window(label="molecule", width=550, height=550):
    with dpg.drawlist(width=500, height=500):

        with dpg.draw_layer(tag="main pass", depth_clipping=True, perspective_divide=True, cull_mode=dpg.mvCullMode_Back):

            with dpg.draw_node(tag="icosahedron"):
                faces = prepare_icosahedron()
                for face in faces:
                    dpg.draw_triangle(face[0], face[1], face[2], color=[0, 0, 0, 0], fill=[255, 255, 255*face[4]])
