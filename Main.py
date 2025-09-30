from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import re
import math
from math import cos, sin, sqrt
import os

# --- Parâmetros Globais ---
entities = []          # Lista com todas as entidades (trajectórias)
frame = 0
scale_factor = 1.0
window_width, window_height = 800, 600

# Avatar (entidade controlada pelo usuário)
avatar_position = [400.0, 300.0]   # Posição inicial do avatar
avatar_size = 15.0                 # Tamanho do avatar (quadrado azul)
avatar_speed = 10.0                # Velocidade de movimento

# Entidades (pessoas do dataset)
entity_size = 10.0

# Parâmetros de Processamento
PROXIMITY_THRESHOLD = 50.0   # Distância para ALERTA (Amarelo)
COLLISION_DISTANCE = 25.0    # Distância para COLISÃO (Vermelho/Círculo)
SAFE_DISTANCE = 15.0         # Distância mínima entre entidades
WORLD_CENTER = [0, 0]

# ---------------- Funções Auxiliares ----------------
def load_data(filepath):
    """Carrega as trajetórias do Cultural Dataset."""
    global scale_factor, entities
    entities = []
    try:
        with open(filepath, 'r') as file:
            lines = file.readlines()
            
            # Primeiro valor: scale factor
            match = re.search(r'\[(\d+)\]', lines[0])
            if match:
                scale_factor = float(match.group(1))
            else:
                raise ValueError("Scale factor não encontrado na primeira linha.")
            
            # Demais linhas: entidades
            for line in lines[1:]:
                parts = line.split('\t')
                if len(parts) > 1:
                    entity_data = re.findall(r'\((\d+),(\d+),(\d+)\)', parts[1])
                    if entity_data:
                        entities.append([(int(x), int(y), int(f)) for x, y, f in entity_data])
            
            if len(entities) < 6:
                print(f"[Atenção] Apenas {len(entities)} entidades carregadas (mínimo = 6).")
                
    except FileNotFoundError:
        print(f"[ERRO] Arquivo '{filepath}' não encontrado.")
        os._exit(1)
    except Exception as e:
        print(f"[ERRO] {e}")
        os._exit(1)


def draw_square(x, y, size):
    half_size = size / 2
    glBegin(GL_QUADS)
    glVertex2f(x - half_size, y - half_size)
    glVertex2f(x + half_size, y - half_size)
    glVertex2f(x + half_size, y + half_size)
    glVertex2f(x - half_size, y + half_size)
    glEnd()


def draw_circle(x, y, radius, segments=64):
    glBegin(GL_POLYGON)
    for i in range(segments):
        angle = i * 2 * math.pi / segments
        glVertex2f(x + radius * cos(angle), y + radius * sin(angle))
    glEnd()


def world_to_screen(x_world, y_world, scale):
    """Transforma coordenadas do dataset para tela."""
    x_screen = (x_world / scale) * 3 + (window_width / 2)
    y_screen = (y_world / scale) * 3 + (window_height / 2)
    return x_screen, y_screen


def avoid_collision(current_x, current_y, neighbors):
    """Calcula desvio para evitar vizinhos próximos."""
    force_x, force_y = 0.0, 0.0
    for nx, ny in neighbors:
        distance = sqrt((current_x - nx) ** 2 + (current_y - ny) ** 2)
        if 0.0 < distance < SAFE_DISTANCE:
            dx = current_x - nx
            dy = current_y - ny
            repulsion_strength = (SAFE_DISTANCE - distance) / SAFE_DISTANCE
            force_x += repulsion_strength * dx / distance
            force_y += repulsion_strength * dy / distance
    
    # Limita o deslocamento
    max_corr = 0.5
    force_x = max(-max_corr, min(max_corr, force_x))
    force_y = max(-max_corr, min(max_corr, force_y))
    return force_x, force_y

# ---------------- Renderização ----------------
def draw_entities():
    global frame
    glClear(GL_COLOR_BUFFER_BIT)

    current_positions = []

    # Adiciona o avatar como primeira posição
    current_positions.append(tuple(avatar_position))

    # Calcula posição das entidades para o frame atual
    positions_with_collision = []
    for entity in entities:
        if frame < len(entity):
            x_world, y_world, _ = entity[frame]
            x_screen, y_screen = world_to_screen(x_world, y_world, scale_factor)
            positions_with_collision.append([x_screen, y_screen])
            current_positions.append((x_screen, y_screen))

    # Desenha Avatar
    glColor3f(0.0, 0.0, 1.0)
    draw_square(avatar_position[0], avatar_position[1], avatar_size)

    # Desenha Entidades
    for i, pos in enumerate(positions_with_collision):
        x_screen, y_screen = pos

        # Evitação de colisão (aplica deslocamento)
        neighbors = [p for j, p in enumerate(current_positions) if j != i + 1]
        fx, fy = avoid_collision(x_screen, y_screen, neighbors)
        x_screen += fx
        y_screen += fy

        # Distância até o avatar
        dx = x_screen - avatar_position[0]
        dy = y_screen - avatar_position[1]
        distance = sqrt(dx*dx + dy*dy)

        if distance <= COLLISION_DISTANCE:
            glColor3f(1.0, 0.0, 0.0)
            draw_circle(x_screen, y_screen, entity_size)
        elif distance <= PROXIMITY_THRESHOLD:
            glColor3f(1.0, 1.0, 0.0)
            draw_square(x_screen, y_screen, entity_size)
        else:
            glColor3f(0.0, 1.0, 0.0)
            draw_square(x_screen, y_screen, entity_size)

    glutSwapBuffers()

# ---------------- Atualização e Interação ----------------
def update(value):
    global frame
    frame += 1
    max_frames = max((len(e) for e in entities), default=0)
    if frame >= max_frames:
        frame = 0
    glutPostRedisplay()
    glutTimerFunc(100, update, 0)


def keyboard(key, x, y):
    global avatar_position
    if key == b'\x1b':  # ESC
        os._exit(0)
    elif key == b'w':
        avatar_position[1] += avatar_speed
    elif key == b's':
        avatar_position[1] -= avatar_speed
    elif key == b'a':
        avatar_position[0] -= avatar_speed
    elif key == b'd':
        avatar_position[0] += avatar_speed

    avatar_position[0] = max(avatar_size/2, min(window_width - avatar_size/2, avatar_position[0]))
    avatar_position[1] = max(avatar_size/2, min(window_height - avatar_size/2, avatar_position[1]))

    glutPostRedisplay()


def init():
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)


def main():
    load_data('Paths_D.txt')
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(window_width, window_height)
    glutCreateWindow(b"T1 CG - Evitacao de Colisao")
    init()
    glutDisplayFunc(draw_entities)
    glutKeyboardFunc(keyboard)
    glutTimerFunc(100, update, 0)
    glutMainLoop()


if __name__ == "__main__":
    avatar_position = [float(avatar_position[0]), float(avatar_position[1])]
    main()
