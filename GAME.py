# -*- coding: utf-8 -*-
import pygame
import cv2
import mediapipe as mp
import random
import math
import os
import subprocess
import sys

# --- Pygame and Game Constants ---
pygame.init()
pygame.mixer.init()  # Initialize the mixer for sound

# Screen dimensions
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("体感射击游戏")

try:
    background_image = pygame.image.load("背景图1.png").convert()
    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
except pygame.error:
    print("Warning: Background image not found. Using a solid color background.")
    background_image = None

# Colors (Apple-style minimalist palette)
WHITE = (255, 255, 255)
LIGHT_GRAY = (242, 242, 247)
DARK_GRAY = (28, 28, 30)
BLUE = (10, 132, 255)
ACCENT_GREEN = (48, 209, 88)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

# Fonts
try:
    font_title = pygame.font.Font("SanJiHuaChaoTi-Cu-2.ttf", 130)
    font_title.bold = True
    font_large = pygame.font.Font("SanJiHuaChaoTi-Cu-2.ttf", 48)
    font_large.bold = True
    font_medium = pygame.font.Font("dinglieciweifont.ttf", 36)
    font_small = pygame.font.Font("dinglieciweifont.ttf", 36)
    font_score = pygame.font.Font("dinglieciweifont.ttf", 40)
except FileNotFoundError:
     font_title = pygame.font.SysFont("SimHei", 130, bold=True)
     font_large = pygame.font.SysFont("SimHei", 48, bold=True)
     font_medium = pygame.font.SysFont("SimHei", 36)
     font_small = pygame.font.SysFont("SimHei", 36)
     font_score = pygame.font.SysFont("SimHei", 40)

# --- Sound Setup ---
try:
    sound_explosion = pygame.mixer.Sound("fire.mp3")
except pygame.error:
    print("Warning: fire.mp3 not found. Please place an explosion sound file in the game directory.")
    sound_explosion = None

# --- Game Objects ---
class Ball:
    """A single target object for the player to shoot."""
    def __init__(self, image_path, balls=[]):
        self.radius = 80  # Object size
        self.image_path = image_path
        
        if os.path.exists(self.image_path):
            self.image = pygame.image.load(self.image_path).convert_alpha()
            self.image = pygame.transform.scale(self.image, (self.radius * 2, self.radius * 2))
        else:
            print(f"Warning: Image not found at {self.image_path}. Using a placeholder circle.")
            self.image = None

        self.color = random.choice([BLUE, ACCENT_GREEN, RED, YELLOW, ORANGE])
        self.pos = self.get_random_pos(balls)
        self.velocity = self.get_random_velocity()

    def get_random_pos(self, balls):
        while True:
            new_pos = [random.randint(self.radius, SCREEN_WIDTH - self.radius),
                       random.randint(self.radius, SCREEN_HEIGHT - self.radius)]
            overlap = False
            for ball in balls:
                dist_to_ball = math.sqrt((new_pos[0] - ball.pos[0])**2 + (new_pos[1] - ball.pos[1])**2)
                if dist_to_ball < self.radius + ball.radius:
                    overlap = True
                    break
            if not overlap:
                return new_pos

    def get_random_velocity(self):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 6)
        return [speed * math.cos(angle), speed * math.sin(angle)]

    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        
        if self.pos[0] <= self.radius:
            self.pos[0] = self.radius
            self.velocity[0] *= -1
        elif self.pos[0] >= SCREEN_WIDTH - self.radius:
            self.pos[0] = SCREEN_WIDTH - self.radius
            self.velocity[0] *= -1
        
        if self.pos[1] <= self.radius:
            self.pos[1] = self.radius
            self.velocity[1] *= -1
        elif self.pos[1] >= SCREEN_HEIGHT - self.radius:
            self.pos[1] = SCREEN_HEIGHT - self.radius
            self.velocity[1] *= -1

    def draw(self, surface):
        if self.image:
            surface.blit(self.image, (self.pos[0] - self.radius, self.pos[1] - self.radius))
        else:
            pygame.draw.circle(surface, self.color, (int(self.pos[0]), int(self.pos[1])), self.radius)

class Crosshair:
    """The player's aiming cursor controlled by hand gestures."""
    def __init__(self):
        self.pos = [SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2]
        self.is_closed = False
        try:
            # Load images for both open and closed hand states
            self.open_hand_image = pygame.image.load("手掌.png").convert_alpha()
            self.closed_hand_image = pygame.image.load("握拳.png").convert_alpha()

            # Scale images to the desired size
            self.open_hand_image = pygame.transform.scale(self.open_hand_image, (100, 100))
            self.closed_hand_image = pygame.transform.scale(self.closed_hand_image, (100, 100))

            # Set the initial image to the open hand
            self.image = self.open_hand_image
            self.rect = self.image.get_rect()
            self.radius = self.rect.width / 2
        except pygame.error as e:
            print(f"Warning: Could not load hand images ('手掌.png' or '握拳.png'): {e}. Drawing a circle instead.")
            self.open_hand_image = None
            self.closed_hand_image = None
            self.image = None
            self.radius = 15
            self.color = DARK_GRAY

    def update(self, hand_x, hand_y):
        self.pos[0] = hand_x
        self.pos[1] = hand_y

    def set_state(self, is_closed):
        """Sets the hand state to open or closed and updates the image."""
        if self.open_hand_image and self.closed_hand_image:
            # Only update if the state has actually changed to avoid unnecessary work
            if is_closed and not self.is_closed:
                self.image = self.closed_hand_image
                self.is_closed = True
            elif not is_closed and self.is_closed:
                self.image = self.open_hand_image
                self.is_closed = False

    def draw(self, surface):
        if self.image:
            # Center the current image on the hand position and draw it
            self.rect.center = (int(self.pos[0]), int(self.pos[1]))
            surface.blit(self.image, self.rect)
        else:
            # Draw the original circle if images failed to load
            pygame.draw.circle(surface, self.color, (int(self.pos[0]), int(self.pos[1])), self.radius, 3)

class Particle:
    """A single particle for the explosion effect."""
    def __init__(self, x, y, color):
        self.pos = [x, y]
        self.velocity = [random.uniform(-3, 3), random.uniform(-3, 3)]
        self.radius = random.randint(3, 8)
        self.color = color
        self.lifetime = 60

    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.radius -= 0.1
        self.lifetime -= 1

    def draw(self, surface):
        if self.radius > 0:
            pygame.draw.circle(surface, self.color, (int(self.pos[0]), int(self.pos[1])), int(self.radius))

# --- OpenCV and MediaPipe Setup ---
cap = cv2.VideoCapture(0)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# --- Game State ---
game_state = "loading"  # "loading", "transition", "playing"
pingpong_score = 0
fishing_score = 0
healing_score = 0
loading_start_time = 0
transition_start_time = 0
game_to_switch_to = None

# --- Loading Screen Elements ---
start_ball = {
    'pos': [SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 150],
    'radius': 80,
    'color': ACCENT_GREEN,
    'text_color': WHITE
}

# --- Game Elements ---
balls = []
image_files = ["钓鱼竿.png", "乒乓球拍.png", "中草药.png"]
crosshair = Crosshair()
last_shoot_time = 0
particles = []

# Game loop variables
running = True
clock = pygame.time.Clock()

# Main Game Loop
while running:
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- OpenCV Hand Tracking Logic ---
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame from camera.")
        continue

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            hand_x = int(index_finger_tip.x * SCREEN_WIDTH)
            hand_y = int(index_finger_tip.y * SCREEN_HEIGHT)
            crosshair.update(hand_x, hand_y)

            # Check for pinch gesture to change cursor image
            distance = math.sqrt((thumb_tip.x - index_finger_tip.x)**2 + (thumb_tip.y - index_finger_tip.y)**2)
            if distance < 0.05:
                crosshair.set_state(is_closed=True)
            else:
                crosshair.set_state(is_closed=False)

            # --- State-Specific Logic ---
            if game_state == "loading":
                dist_to_ball = math.sqrt((crosshair.pos[0] - start_ball['pos'][0])**2 + (crosshair.pos[1] - start_ball['pos'][1])**2)
                
                if dist_to_ball < start_ball['radius'] + crosshair.radius:
                    if loading_start_time == 0:
                        loading_start_time = pygame.time.get_ticks()
                    
                    elapsed_time = pygame.time.get_ticks() - loading_start_time
                    if elapsed_time >= 1000:
                        game_state = "transition"
                        transition_start_time = pygame.time.get_ticks()
                        loading_start_time = 0  # Reset the loading timer
                else:
                    loading_start_time = 0
            elif game_state == "playing":
                # The distance is already calculated, just use it for shooting logic
                if distance < 0.05 and pygame.time.get_ticks() - last_shoot_time > 500:
                    for i, ball in enumerate(balls):
                        dist_to_ball = math.sqrt((crosshair.pos[0] - ball.pos[0])**2 + (crosshair.pos[1] - ball.pos[1])**2)
                        if dist_to_ball <= ball.radius + crosshair.radius:
                            if ball.image_path == "乒乓球拍.png":
                                pingpong_score += 1
                            elif ball.image_path == "钓鱼竿.png":
                                fishing_score += 1
                            elif ball.image_path == "中草药.png":
                                healing_score += 1

                            if sound_explosion:
                                sound_explosion.play()
                            for _ in range(30):
                                particles.append(Particle(ball.pos[0], ball.pos[1], ball.color))
                            
                            shot_ball_type = ball.image_path
                            other_balls = [b for b in balls if b is not ball]
                            
                            is_last_of_type = not any(b.image_path == shot_ball_type for b in other_balls)
                            
                            if is_last_of_type:
                                new_image_path = shot_ball_type
                            else:
                                new_image_path = random.choice(image_files)
                            
                            balls[i] = Ball(image_path=new_image_path, balls=other_balls)
                            last_shoot_time = pygame.time.get_ticks()
                            
                            if pingpong_score > 5:
                                game_to_switch_to = "pingpong.py"
                                running = False
                            elif healing_score > 5:
                                game_to_switch_to = "medicine.py"
                                running = False
                            break

    # --- Game Logic ---
    if game_state == "transition":
        if pygame.time.get_ticks() - transition_start_time > 2000:  # Show loading for 2 seconds
            game_state = "playing"
            pingpong_score = 0
            fishing_score = 0
            healing_score = 0
            particles = []
            last_shoot_time = 0
            balls = []

            # Ensure at least one of each ball type
            for image_path in image_files:
                balls.append(Ball(image_path=image_path, balls=balls))

            # Fill the rest with random balls up to 8
            remaining_balls_count = 8 - len(image_files)
            for _ in range(remaining_balls_count):
                image_path = random.choice(image_files)
                balls.append(Ball(image_path=image_path, balls=balls))

            try:
                pygame.mixer.music.load("spring.mp3")
                pygame.mixer.music.play(loops=-1)
            except pygame.error:
                pass
    if game_state == "playing":
        for ball in balls:
            ball.update()

        for i in range(len(balls)):
            for j in range(i + 1, len(balls)):
                ball1, ball2 = balls[i], balls[j]
                dist_vec = [ball1.pos[0] - ball2.pos[0], ball1.pos[1] - ball2.pos[1]]
                dist = math.sqrt(dist_vec[0]**2 + dist_vec[1]**2)
                if dist < ball1.radius + ball2.radius:
                    overlap = (ball1.radius + ball2.radius) - dist
                    if dist == 0: dist = 1
                    normal_vec = [dist_vec[0] / dist, dist_vec[1] / dist]
                    ball1.pos[0] += normal_vec[0] * overlap / 2
                    ball1.pos[1] += normal_vec[1] * overlap / 2
                    ball2.pos[0] -= normal_vec[0] * overlap / 2
                    ball2.pos[1] -= normal_vec[1] * overlap / 2
                    v1, v2 = ball1.velocity, ball2.velocity
                    x1_minus_x2 = [ball1.pos[0] - ball2.pos[0], ball1.pos[1] - ball2.pos[1]]
                    dist_squared = x1_minus_x2[0]**2 + x1_minus_x2[1]**2
                    if dist_squared == 0: continue
                    dot_product = (v1[0] - v2[0]) * x1_minus_x2[0] + (v1[1] - v2[1]) * x1_minus_x2[1]
                    factor = dot_product / dist_squared
                    change_vx, change_vy = factor * x1_minus_x2[0], factor * x1_minus_x2[1]
                    ball1.velocity[0] -= change_vx
                    ball1.velocity[1] -= change_vy
                    ball2.velocity[0] += change_vx
                    ball2.velocity[1] += change_vy

        for particle in particles:
            particle.update()
        particles = [p for p in particles if p.lifetime > 0]

    # --- Drawing ---
    if background_image:
        screen.blit(background_image, (0, 0))
    else:
        screen.fill(LIGHT_GRAY)

    if game_state == "loading":
        title_text = font_title.render("银动﹒乐享", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 150))
        screen.blit(title_text, title_rect)
        
        instruction_text = font_small.render("游戏玩法：通过手势移动准星，并用捏合手势射击目标！", True, DARK_GRAY)
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50))
        screen.blit(instruction_text, instruction_rect)
        
        start_instruction = font_medium.render("请移动准星到绿色的'开始'球上, 开始游戏", True, DARK_GRAY)
        start_rect = start_instruction.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 20))
        screen.blit(start_instruction, start_rect)

        pygame.draw.circle(screen, start_ball['color'], (int(start_ball['pos'][0]), int(start_ball['pos'][1])), start_ball['radius'])
        start_text = font_large.render("开始", True, start_ball['text_color'])
        start_text_rect = start_text.get_rect(center=(start_ball['pos'][0], start_ball['pos'][1]))
        screen.blit(start_text, start_text_rect)

        if loading_start_time != 0:
            elapsed_time = pygame.time.get_ticks() - loading_start_time
            progress = min(elapsed_time / 1000.0, 1.0)
            end_angle_rad = progress * 2 * math.pi

            if end_angle_rad > 0:
                arc_rect = pygame.Rect(start_ball['pos'][0] - start_ball['radius'],
                                       start_ball['pos'][1] - start_ball['radius'],
                                       start_ball['radius'] * 2,
                                       start_ball['radius'] * 2)
                pygame.draw.arc(screen, BLUE, arc_rect, -math.pi / 2, -math.pi / 2 + end_angle_rad, 10)
    elif game_state == "transition":
        # Keep the loading screen visible in the background
        title_text = font_title.render("银动﹒乐享", True, DARK_GRAY)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 150))
        screen.blit(title_text, title_rect)
        
        instruction_text = font_small.render("游戏玩法：通过手势移动准星，并用捏合手势射击目标！", True, DARK_GRAY)
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50))
        screen.blit(instruction_text, instruction_rect)
        
        start_instruction = font_medium.render("请移动准星到绿色的'开始'球上, 以开始游戏", True, DARK_GRAY)
        start_rect = start_instruction.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 20))
        screen.blit(start_instruction, start_rect)

        pygame.draw.circle(screen, start_ball['color'], (int(start_ball['pos'][0]), int(start_ball['pos'][1])), start_ball['radius'])
        start_text = font_large.render("开始", True, start_ball['text_color'])
        start_text_rect = start_text.get_rect(center=(start_ball['pos'][0], start_ball['pos'][1]))
        screen.blit(start_text, start_text_rect)

        # Create a semi-transparent overlay
        popup_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        popup_surface.fill((0, 0, 0, 180))  # Black with 180/255 alpha
        screen.blit(popup_surface, (0, 0))

        # Display the "Loading..." text
        loading_text = font_large.render("抓乒乓球拍或草药！分数大于5即可进入对应游戏！", True, WHITE)
        loading_rect = loading_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
        screen.blit(loading_text, loading_rect)
    elif game_state == "playing":
        for ball in balls:
            ball.draw(screen)
        for particle in particles:
            particle.draw(screen)
        pingpong_score_text = font_score.render(f"乒乓球分数: {pingpong_score}", True, WHITE)
        screen.blit(pingpong_score_text, (20, 20))
        
        fishing_score_text = font_score.render(f"钓鱼分数: {fishing_score}", True, WHITE)
        screen.blit(fishing_score_text, (20, 60))

        healing_score_text = font_score.render(f"治疗分数: {healing_score}", True, WHITE)
        screen.blit(healing_score_text, (20, 100))

    crosshair.draw(screen)
    frame_scaled = cv2.resize(frame, (200, 150))
    frame_rgb = cv2.cvtColor(frame_scaled, cv2.COLOR_BGR2RGB)
    frame_pygame = pygame.image.frombuffer(frame_rgb.tobytes(), frame_rgb.shape[1::-1], "RGB")
    screen.blit(frame_pygame, (SCREEN_WIDTH - 220, 20))

    pygame.display.flip()
    clock.tick(60)

# Clean up
cap.release()
cv2.destroyAllWindows()
pygame.quit()

if game_to_switch_to:
    print(f"正在切换到 {game_to_switch_to}...")
    try:
        # Use sys.executable to ensure the same python interpreter is used
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), game_to_switch_to)
        subprocess.run([sys.executable, script_path], check=True)
    except FileNotFoundError:
        print(f"错误: '{script_path}' 未找到。无法启动下一个游戏。")
    except subprocess.CalledProcessError as e:
        print(f"执行 '{game_to_switch_to}' 时出错: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")