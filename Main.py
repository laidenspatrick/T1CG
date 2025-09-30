from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import re
import math
from math import cos, sin, sqrt
import os

# Global variables
entities = []
frame = 0
scale_factor = 1.0
window_width, window_height = 800, 600
avatar_position = [400, 300]  # Initial position of the avatar
proximity_threshold = 50  # Distance threshold for when it is kinda close
entity_size = 10  # Size of the entities

# Load data from Paths_D.txt
def load_data(filepath):
    global scale_factor
    with open(filepath, 'r') as file:
        lines = file.readlines()
        scale_factor = float(re.search(r'\[(\d+)\]', lines[0]).group(1))
        for line in lines[1:11]:  # Load only the first 10 entities
            parts = line.split('\t')
            if len(parts) > 1:
                entity_data = re.findall(r'\((\d+),(\d+),(\d+)\)', parts[1])
                entities.append([(int(x), int(y), int(f)) for x, y, f in entity_data])

# Initialize OpenGL
def init():
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)

# Draw entities
def draw_entities():
    global frame
    glClear(GL_COLOR_BUFFER_BIT)

    for i, entity in enumerate(entities):
        if frame < len(entity):
            x, y, _ = entity[frame]

            # Adjust coordinates to center of the window
            x = (x / scale_factor) * 30 + (window_width / 2)
            y = (y / scale_factor) * 30 + (window_height / 2)

            # Check proximity to the avatar
            distance_to_avatar = sqrt((x - avatar_position[0]) ** 2 + (y - avatar_position[1]) ** 2)
            if distance_to_avatar <= entity_size:  # Super close
                glColor3f(1.0, 0.0, 0.0)  # Red
                draw_circle(x, y, entity_size)  # Draw as a circle
            elif distance_to_avatar <= proximity_threshold:  # Kinda close
                glColor3f(1.0, 1.0, 0.0)  # Yellow
                draw_square(x, y, entity_size)  # Draw as a square
            else:
                glColor3f(0.0, 1.0, 0.0)  # Green otherwise
                draw_square(x, y, entity_size)  # Draw as a square

    # Draw the avatar
    glColor3f(0.0, 0.0, 1.0)  # Blue for the avatar
    draw_square(avatar_position[0], avatar_position[1], 15)  # Draw avatar
    glutSwapBuffers()

# Draw a square
def draw_square(x, y, size):
    half_size = size / 2
    glBegin(GL_QUADS)
    glVertex2f(x - half_size, y - half_size)  # Bottom-left
    glVertex2f(x + half_size, y - half_size)  # Bottom-right
    glVertex2f(x + half_size, y + half_size)  # Top-right
    glVertex2f(x - half_size, y + half_size)  # Top-left
    glEnd()

# Draw a circle
def draw_circle(x, y, radius):
    glBegin(GL_POLYGON)
    for i in range(360):
        angle = i * math.pi / 180
        glVertex2f(x + radius * cos(angle), y + radius * sin(angle))
    glEnd()

# Update frame
def update(value):
    global frame
    frame += 1
    max_frames = max(len(entity) for entity in entities)  # Maximum number of frames
    if frame >= max_frames:
        frame = 0  # Reset frame to loop the animation
    glutPostRedisplay()
    glutTimerFunc(100, update, 0)

# Keyboard interaction
def keyboard(key, x, y):
    global avatar_position
    step = 10  # Movement step
    if key == b'\x1b':  # ESC key
        os._exit(0)  # Exit the program immediately
    elif key == b'w':  # Move up
        avatar_position[1] += step
    elif key == b's':  # Move down
        avatar_position[1] -= step
    elif key == b'a':  # Move left
        avatar_position[0] -= step
    elif key == b'd':  # Move right
        avatar_position[0] += step

# Main function
def main():
    load_data('Paths_D.txt')
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(window_width, window_height)
    glutCreateWindow(b"T1 CG Soraia")
    init()
    glutDisplayFunc(draw_entities)
    glutKeyboardFunc(keyboard)
    glutTimerFunc(100, update, 0)
    glutMainLoop()

if __name__ == "__main__":
    main()
