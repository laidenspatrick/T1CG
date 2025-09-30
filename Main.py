from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import re
import math
from math import cos, sin, sqrt
import os

# --- Parâmetros Globais ---
entities = []
frame = 0
scale_factor = 1.0
window_width, window_height = 800, 600
# Avatar (entidade controlada pelo usuário)
avatar_position = [400.0, 300.0]  # Posição inicial do avatar (float para cálculos)
avatar_size = 15.0 # Tamanho do avatar (quadrado azul)
avatar_speed = 10.0 # Velocidade de movimento
# Entidades (pessoas do dataset)
entity_size = 10.0 

# Parâmetros de Processamento (Critério de Processamento e Visualização)
PROXIMITY_THRESHOLD = 50.0  # Distância para o ALERTA (Amarelo)
COLLISION_DISTANCE = 25.0 # Distância para o EVITAR COLISÃO/COLISÃO (Vermelho/Círculo)
SAFE_DISTANCE = 15.0 # Distância mínima entre entidades para evitar colisão
WORLD_CENTER = [0, 0] # Assume-se o centro do "Cultural Dataset" como (0,0)

# Load data from Paths_D.txt
def load_data(filepath):
    global scale_factor, entities
    entities = []
    try:
        with open(filepath, 'r') as file:
            lines = file.readlines()
            
            match = re.search(r'\[(\d+)\]', lines[0])
            if match:
                scale_factor = float(match.group(1))
            else:
                raise ValueError("Scale factor not found in the first line.")
            for line in lines[1:11]:
                parts = line.split('\t')
                if len(parts) > 1:
                    entity_data = re.findall(r'\((\d+),(\d+),(\d+)\)', parts[1])
                    entities.append([(int(x), int(y), int(f)) for x, y, f in entity_data])
            
            if len(entities) < 6:
                print(f"Atenção: Apenas {len(entities)} entidades foram carregadas. O requisito é de pelo menos 6.")
                
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{filepath}' não encontrado. Certifique-se de que está no diretório correto.")
        os._exit(1)
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        os._exit(1)


# --- Funções de Desenho ---
def draw_square(x, y, size):
    half_size = size / 2
    glBegin(GL_QUADS)
    glVertex2f(x - half_size, y - half_size) # Bottom-left
    glVertex2f(x + half_size, y - half_size) # Bottom-right
    glVertex2f(x + half_size, y + half_size) # Top-right
    glVertex2f(x - half_size, y + half_size) # Top-left
    glEnd()

def draw_circle(x, y, radius):
    glBegin(GL_POLYGON)
    for i in range(360):
        angle = i * math.pi / 180
        glVertex2f(x + radius * cos(angle), y + radius * sin(angle))
    glEnd()

# Converte coordenadas do dataset (Mundo) para o plano de visualização (Janela)
def world_to_screen(x_world, y_world, scale):
    x_screen = (x_world / scale) * 3 + (window_width / 2)
    y_screen = (y_world / scale) * 3 + (window_height / 2)
    return x_screen, y_screen

# --- Lógica de Evitação de Colisão ---
def avoid_collision(current_x, current_y, neighbors):
    """Calcula um pequeno desvio para evitar vizinhos próximos."""
    force_x, force_y = 0.0, 0.0
    
    for nx, ny in neighbors:
        # Calcular distância entre o ponto atual e o vizinho
        distance = sqrt((current_x - nx) ** 2 + (current_y - ny) ** 2)
        
        # Aplicar repulsão se a distância for menor que o SAFE_DISTANCE
        if distance < SAFE_DISTANCE and distance > 0.0:
            # Força é inversamente proporcional à distância (quanto mais perto, mais forte)
            # Normaliza o vetor (nx-current_x, ny-current_y)
            dx = current_x - nx
            dy = current_y - ny
            
            # Magnitude da força repulsiva
            repulsion_strength = (SAFE_DISTANCE - distance) / SAFE_DISTANCE
            
            # Adiciona a força no sentido oposto ao vizinho
            force_x += repulsion_strength * dx / distance
            force_y += repulsion_strength * dy / distance
    
    # Limita o movimento de correção (para evitar saltos bruscos)
    max_correction = 0.5 
    force_x = max(-max_correction, min(max_correction, force_x))
    force_y = max(-max_correction, min(max_correction, force_y))
    
    return force_x, force_y

# --- Função de Desenho e Visualização Principal ---
def draw_entities():
    global frame
    glClear(GL_COLOR_BUFFER_BIT)

    # 1. Encontra as posições de todas as entidades para o frame atual
    current_positions_screen = []
    
    # A. Adiciona o avatar para o cálculo de colisão
    current_positions_screen.append(tuple(avatar_position))
    
    # B. Adiciona as entidades do dataset
    for entity in entities:
        if frame < len(entity):
            x_world, y_world, _ = entity[frame]
            x_screen, y_screen = world_to_screen(x_world, y_world, scale_factor)
            current_positions_screen.append((x_screen, y_screen))

    # 2. Desenha o Avatar (Entidade Controlada)
    glColor3f(0.0, 0.0, 1.0) # Azul para o avatar
    draw_square(avatar_position[0], avatar_position[1], avatar_size)

    # 3. Desenha as Entidades do Dataset
    for i, entity in enumerate(entities):
        if frame < len(entity):
            x_world, y_world, _ = entity[frame]
            x_screen, y_screen = world_to_screen(x_world, y_world, scale_factor)

            # --- Processamento 1: Evitação de Colisão (Movimento) ---
            neighbors = [pos for j, pos in enumerate(current_positions_screen) if j != i + 1] 
            # --- Processamento 2: Verificação de Proximidade (Visualização/Cor) ---
            distance_to_avatar = sqrt((x_screen - avatar_position[0]) ** 2 + (y_screen - avatar_position[1]) ** 2)
            
            if distance_to_avatar <= COLLISION_DISTANCE: # Super perto: COLISÃO/EVASÃO
                glColor3f(1.0, 0.0, 0.0) # Vermelho
                draw_circle(x_screen, y_screen, entity_size) # Altera para círculo (alerta máximo)
            elif distance_to_avatar <= PROXIMITY_THRESHOLD: # Perto: ALERTA
                glColor3f(1.0, 1.0, 0.0) # Amarelo
                draw_square(x_screen, y_screen, entity_size)
            else:
                # Distância Normal: Entidade Padrão
                glColor3f(0.0, 1.0, 0.0) # Verde
                draw_square(x_screen, y_screen, entity_size)
        
    glutSwapBuffers()

# Update frame (Animação)
def update(value):
    global frame
    frame += 1
    max_frames = max(len(entity) for entity in entities) if entities else 0
    
    if frame >= max_frames:
        frame = 0  # Loop
        
    glutPostRedisplay()
    glutTimerFunc(100, update, 0) # 100ms = 10 FPS (Taxa de Quadros)

# Keyboard interaction
def keyboard(key, x, y):
    global avatar_position
    
    if key == b'\x1b': # ESC key
        os._exit(0)
    elif key == b'w': # Move up
        avatar_position[1] += avatar_speed
    elif key == b's': # Move down
        avatar_position[1] -= avatar_speed
    elif key == b'a': # Move left
        avatar_position[0] -= avatar_speed
    elif key == b'd': # Move right
        avatar_position[0] += avatar_speed
        
    # Limita o avatar dentro da janela
    avatar_position[0] = max(avatar_size/2, min(window_width - avatar_size/2, avatar_position[0]))
    avatar_position[1] = max(avatar_size/2, min(window_height - avatar_size/2, avatar_position[1]))

    glutPostRedisplay() # Redesenha imediatamente após o movimento do avatar

# Initialize OpenGL
def init():
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # Define o sistema de coordenadas 2D do OpenGL com o tamanho da janela
    gluOrtho2D(0, window_width, 0, window_height)

def main():
    # Caminho do arquivo a ser testado
    # OBS: O arquivo deve estar na raiz do projeto (ou altere o path)
    load_data('Paths_D.txt') 
    
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(window_width, window_height)
    glutCreateWindow(b"T1 CG Soraia - Refatorado")
    init()
    glutDisplayFunc(draw_entities)
    glutKeyboardFunc(keyboard)
    glutTimerFunc(100, update, 0)
    glutMainLoop()

if __name__ == "__main__":
    # É uma boa prática inicializar a posição do avatar para floats
    avatar_position = [float(avatar_position[0]), float(avatar_position[1])]
    main()
