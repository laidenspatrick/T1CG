import com.jogamp.opengl.*;
import com.jogamp.opengl.awt.GLCanvas;
import com.jogamp.opengl.glu.GLU;

import javax.swing.*;
import java.awt.*;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.io.File;
import java.io.FileNotFoundException;
import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static java.lang.Math.*;

public class AnimacaoPessoas implements GLEventListener {

    // --- Parametros Globais ---
    private static final int WINDOW_WIDTH = 800;
    private static final int WINDOW_HEIGHT = 600;
    private static final float AVATAR_SIZE = 15.0f;
    private static final float AVATAR_SPEED = 10.0f;
    private static final float ENTITY_SIZE = 10.0f;

    // Parametros de Processamento
    private static final float PROXIMITY_THRESHOLD = 50.0f;   // Distancia para ALERTA (Amarelo)
    private static final float COLLISION_DISTANCE = 25.0f;    // Distancia para COLISAO (Vermelho/Circulo)
    private static final float SAFE_DISTANCE = 15.0f;         // Distancia minima entre entidades

    // Dados de Animacao
    private List<List<int[]>> entities = new ArrayList<>();
    private int frame = 0;
    private float scaleFactor = 1.0f;
    private float[] avatarPosition = {WINDOW_WIDTH / 2.0f, WINDOW_HEIGHT / 2.0f};

    // Objeto GLU para a projecao
    private GLU glu;

    // Construtor: Carrega dados ao inicializar
    public AnimacaoPessoas(String filePath) {
        loadData(filePath);
    }

    // ---------------- Funcoes Auxiliares ----------------

    private void loadData(String filepath) {
        entities.clear();
        try (Scanner scanner = new Scanner(new File(filepath))) {
            String firstLine = scanner.nextLine();
            
            // 1. Obter o Fator de Escala [XXX]
            Matcher match = Pattern.compile("\\[(\\d+)\\]").matcher(firstLine);
            if (match.find()) {
                scaleFactor = Float.parseFloat(match.group(1));
            } else {
                throw new IllegalArgumentException("Scale factor nao encontrado na primeira linha.");
            }

            // 2. Carregar entidades (limitado a 10 para testes rapidos, como no Python)
            int count = 0;
            while (scanner.hasNextLine() && count < 10) {
                String line = scanner.nextLine();
                String[] parts = line.split("\t");
                if (parts.length > 1) {
                    Matcher dataMatch = Pattern.compile("\\((\\d+),(\\d+),(\\d+)\\)").matcher(parts[1]);
                    List<int[]> entityFrames = new ArrayList<>();
                    while (dataMatch.find()) {
                        int x = Integer.parseInt(dataMatch.group(1));
                        int y = Integer.parseInt(dataMatch.group(2));
                        int f = Integer.parseInt(dataMatch.group(3));
                        entityFrames.add(new int[]{x, y, f});
                    }
                    if (!entityFrames.isEmpty()) {
                        entities.add(entityFrames);
                        count++;
                    }
                }
            }

            if (entities.size() < 6) {
                System.out.println("[Atencao] Apenas " + entities.size() + " entidades carregadas (minimo = 6).");
            }

        } catch (FileNotFoundException e) {
            System.err.println("[ERRO] Arquivo '" + filepath + "' nao encontrado.");
            System.exit(1);
        } catch (Exception e) {
            System.err.println("[ERRO] Erro ao carregar dados: " + e.getMessage());
            System.exit(1);
        }
    }

    private float[] worldToScreen(int x_world, int y_world, float scale) {
        float x_screen = (x_world / scale) * 3 + (WINDOW_WIDTH / 2.0f);
        float y_screen = (y_world / scale) * 3 + (WINDOW_HEIGHT / 2.0f);
        return new float[]{x_screen, y_screen};
    }

    private void drawSquare(GL2 gl, float x, float y, float size) {
        float halfSize = size / 2.0f;
        gl.glBegin(GL2.GL_QUADS);
        gl.glVertex2f(x - halfSize, y - halfSize);
        gl.glVertex2f(x + halfSize, y - halfSize);
        gl.glVertex2f(x + halfSize, y + halfSize);
        gl.glVertex2f(x - halfSize, y + halfSize);
        gl.glEnd();
    }

    private void drawCircle(GL2 gl, float x, float y, float radius, int segments) {
        gl.glBegin(GL2.GL_POLYGON);
        for (int i = 0; i < segments; i++) {
            double angle = i * 2 * PI / segments;
            gl.glVertex2f(x + (float) (radius * cos(angle)), y + (float) (radius * sin(angle)));
        }
        gl.glEnd();
    }

    private float[] avoidCollision(float currentX, float currentY, List<float[]> neighbors) {
        float forceX = 0.0f;
        float forceY = 0.0f;

        for (float[] neighbor : neighbors) {
            float nx = neighbor[0];
            float ny = neighbor[1];

            float distance = (float) sqrt(pow(currentX - nx, 2) + pow(currentY - ny, 2));

            if (distance > 0.0f && distance < SAFE_DISTANCE) {
                float dx = currentX - nx;
                float dy = currentY - ny;

                float repulsionStrength = (SAFE_DISTANCE - distance) / SAFE_DISTANCE;

                forceX += repulsionStrength * dx / distance;
                forceY += repulsionStrength * dy / distance;
            }
        }

        // Limita o deslocamento
        float maxCorr = 0.5f;
        forceX = max(-maxCorr, min(maxCorr, forceX));
        forceY = max(-maxCorr, min(maxCorr, forceY));

        return new float[]{forceX, forceY};
    }

    // ---------------- JOGL/OpenGL Callbacks ----------------

    @Override
    public void init(GLAutoDrawable drawable) {
        GL2 gl = drawable.getGL().getGL2();
        glu = new GLU();
        gl.glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        gl.glMatrixMode(GL2.GL_PROJECTION);
        gl.glLoadIdentity();
        // Define o sistema de coordenadas 2D (0,0 no canto inferior esquerdo)
        glu.gluOrtho2D(0.0, WINDOW_WIDTH, 0.0, WINDOW_HEIGHT);
    }

    @Override
    public void dispose(GLAutoDrawable drawable) {
        // Limpeza de recursos
    }

    @Override
    public void display(GLAutoDrawable drawable) {
        GL2 gl = drawable.getGL().getGL2();
        gl.glClear(GL2.GL_COLOR_BUFFER_BIT);

        List<float[]> currentPositions = new ArrayList<>();
        // Adiciona o avatar como primeira posicao para calculos de colisao
        currentPositions.add(avatarPosition);

        List<float[]> positionsForDrawing = new ArrayList<>();

        // 1. Calcula a posicao das entidades no frame atual
        for (List<int[]> entity : entities) {
            if (frame < entity.size()) {
                int[] frameData = entity.get(frame);
                float[] screenPos = worldToScreen(frameData[0], frameData[1], scaleFactor);
                positionsForDrawing.add(screenPos);
                currentPositions.add(screenPos);
            }
        }

        // 2. Desenha Avatar (Azul)
        gl.glColor3f(0.0f, 0.0f, 1.0f);
        drawSquare(gl, avatarPosition[0], avatarPosition[1], AVATAR_SIZE);

        // 3. Desenha Entidades
        for (int i = 0; i < positionsForDrawing.size(); i++) {
            float[] pos = positionsForDrawing.get(i);
            float x_original = pos[0];
            float y_original = pos[1];
            
            float x_screen = x_original;
            float y_screen = y_original;

            // Evitacao de colisao (calcula o desvio baseado em vizinhos, incluindo o avatar)
            // A lista de vizinhos deve excluir a entidade atual (indice i + 1, pois o avatar é 0)
            List<float[]> neighborsForCollision = new ArrayList<>();
            for (int j = 0; j < currentPositions.size(); j++) {
                if (j != i + 1) {
                    neighborsForCollision.add(currentPositions.get(j));
                }
            }
            
            float[] forces = avoidCollision(x_original, y_original, neighborsForCollision);
            x_screen += forces[0];
            y_screen += forces[1];

            // Distancia ate o avatar (calculo de proximidade)
            float dx = x_screen - avatarPosition[0];
            float dy = y_screen - avatarPosition[1];
            float distance = (float) sqrt(dx * dx + dy * dy);

            if (distance <= COLLISION_DISTANCE) {
                gl.glColor3f(1.0f, 0.0f, 0.0f); // Vermelho: COLISAO
                drawCircle(gl, x_screen, y_screen, ENTITY_SIZE, 64);
            } else if (distance <= PROXIMITY_THRESHOLD) {
                gl.glColor3f(1.0f, 1.0f, 0.0f); // Amarelo: ALERTA
                drawSquare(gl, x_screen, y_screen, ENTITY_SIZE);
            } else {
                gl.glColor3f(0.0f, 1.0f, 0.0f); // Verde: Normal
                drawSquare(gl, x_screen, y_screen, ENTITY_SIZE);
            }
        }
    }

    @Override
    public void reshape(GLAutoDrawable drawable, int x, int y, int width, int height) {
        GL2 gl = drawable.getGL().getGL2();
        gl.glViewport(0, 0, width, height);
        gl.glMatrixMode(GL2.GL_PROJECTION);
        gl.glLoadIdentity();
        glu.gluOrtho2D(0.0, WINDOW_WIDTH, 0.0, WINDOW_HEIGHT);
    }
    
    // ---------------- Controle e Loop Principal ----------------

    public static void main(String[] args) {
        // Nome do arquivo de dados (deve estar no diretorio raiz do projeto)
        String dataPath = "Paths_D.txt"; 
        
        // 1. Configura JOGL e a janela
        GLProfile profile = GLProfile.get(GLProfile.GL2);
        GLCapabilities caps = new GLCapabilities(profile);
        GLCanvas canvas = new GLCanvas(caps);

        AnimacaoPessoas animator = new AnimacaoPessoas(dataPath);
        canvas.addGLEventListener(animator);

        // 2. Configura a interacao do teclado (KeyAdapter para simplificar)
        canvas.addKeyListener(new KeyAdapter() {
            @Override
            public void keyPressed(KeyEvent e) {
                animator.handleKeyPress(e.getKeyCode(), canvas);
            }
        });
        canvas.setFocusable(true);

        // 3. Configura o JFrame (Janela)
        JFrame frame = new JFrame("T1 CG - Evitacao de Colisao (Java JOGL)");
        frame.getContentPane().add(canvas);
        frame.setSize(WINDOW_WIDTH, WINDOW_HEIGHT);
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setVisible(true);

        // 4. Configura o Timer de Animacao (10 FPS = 100ms)
        Timer timer = new Timer(100, e -> {
            animator.updateFrame();
            canvas.display(); // Redesenha
        });
        timer.start();
    }
    
    // ---------------- Logica de Animacao e Teclado ----------------
    
    public void updateFrame() {
        frame++;
        int maxFrames = entities.isEmpty() ? 0 : entities.stream().mapToInt(List::size).max().orElse(0);
        
        if (frame >= maxFrames) {
            frame = 0; // Loop da animacao
        }
    }

    public void handleKeyPress(int keyCode, GLCanvas canvas) {
        switch (keyCode) {
            case KeyEvent.VK_ESCAPE:
                System.exit(0);
                break;
            case KeyEvent.VK_W:
                avatarPosition[1] = min(WINDOW_HEIGHT - AVATAR_SIZE / 2.0f, avatarPosition[1] + AVATAR_SPEED);
                break;
            case KeyEvent.VK_S:
                avatarPosition[1] = max(AVATAR_SIZE / 2.0f, avatarPosition[1] - AVATAR_SPEED);
                break;
            case KeyEvent.VK_A:
                avatarPosition[0] = max(AVATAR_SIZE / 2.0f, avatarPosition[0] - AVATAR_SPEED);
                break;
            case KeyEvent.VK_D:
                avatarPosition[0] = min(WINDOW_WIDTH - AVATAR_SIZE / 2.0f, avatarPosition[0] + AVATAR_SPEED);
                break;
        }
        canvas.display(); // Redesenha imediatamente apos o movimento do avatar
    }
}
