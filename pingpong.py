import cv2
import mediapipe as mp
import pygame
import sys
import os
import random
import time
import math
import numpy as np

# ======================
# 1. 初始化 MediaPipe 姿势检测
# ======================
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# ======================
# 2. 初始化 PyGame 乒乓球游戏
# ======================
pygame.init()
pygame.mixer.init()

# 游戏窗口
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("体感乒乓球游戏（头部控制球拍）")

# 解决中文显示问题
def get_chinese_font(size=36):
    font_paths = [
        'msyh.ttc', 'simhei.ttf',
        'C:/Windows/Fonts/msyh.ttc',
        '/System/Library/Fonts/STHeiti Medium.ttc'
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except:
                continue
    return pygame.font.Font(None, size)

# 加载音效
def load_sound(filename):
    try:
        return pygame.mixer.Sound(filename)
    except:
        print(f"无法加载音效文件: {filename}")
        return None

hit_sound = load_sound("pingpong.mp3")
lose_sound = load_sound("lose.wav")
win_sound = load_sound("applause.mp3")
obstacle_hit_sound = load_sound("pingpong.mp3")
wall_hit_sound = load_sound("pingpong.mp3")

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
TRANSPARENT = (0, 0, 0, 150)

# 加载游戏图片资源
try:
    # 加载背景图片（乒乓球桌）
    background_img = pygame.image.load('PingPangDesk.png')
    background_img = pygame.transform.scale(background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
    
    # 加载乒乓球拍图片
    paddle_img = pygame.image.load('PingPangPai.png')
    original_paddle_width = paddle_img.get_width()
    original_paddle_height = paddle_img.get_height()
    
    # 设置球拍在游戏中的尺寸
    PADDLE_WIDTH = 250
    PADDLE_HEIGHT = int(original_paddle_height * (PADDLE_WIDTH / original_paddle_width))
    paddle_img = pygame.transform.scale(paddle_img, (PADDLE_WIDTH, PADDLE_HEIGHT))
    
    # 加载乒乓球图片
    ball_img = pygame.image.load('PingPangBall.png')
    original_ball_size = ball_img.get_width()
    BALL_SIZE = 40
    ball_img = pygame.transform.scale(ball_img, (BALL_SIZE, BALL_SIZE))
    
    # 计算碰撞检测用的球拍矩形
    PADDLE_COLLISION_WIDTH = PADDLE_WIDTH - 40
    PADDLE_COLLISION_HEIGHT = 9
    
    # 加载障碍物图片
    obstacle_img = pygame.image.load('obstacle.png') if os.path.exists('obstacle.png') else None
    if obstacle_img:
        OBSTACLE_WIDTH = 120  # 障碍物宽度
        OBSTACLE_HEIGHT = 40  # 障碍物高度
        obstacle_img = pygame.transform.scale(obstacle_img, (OBSTACLE_WIDTH, OBSTACLE_HEIGHT))
    
    # 加载破坏特效图片
    explosion_img = pygame.image.load('explosion.png') if os.path.exists('explosion.png') else None
    if explosion_img:
        EXPLOSION_SIZE = 100
        explosion_img = pygame.transform.scale(explosion_img, (EXPLOSION_SIZE, EXPLOSION_SIZE))
    
except pygame.error as e:
    print(f"无法加载图片资源: {e}")
    print("请确保以下图片文件与脚本在同一目录下:")
    print("- PingPangDesk.png (乒乓球桌背景)")
    print("- PingPangPai.png (乒乓球拍)")
    print("- PingPangBall.png (乒乓球)")
    print("- obstacle.png (障碍物，可选)")
    print("- explosion.png (破坏特效，可选)")
    pygame.quit()
    sys.exit()

# 游戏设置
PADDLE_SPEED = 8
MAX_HEALTH = 5
INITIAL_BALL_SPEED = 10
MAX_BALL_SPEED = 20

# 球拍位置
paddle_x = (SCREEN_WIDTH - PADDLE_WIDTH) // 2
paddle_y = SCREEN_HEIGHT - 300

# 球的初始位置和速度
ball_x = SCREEN_WIDTH // 2
ball_y = SCREEN_HEIGHT // 2
ball_dx = INITIAL_BALL_SPEED * (1 if random.random() > 0.5 else -1)
ball_dy = -INITIAL_BALL_SPEED

# 定义合理的击球区域
TABLE_TOP = 0
TABLE_BOTTOM = SCREEN_HEIGHT
TABLE_LEFT = 100
TABLE_RIGHT = SCREEN_WIDTH - 100

# 游戏状态
class GameState:
    INTRODUCTION = -1
    COUNTDOWN = 0
    PLAYING = 1
    GAME_OVER = 2
    VICTORY = 3

current_state = GameState.INTRODUCTION  # 初始状态为介绍
countdown_time = 3
countdown_start = 0
health = MAX_HEALTH
score = 0

# 球的历史位置（用于残影效果）
ball_history = []
MAX_HISTORY = 5

# 边缘闪烁效果
left_wall_flash = 0
right_wall_flash = 0
WALL_FLASH_DURATION = 10

# 击打反馈效果
hit_feedback = []
HIT_FEEDBACK_DURATION = 15

# 障碍物系统
class Obstacle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = OBSTACLE_WIDTH if obstacle_img else 120
        self.height = OBSTACLE_HEIGHT if obstacle_img else 40
        self.hits_remaining = 5
        self.hit_animation = 0
        self.destroy_animation = 0
    
    def draw(self, screen):
        if self.destroy_animation > 0:
            if explosion_img:
                for i in range(3):
                    offset_x = random.randint(-20, 20)
                    offset_y = random.randint(-20, 20)
                    screen.blit(explosion_img, 
                               (self.x + self.width//2 - EXPLOSION_SIZE//2 + offset_x, 
                                self.y + self.height//2 - EXPLOSION_SIZE//2 + offset_y))
            else:
                for i in range(10):
                    offset_x = random.randint(-30, 30)
                    offset_y = random.randint(-30, 30)
                    size = random.randint(5, 15)
                    color = (random.randint(200, 255), random.randint(100, 200), 0)
                    pygame.draw.circle(screen, color, 
                                     (self.x + self.width//2 + offset_x, 
                                      self.y + self.height//2 + offset_y), size)
            
            self.destroy_animation -= 1
            return
        
        if obstacle_img:
            screen.blit(obstacle_img, (self.x, self.y))
        else:
            color = (255, 165, 0) if self.hits_remaining == 2 else (255, 69, 0)
            pygame.draw.rect(screen, color, (self.x, self.y, self.width, self.height))
            
            font = get_chinese_font(24)
            text = font.render(str(self.hits_remaining), True, WHITE)
            screen.blit(text, (self.x + self.width // 2 - text.get_width() // 2, 
                              self.y + self.height // 2 - text.get_height() // 2))
        
        if self.hit_animation > 0:
            pygame.draw.rect(screen, YELLOW, (self.x, self.y, self.width, self.height), 5)
            self.hit_animation -= 1
    
    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
    
    def destroy(self):
        self.destroy_animation = 15
        if obstacle_hit_sound: obstacle_hit_sound.play()

# 生成横向铺满的障碍物
def generate_full_row_obstacles():
    obstacles = []
    fixed_height = TABLE_TOP + 100  # 固定高度距离顶部100像素
    obstacle_width = OBSTACLE_WIDTH if obstacle_img else 120
    obstacle_height = OBSTACLE_HEIGHT if obstacle_img else 40
    
    # 计算可以放置多少个障碍物
    num_obstacles = SCREEN_WIDTH // obstacle_width + 1
    
    for i in range(num_obstacles):
        x = i * obstacle_width
        # 确保障碍物不会超出屏幕右侧
        if x + obstacle_width > SCREEN_WIDTH:
            # 调整最后一个障碍物的宽度以刚好填满屏幕
            obstacle_width = SCREEN_WIDTH - x
        obstacles.append(Obstacle(x, fixed_height))
    
    return obstacles

obstacles = generate_full_row_obstacles()

# 弹窗类
class Popup:
    def __init__(self, title, message, button_text="确定"):
        self.width = 400
        self.height = 250
        self.x = (SCREEN_WIDTH - self.width) // 2
        self.y = (SCREEN_HEIGHT - self.height) // 2
        self.title = title
        self.message = message
        self.button_text = button_text
        self.button_rect = pygame.Rect(self.x + 150, self.y + 180, 100, 40)
        self.visible = False
    
    def draw(self, screen):
        if not self.visible:
            return
        
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill(TRANSPARENT)
        screen.blit(s, (0, 0))
        
        pygame.draw.rect(screen, WHITE, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 2)
        
        title_font = get_chinese_font(30)
        title_text = title_font.render(self.title, True, BLACK)
        screen.blit(title_text, (self.x + self.width // 2 - title_text.get_width() // 2, self.y + 30))
        
        message_font = get_chinese_font(24)
        message_lines = self.message.split('\n')
        for i, line in enumerate(message_lines):
            message_text = message_font.render(line, True, BLACK)
            screen.blit(message_text, (self.x + self.width // 2 - message_text.get_width() // 2, 
                                      self.y + 90 + i * 30))
        
        pygame.draw.rect(screen, (100, 100, 255), self.button_rect)
        pygame.draw.rect(screen, BLACK, self.button_rect, 2)
        button_font = get_chinese_font(20)
        button_text = button_font.render(self.button_text, True, WHITE)
        screen.blit(button_text, (self.button_rect.x + self.button_rect.width // 2 - button_text.get_width() // 2, 
                                 self.button_rect.y + self.button_rect.height // 2 - button_text.get_height() // 2))
    
    def check_click(self, pos):
        if self.visible and self.button_rect.collidepoint(pos):
            return True
        return False

# 创建弹窗实例
game_over_popup = Popup("游戏结束", f"最终得分: {score}")
victory_popup = Popup("胜利!", f"恭喜获胜!\n得分: {score}")

# 血条类
class HealthBar:
    def __init__(self, x, y, width, height, max_health):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.max_health = max_health
        self.current_health = max_health
        self.damage_animation = 0
    
    def draw(self, screen):
        pygame.draw.rect(screen, (50, 50, 50), (self.x, self.y, self.width, self.height))
        
        health_width = int((self.current_health / self.max_health) * self.width)
        pygame.draw.rect(screen, RED, (self.x, self.y, health_width, self.height))
        
        pygame.draw.rect(screen, WHITE, (self.x, self.y, self.width, self.height), 2)
        
        font = get_chinese_font(20)
        text = font.render(f"{self.current_health}/{self.max_health}", True, WHITE)
        screen.blit(text, (self.x + self.width + 10, self.y + self.height // 2 - text.get_height() // 2))
        
        if self.damage_animation > 0:
            pygame.draw.rect(screen, YELLOW, (self.x, self.y, self.width, self.height), 3)
            self.damage_animation -= 1
    
    def take_damage(self, amount=1):
        self.current_health = max(0, self.current_health - amount)
        self.damage_animation = 10

# 创建血条实例
health_bar = HealthBar(20, 60, 200, 20, MAX_HEALTH)

# 摄像头设置
CAM_WIDTH = TABLE_RIGHT - TABLE_LEFT
CAM_HEIGHT = TABLE_BOTTOM - TABLE_TOP
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

# 游戏介绍界面变量
introduction_start_time = 0
button_hover_start = 0
button_hover_duration = 3  # 需要停留3秒
button_rect = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 100, 200, 60)
dark_overlay_alpha = 180  # 初始暗化程度

clock = pygame.time.Clock()

# ======================
# 3. 主循环
# ======================
running = True
while running:
    # === 修复点1: 初始化变量作用域 ===
    hand_detected = False
    head_detected = False
    hand_pos = None
    head_pos = None

    # --- PyGame 事件处理 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            
            if current_state == GameState.GAME_OVER and game_over_popup.check_click(mouse_pos):
                current_state = GameState.INTRODUCTION
                introduction_start_time = pygame.time.get_ticks()
                health = MAX_HEALTH
                health_bar.current_health = MAX_HEALTH
                score = 0
                ball_x = SCREEN_WIDTH // 2
                ball_y = SCREEN_HEIGHT // 2
                ball_dx = INITIAL_BALL_SPEED * (1 if random.random() > 0.5 else -1)
                ball_dy = -INITIAL_BALL_SPEED
                obstacles = generate_full_row_obstacles()
                ball_history = []
                hit_feedback = []
                game_over_popup.visible = False
            
            elif current_state == GameState.VICTORY and victory_popup.check_click(mouse_pos):
                current_state = GameState.INTRODUCTION
                introduction_start_time = pygame.time.get_ticks()
                health = MAX_HEALTH
                health_bar.current_health = MAX_HEALTH
                score = 0
                ball_x = SCREEN_WIDTH // 2
                ball_y = SCREEN_HEIGHT // 2
                ball_dx = INITIAL_BALL_SPEED * (1 if random.random() > 0.5 else -1)
                ball_dy = -INITIAL_BALL_SPEED
                obstacles = generate_full_row_obstacles()
                ball_history = []
                hit_feedback = []
                victory_popup.visible = False

    # --- 1. 摄像头读取 + MediaPipe 检测 ---
    ret, frame = cap.read()
    if not ret:
        print("无法读取摄像头")
        break

    frame = cv2.resize(frame, (CAM_WIDTH, CAM_HEIGHT))
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # 根据游戏状态选择检测模式
    if current_state == GameState.INTRODUCTION:
        # 介绍界面使用手部检测
        result_hands = hands.process(frame_rgb)
        
        if result_hands and result_hands.multi_hand_landmarks:
            for hand_data in result_hands.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_data, mp_hands.HAND_CONNECTIONS)
                wrist = hand_data.landmark[0]
                h, w, _ = frame.shape
                wrist_x = int(wrist.x * w)
                wrist_y = int(wrist.y * h)
                cv2.circle(frame, (wrist_x, wrist_y), 10, (0, 255, 0), -1)
                
                # 手部位置提示文字
                cv2.putText(frame, f"Hand X: {wrist_x}, Y: {wrist_y}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # 记录手部位置用于按钮检测
                hand_detected = True
                mirror_wrist_x = CAM_WIDTH - wrist_x
                mapped_wrist_x = TABLE_LEFT + mirror_wrist_x
                mapped_wrist_y = TABLE_TOP + int(wrist_y * (TABLE_BOTTOM - TABLE_TOP) / h)
                hand_pos = (mapped_wrist_x, mapped_wrist_y)
    
    elif current_state == GameState.PLAYING:
        # 游戏中使用姿势检测（头部）
        result_pose = pose.process(frame_rgb)
        
        if result_pose and result_pose.pose_landmarks:
            mp_drawing.draw_landmarks(frame, result_pose.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            # 获取鼻尖位置（头部）
            nose = result_pose.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE]
            h, w, _ = frame.shape
            nose_x = int(nose.x * w)
            nose_y = int(nose.y * h)
            cv2.circle(frame, (nose_x, nose_y), 10, (255, 0, 0), -1)
            
            # 头部位置提示文字
            cv2.putText(frame, f"Head X: {nose_x}, Y: {nose_y}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            
            # 记录头部位置
            head_detected = True
            mirror_nose_x = CAM_WIDTH - nose_x
            mapped_nose_x = TABLE_LEFT + mirror_nose_x
            head_pos = (mapped_nose_x, nose_y)

    # === 修复点2: 调整条件判断顺序 ===
    if current_state == GameState.PLAYING and head_detected:
        # 使用头部位置控制球拍
        target_paddle_x = head_pos[0] - PADDLE_WIDTH // 2
        # 添加平滑移动
        paddle_x += (target_paddle_x - paddle_x) * 0.2
        # 确保球拍在边界内
        paddle_x = max(TABLE_LEFT, min(TABLE_RIGHT - PADDLE_WIDTH, paddle_x))
        
        # 头部位置校准提示
        if head_pos[0] < TABLE_LEFT or head_pos[0] > TABLE_RIGHT:
            cv2.putText(frame, "请将头部移动到中央区域", (w//2-150, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # --- 3. 游戏逻辑更新 ---
    if current_state == GameState.INTRODUCTION:
        if introduction_start_time == 0:
            introduction_start_time = pygame.time.get_ticks()
        
        # 检测手部是否在按钮上
        if hand_detected and hand_pos and button_rect.collidepoint(hand_pos):
            if button_hover_start == 0:
                button_hover_start = pygame.time.get_ticks()
            else:
                hover_duration = (pygame.time.get_ticks() - button_hover_start) / 1000
                if hover_duration >= button_hover_duration:
                    current_state = GameState.COUNTDOWN
                    countdown_start = pygame.time.get_ticks()
                    button_hover_start = 0
        else:
            button_hover_start = 0
    
    elif current_state == GameState.COUNTDOWN:
        if countdown_start == 0:
            countdown_start = pygame.time.get_ticks()
        
        elapsed = (pygame.time.get_ticks() - countdown_start) / 1000
        remaining = max(0, countdown_time - elapsed)
        
        # 计算暗化程度（逐渐变亮）
        if remaining > 0:
            progress = elapsed / countdown_time
            dark_overlay_alpha = int(180 * (1 - progress))  # 从180逐渐变为0
        
        if remaining <= 0:
            current_state = GameState.PLAYING
            dark_overlay_alpha = 0  # 完全恢复亮度
    
    elif current_state == GameState.PLAYING:
        ball_x += ball_dx
        ball_y += ball_dy
        
        ball_history.append((ball_x + BALL_SIZE//2, ball_y + BALL_SIZE//2))
        if len(ball_history) > MAX_HISTORY:
            ball_history.pop(0)

        if (ball_x <= TABLE_LEFT and ball_dx < 0):
            ball_dx = -ball_dx
            left_wall_flash = WALL_FLASH_DURATION
            if wall_hit_sound: wall_hit_sound.play()
            
        elif (ball_x >= TABLE_RIGHT - BALL_SIZE and ball_dx > 0):
            ball_dx = -ball_dx
            right_wall_flash = WALL_FLASH_DURATION
            if wall_hit_sound: wall_hit_sound.play()

        # 球掉出下边界 - 扣血
        if ball_y >= TABLE_BOTTOM:
            health_bar.take_damage()
            health -= 1
            ball_x = SCREEN_WIDTH // 2
            ball_y = SCREEN_HEIGHT // 2
            ball_dx = INITIAL_BALL_SPEED * (1 if random.random() > 0.5 else -1)
            ball_dy = -INITIAL_BALL_SPEED
            ball_history = []
            
            if lose_sound: lose_sound.play()
            
            # 检查游戏是否结束
            if health <= 0:
                current_state = GameState.GAME_OVER
                game_over_popup.message = f"最终得分: {score}"
                game_over_popup.visible = True

        # 球拍碰撞检测
        paddle_collision_rect = pygame.Rect(
            paddle_x + (PADDLE_WIDTH - PADDLE_COLLISION_WIDTH) // 2,
            paddle_y + 100,
            PADDLE_COLLISION_WIDTH,
            PADDLE_COLLISION_HEIGHT + 200
        )
        
        ball_rect = pygame.Rect(ball_x, ball_y, BALL_SIZE, BALL_SIZE)

        if ball_rect.colliderect(paddle_collision_rect) and ball_dy > 0:
            ball_dy = -ball_dy
            score += 1
            
            # 添加击打反馈效果
            hit_feedback.append({
                'x': ball_x + BALL_SIZE//2,
                'y': ball_y + BALL_SIZE//2,
                'timer': HIT_FEEDBACK_DURATION
            })
            
            # 根据击中位置调整反弹角度
            hit_pos = (ball_x + BALL_SIZE/2) - (paddle_x + PADDLE_WIDTH/2)
            ball_dx = hit_pos * 0.15
            
            # 限制最大速度
            ball_dx = max(-MAX_BALL_SPEED, min(MAX_BALL_SPEED, ball_dx))
            ball_dy = max(-MAX_BALL_SPEED, min(MAX_BALL_SPEED, ball_dy))
            
            # 播放击中音效
            if hit_sound: hit_sound.play()

        # 障碍物碰撞检测与解析
        ball_rect = pygame.Rect(ball_x, ball_y, BALL_SIZE, BALL_SIZE)
        obstacle_destroyed = False
        
        for obstacle in obstacles[:]:
            if obstacle.destroy_animation > 0:
                continue
                
            obstacle_rect = obstacle.get_rect()
            if ball_rect.colliderect(obstacle_rect):
                # 计算重叠深度
                delta_x = ball_rect.centerx - obstacle_rect.centerx
                delta_y = ball_rect.centery - obstacle_rect.centery
                
                combined_half_width = ball_rect.width / 2 + obstacle_rect.width / 2
                combined_half_height = ball_rect.height / 2 + obstacle_rect.height / 2
                
                overlap_x = combined_half_width - abs(delta_x)
                overlap_y = combined_half_height - abs(delta_y)

                # 找出穿透最小的轴，并沿该轴将球推出
                if overlap_x < overlap_y:
                    # 水平碰撞
                    ball_dx = -ball_dx
                    if delta_x > 0: ball_x += overlap_x # 从右侧推开
                    else: ball_x -= overlap_x # 从左侧推开
                else:
                    # 垂直碰撞
                    ball_dy = -ball_dy
                    if delta_y > 0: ball_y += overlap_y # 从下方推开
                    else: ball_y -= overlap_y # 从上方推开

                # 更新障碍物状态
                obstacle.hits_remaining -= 1
                obstacle.hit_animation = 10
                if obstacle.hits_remaining <= 0:
                    obstacle_destroyed = True
                    obstacle.destroy() # 触发销毁动画
                
                if obstacle_hit_sound: obstacle_hit_sound.play()
                
                # 添加击打反馈
                hit_feedback.append({
                    'x': ball_rect.centerx,
                    'y': ball_rect.centery,
                    'timer': HIT_FEEDBACK_DURATION
                })
                
                break # 每帧只处理一次碰撞，防止重复解析

        # 移除已完成销毁动画的障碍物
        obstacles = [obs for obs in obstacles if obs.hits_remaining > 0 or obs.destroy_animation > 0]

        # 检查胜利条件：打破任意一个障碍物
        if obstacle_destroyed:
            current_state = GameState.VICTORY
            victory_popup.message = f"恭喜获胜!\n得分: {score}"
            victory_popup.visible = True
            if win_sound: 
                win_sound.play()
                
                # 添加胜利特效
                for _ in range(50):
                    hit_feedback.append({
                        'x': random.randint(0, SCREEN_WIDTH),
                        'y': random.randint(0, SCREEN_HEIGHT),
                        'timer': random.randint(20, 40),
                        'color': (random.randint(200, 255), random.randint(200, 255), 0)
                    })

        # 更新击打反馈效果
        for feedback in hit_feedback[:]:
            feedback['timer'] -= 1
            if feedback['timer'] <= 0:
                hit_feedback.remove(feedback)

    # --- 4. 渲染 ---
    # 绘制背景
    screen.blit(background_img, (0, 0))
    
    # 绘制边缘闪烁效果
    if left_wall_flash > 0:
        pygame.draw.rect(screen, YELLOW, (TABLE_LEFT, TABLE_TOP, 10, TABLE_BOTTOM-TABLE_TOP))
        left_wall_flash -= 1
    
    if right_wall_flash > 0:
        pygame.draw.rect(screen, YELLOW, (TABLE_RIGHT-10, TABLE_TOP, 10, TABLE_BOTTOM-TABLE_TOP))
        right_wall_flash -= 1
    
    # 绘制球拍
    if current_state == GameState.PLAYING:
        screen.blit(paddle_img, (paddle_x, paddle_y))
    
    # 绘制球的残影效果
    if current_state == GameState.PLAYING:
        for i, (hx, hy) in enumerate(ball_history):
            alpha = int(255 * (i+1) / (MAX_HISTORY+1))
            temp_img = ball_img.copy()
            temp_img.fill((255, 255, 255, alpha), None, pygame.BLEND_RGBA_MULT)
            screen.blit(temp_img, (hx - BALL_SIZE//2, hy - BALL_SIZE//2))
    
    # 绘制球
    if current_state == GameState.PLAYING:
        screen.blit(ball_img, (ball_x, ball_y))
    
    # 绘制击打反馈效果
    for feedback in hit_feedback:
        radius = int(feedback['timer'] * 2)
        if radius > 0:
            color = feedback.get('color', YELLOW)
            pygame.draw.circle(screen, color, (int(feedback['x']), int(feedback['y'])), radius, 3)

    # 绘制障碍物
    for obstacle in obstacles:
        obstacle.draw(screen)

    # 绘制UI元素
    if current_state != GameState.INTRODUCTION:
        font = get_chinese_font(36)
        score_text = font.render(f"得分: {score}", True, WHITE)
        screen.blit(score_text, (20, 20))
        
        health_bar.draw(screen)
    
    # 绘制摄像头画面
    frame_surface = pygame.surfarray.make_surface(cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE))
    frame_surface = pygame.transform.flip(frame_surface, True, False)
    frame_surface = pygame.transform.scale(frame_surface, (200, 150))
    screen.blit(frame_surface, (SCREEN_WIDTH - 210, 10))
    pygame.draw.rect(screen, WHITE, (SCREEN_WIDTH - 210, 10, 200, 150), 2)

    # 游戏状态UI
    if current_state == GameState.INTRODUCTION:
        # 绘制暗化背景
        dark_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, dark_overlay_alpha))
        screen.blit(dark_overlay, (0, 0))
        
        # 绘制游戏介绍文字
        font_large = get_chinese_font(48)
        font_small = get_chinese_font(36)
        
        title_text = font_large.render("体感乒乓球游戏", True, WHITE)
        screen.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, SCREEN_HEIGHT//2 - 150))
        
        instruction_text = font_small.render("使用头部左右移动控制球拍，打破任意障碍物获胜", True, WHITE)
        screen.blit(instruction_text, (SCREEN_WIDTH//2 - instruction_text.get_width()//2, SCREEN_HEIGHT//2 - 50))
        
        # 绘制继续按钮
        button_color = (100, 200, 100) if button_hover_start > 0 else (100, 100, 255)
        pygame.draw.rect(screen, button_color, button_rect)
        pygame.draw.rect(screen, WHITE, button_rect, 3)
        
        # 绘制按钮文字
        button_font = get_chinese_font(30)
        if button_hover_start > 0:
            hover_duration = (pygame.time.get_ticks() - button_hover_start) / 1000
            progress = min(1.0, hover_duration / button_hover_duration)
            button_text = button_font.render(f"继续 ({int(progress * 100)}%)", True, WHITE)
            
            # 绘制进度条
            progress_width = int(button_rect.width * progress)
            pygame.draw.rect(screen, (50, 150, 50), 
                           (button_rect.x, button_rect.y + button_rect.height + 10, 
                            progress_width, 10))
        else:
            button_text = button_font.render("继续", True, WHITE)
        
        screen.blit(button_text, 
                  (button_rect.x + button_rect.width//2 - button_text.get_width()//2,
                   button_rect.y + button_rect.height//2 - button_text.get_height()//2))
        
        # 添加手部位置提示
        if hand_detected:
            # 绘制手部位置标记
            pygame.draw.circle(screen, (0, 255, 0), hand_pos, 15)
            
            # 绘制引导线
            pygame.draw.line(screen, (0, 255, 0), hand_pos, 
                           (button_rect.centerx, button_rect.centery), 2)
            
            # 添加文字提示
            hand_text = font_small.render(f"手部位置: X={hand_pos[0]}, Y={hand_pos[1]}", True, (0, 255, 0))
            screen.blit(hand_text, (SCREEN_WIDTH//2 - hand_text.get_width()//2, SCREEN_HEIGHT//2 + 50))
            
            # 添加手部引导动画
            pulse = abs(math.sin(pygame.time.get_ticks() / 200)) * 10
            pygame.draw.circle(screen, (255, 255, 255), hand_pos, 20 + int(pulse), 2)
    
    elif current_state == GameState.COUNTDOWN:
        if countdown_start > 0:
            elapsed = (pygame.time.get_ticks() - countdown_start) / 1000
            remaining = max(0, countdown_time - elapsed)
            
            # 绘制暗化背景（逐渐变亮）
            if dark_overlay_alpha > 0:
                dark_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                dark_overlay.fill((0, 0, 0, dark_overlay_alpha))
                screen.blit(dark_overlay, (0, 0))
            
            font = get_chinese_font(100)
            text = font.render(str(math.ceil(remaining)), True, WHITE)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 
                              SCREEN_HEIGHT // 2 - text.get_height() // 2))
    
    elif current_state == GameState.GAME_OVER:
        game_over_popup.draw(screen)
        
    elif current_state == GameState.VICTORY:
        victory_popup.draw(screen)

    pygame.display.flip()
    clock.tick(60)

# ======================
# 4. 清理
# ======================
cap.release()
hands.close()
pose.close()
pygame.quit()
sys.exit()