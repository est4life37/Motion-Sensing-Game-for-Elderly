import cv2
import numpy as np
import pygame
import sys
import random
import mediapipe as mp
from pygame.locals import *
import os
import io
from PIL import Image, ImageDraw, ImageFont

# 解决中文显示问题（跨平台支持）
def create_text_image(text, font_size, color, bg_color=None):
    """创建包含中文文本的图像，支持多平台"""
    possible_fonts = [
        # macOS 字体
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        # Windows 字体
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        # Linux 字体
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
        "/Library/Fonts/Arial Unicode.ttf"
    ]
    
    font = None
    for font_path in possible_fonts:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue
    
    if font is None:
        font = ImageFont.load_default()
    
    # 计算文本大小
    test_image = Image.new("RGB", (1, 1))
    test_draw = ImageDraw.Draw(test_image)
    bbox = test_draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    
    # 添加内边距
    padding = 10
    width += padding * 2
    height += padding * 2
    
    # 创建图像
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((padding, padding), text, font=font, fill=color)
    
    # 转换为Pygame图像
    byte_io = io.BytesIO()
    image.save(byte_io, format="PNG")
    byte_io.seek(0)
    return pygame.image.load(byte_io)

# 加载自定义药材图片
def load_custom_image(image_path, target_size=(150, 150)):
    """加载药材图片，图片缺失时显示占位符"""
    try:
        # 尝试加载图片
        img = Image.open(image_path)
        img = img.convert("RGBA")
        img = img.resize(target_size, Image.LANCZOS)
        
        # 转换为Pygame图像
        byte_io = io.BytesIO()
        img.save(byte_io, format="PNG")
        byte_io.seek(0)
        return pygame.image.load(byte_io)
    except Exception as e:
        print(f"加载图片错误: {e} - 路径: {image_path}")
        
        # 创建占位符
        placeholder = pygame.Surface(target_size, pygame.SRCALPHA)
        placeholder.fill((200, 200, 200, 128))  # 浅灰色半透明背景
        
        # 尝试使用系统字体
        try:
            # 优先尝试中文字体
            font = pygame.font.SysFont(["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "Arial"], 24)
            text_surface = font.render("图片缺失", True, (100, 100, 100))
        except:
            # fallback方案
            font = pygame.font.SysFont(None, 24)
            text_surface = font.render("No Image", True, (100, 100, 100))
        
        # 将文本居中放置
        text_rect = text_surface.get_rect(center=(target_size[0]//2, target_size[1]//2))
        placeholder.blit(text_surface, text_rect)
        
        return placeholder

# 初始化pygame
pygame.init()

# 设置窗口
WIDTH, HEIGHT = 1280, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("中医药学习")

# 颜色定义
BACKGROUND = (240, 250, 240)
TEXT_COLOR = (50, 110, 50)
HIGHLIGHT = (80, 160, 80)
BUTTON_COLOR = (110, 190, 110)
BUTTON_HOVER = (130, 210, 130)
CORRECT_COLOR = (50, 180, 50)
WRONG_COLOR = (180, 50, 50)
GESTURE_HINT_COLOR = (50, 110, 180)

# 创建文本图像
title_image = create_text_image("中医药学习", 40, TEXT_COLOR)
subtitle_image = create_text_image("通过手势识别学习中医药知识", 20, (100, 150, 100))
# 修改提示文字：将"握拳"改为"张开手掌"
hint_image = create_text_image("比耶查看详情，张开手掌切换下一个药材", 50, (120, 160, 120))
start_hint_image = create_text_image("请确保摄像头已连接，点击任意位置开始", 20, (100, 150, 100))
test_start_image = create_text_image("已学习30种药材，准备开始测试！", 30, TEXT_COLOR)
# 修改测试提示文字：比耶改为张开手掌
test_hint_image = create_text_image("1-4数字手势选择答案，张开手掌手势进入下一题", 20, GESTURE_HINT_COLOR)

# 中医药知识库
herbs = [
    {
        "name": "人参", 
        "category": "补气药", 
        "effect": "大补元气，复脉固脱，补脾益肺，生津安神", 
        "usage": "煎服，3-9克",
        "image_path": "renshen.jpg"
    },
    {
        "name": "黄芪", 
        "category": "补气药", 
        "effect": "补气固表，利尿托毒，排脓，敛疮生肌", 
        "usage": "煎服，9-30克",
        "image_path": "huangqi.jpg"
    },
    {
        "name": "当归", 
        "category": "补血药", 
        "effect": "补血活血，调经止痛，润肠通便", 
        "usage": "煎服，6-12克",
        "image_path": "danggui.jpg"
    },
    {
        "name": "枸杞", 
        "category": "补阴药", 
        "effect": "滋补肝肾，益精明目", 
        "usage": "煎服，6-12克",
        "image_path": "gouqi.jpg"
    },
    {
        "name": "金银花", 
        "category": "清热解毒药", 
        "effect": "清热解毒，疏散风热", 
        "usage": "煎服，6-15克",
        "image_path": "jinyinhua.jpeg"
    },
    {
        "name": "茯苓", 
        "category": "利水渗湿药", 
        "effect": "利水渗湿，健脾宁心", 
        "usage": "煎服，9-15克",
        "image_path": "fuling.jpeg"
    },
    {
        "name": "陈皮", 
        "category": "理气药", 
        "effect": "理气健脾，燥湿化痰", 
        "usage": "煎服，3-9克",
        "image_path": "chenpi.jpeg"
    },
    {
        "name": "三七", 
        "category": "止血药", 
        "effect": "散瘀止血，消肿定痛", 
        "usage": "研末吞服，1-3克",
        "image_path": "sanqi.jpeg"
    },
    {
        "name": "甘草", 
        "category": "补气药", 
        "effect": "补脾益气，清热解毒，祛痰止咳，缓急止痛，调和诸药", 
        "usage": "煎服，2-10克",
        "image_path": "gancao.jpg"
    },
    {
        "name": "川芎", 
        "category": "活血止痛药", 
        "effect": "活血行气，祛风止痛", 
        "usage": "煎服，3-9克",
        "image_path": "chuanxiong.jpeg"
    },
    {
        "name": "白术", 
        "category": "补气药", 
        "effect": "健脾益气，燥湿利水，止汗，安胎", 
        "usage": "煎服，6-12克",
        "image_path": "baizhu.jpeg"
    },
    {
        "name": "黄连", 
        "category": "清热燥湿药", 
        "effect": "清热燥湿，泻火解毒", 
        "usage": "煎服，2-5克",
        "image_path": "huanglian.jpeg"
    },
    {
        "name": "地黄", 
        "category": "补血药", 
        "effect": "鲜地黄：清热生津，凉血止血；生地黄：清热凉血，养阴生津", 
        "usage": "煎服，10-15克",
        "image_path": "dihuang.jpeg"
    },
    {
        "name": "麦冬", 
        "category": "补阴药", 
        "effect": "养阴生津，润肺清心", 
        "usage": "煎服，6-12克",
        "image_path": "maidong.jpg"
    },
    {
        "name": "丹参", 
        "category": "活血调经药", 
        "effect": "活血祛瘀，通经止痛，清心除烦，凉血消痈", 
        "usage": "煎服，10-15克",
        "image_path": "danshen.jpeg"
    }
]

# 加载药材图片
for herb in herbs:
    herb["image"] = load_custom_image(herb["image_path"], (150, 150))

# 初始化MediaPipe手部识别
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,  # 降低检测置信度阈值，更容易检测
    min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# 初始化摄像头
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("无法打开摄像头！")
    camera_error_img = create_text_image("摄像头连接失败", 24, (200, 50, 50))
else:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 20)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 40)
    camera_error_img = None

# 游戏状态管理
class GameState:
    def __init__(self):
        self.current_herb = random.choice(herbs)
        self.learned_count = 0  # 已学习药材数量
        self.learned_herbs = []  # 存储已学习的药材
        self.score = 0  # 学习进度计数
        self.show_info = False
        self.hand_position = (0, 0)
        self.hand_gesture = "未检测到手势"
        self.camera_frame = None
        self.gesture_cooldown = 0
        self.window_size = (WIDTH, HEIGHT)
        self.in_test = False  # 是否处于测试状态
        self.test_questions = []  # 测试题目
        self.current_question = 0  # 当前问题索引
        self.test_score = 0  # 测试得分
        self.selected_answer = None  # 用户选择的答案
        self.test_completed = False  # 测试是否完成
        self.test_gesture_cooldown = 0  # 测试模式下的手势冷却
        self.music_paused = False  # 音乐是否暂停

game_state = GameState()

# 按钮类
class Button:
    def __init__(self, x, y, width, height, text, action=None, answer_index=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.answer_index = answer_index  # 用于测试选项
        self.hovered = False
        self.text_image = create_text_image(text, 24, (255, 255, 255))
        self.color = BUTTON_COLOR
        
    def draw(self, surface):
        color = BUTTON_HOVER if self.hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, HIGHLIGHT, self.rect, 3, border_radius=8)
        text_rect = self.text_image.get_rect(center=self.rect.center)
        surface.blit(self.text_image, text_rect)
        
    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        
    def handle_event(self, event):
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.action:
                    self.action()
                return True, self.answer_index
        return False, None

# 生成测试题目
def generate_test_questions():
    questions = []
    # 确保有足够的学习记录
    available_herbs = game_state.learned_herbs if len(game_state.learned_herbs) >= 5 else herbs
    
    # 生成8个问题
    for _ in range(8):
        # 随机选择一个药材作为问题主体
        target_herb = random.choice(available_herbs)
        
        # 随机选择问题类型
        question_type = random.choice(["effect", "category", "usage"])
        
        # 生成问题和正确答案
        if question_type == "effect":
            question_text = f"{target_herb['name']}的功效是什么？"
            correct_answer = target_herb["effect"]
        elif question_type == "category":
            question_text = f"{target_herb['name']}属于哪类药材？"
            correct_answer = target_herb["category"]
        else:  # usage
            question_text = f"{target_herb['name']}的正确用法是？"
            correct_answer = target_herb["usage"]
        
        # 生成干扰选项
        options = [correct_answer]
        while len(options) < 4:
            # 选择其他药材的同类型属性作为干扰项
            other_herb = random.choice(herbs)
            if other_herb != target_herb:
                distractor = other_herb[question_type]
                if distractor not in options:
                    options.append(distractor)
        
        # 打乱选项顺序
        random.shuffle(options)
        correct_index = options.index(correct_answer)
        
        # 添加到问题列表
        questions.append({
            "text": question_text,
            "options": options,
            "correct_index": correct_index,
            "target_herb": target_herb
        })
    
    return questions

# 按钮动作
def next_herb():
    # 记录已学习的药材
    if game_state.current_herb not in game_state.learned_herbs:
        game_state.learned_herbs.append(game_state.current_herb)
    # 选择新药材
    game_state.current_herb = random.choice(herbs)
    game_state.show_info = False
    game_state.learned_count += 1  # 增加学习计数
    game_state.gesture_cooldown = 20
    
    # 检查是否已学习30种药材，准备测试
    if game_state.learned_count >= 30 and not game_state.in_test:
        game_state.test_questions = generate_test_questions()
        game_state.in_test = True
        game_state.current_question = 0
        game_state.test_score = 0
        game_state.test_completed = False

def toggle_info():
    game_state.show_info = not game_state.show_info
    game_state.gesture_cooldown = 20

def next_question():
    # 检查是否回答了当前问题
    if game_state.selected_answer is not None:
        # 检查答案是否正确
        current_q = game_state.test_questions[game_state.current_question]
        if game_state.selected_answer == current_q["correct_index"]:
            game_state.test_score += 1
        
        # 进入下一题或完成测试
        game_state.current_question += 1
        game_state.selected_answer = None
        
        # 检查是否完成所有问题
        if game_state.current_question >= len(game_state.test_questions):
            game_state.test_completed = True

def return_to_learning():
    game_state.in_test = False
    game_state.learned_count = 0  # 重置计数，允许重新积累学习

def toggle_music():
    """切换背景音乐播放状态"""
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.pause()
        game_state.music_paused = True
    else:
        pygame.mixer.music.unpause()
        game_state.music_paused = False

# 更新学习界面按钮位置
def update_buttons_position():
    w, h = game_state.window_size
    return [
        Button(w - 180, h - 250, 160, 50, "下一个药材", next_herb),
        Button(w - 180, h - 350, 160, 50, "药材详情", toggle_info),
    ]

# 更新测试界面按钮
def get_test_buttons():
    buttons = []
    w, h = game_state.window_size
    
    if game_state.test_completed:
        # 测试完成页面按钮
        buttons.append(Button(w//2 - 80, h - 100, 160, 50, "返回学习", return_to_learning))
    else:
        # 问题选项按钮
        current_q = game_state.test_questions[game_state.current_question]
        for i, option in enumerate(current_q["options"]):
            y_pos = 300 + i * 70
            # 如果已选择答案，高亮显示正确和错误答案
            if game_state.selected_answer is not None:
                btn = Button(w//2 - 300, y_pos, 600, 50, option, None, i)
                if i == game_state.selected_answer:
                    if i == current_q["correct_index"]:
                        btn.color = CORRECT_COLOR
                    else:
                        btn.color = WRONG_COLOR
                elif i == current_q["correct_index"]:
                    btn.color = CORRECT_COLOR
                buttons.append(btn)
            else:
                buttons.append(Button(w//2 - 300, y_pos, 600, 50, option, None, i))
        
        # 下一题按钮（仅在选择答案后启用）
        if game_state.selected_answer is not None:
            buttons.append(Button(w//2 - 80, h - 100, 160, 50, "下一题", next_question))
    
    return buttons

buttons = update_buttons_position()

# 绘制药草卡片
def draw_herb_card():
    w, h = game_state.window_size
    card_rect = pygame.Rect(40, 120, w - 300, h - 200)
    pygame.draw.rect(screen, (255, 255, 255), card_rect, border_radius=12)
    pygame.draw.rect(screen, HIGHLIGHT, card_rect, 3, border_radius=12)
    
    # 显示学习进度
    progress_text = f"学习进度: {game_state.learned_count}/30"
    progress_image = create_text_image(progress_text, 20, TEXT_COLOR)
    screen.blit(progress_image, (card_rect.left + 20, card_rect.top + 10))
    
    # 绘制药草名称
    name_image = create_text_image(game_state.current_herb["name"], 32, TEXT_COLOR)
    name_rect = name_image.get_rect(center=(card_rect.centerx, card_rect.top + 50))
    screen.blit(name_image, name_rect)
    
    # 绘制药材图片
    herb_image = game_state.current_herb["image"]
    image_rect = herb_image.get_rect(center=(card_rect.centerx, card_rect.top + 150))
    screen.blit(herb_image, image_rect)
    
    # 绘制分类、功效和用法
    category_text = f"分类: {game_state.current_herb['category']}"
    category_image = create_text_image(category_text, 24, TEXT_COLOR)
    screen.blit(category_image, (card_rect.left + 40, card_rect.top + 250))
    
    effect_text = f"功效: {game_state.current_herb['effect']}"
    effect_image = create_text_image(effect_text, 24, TEXT_COLOR)
    screen.blit(effect_image, (card_rect.left + 40, card_rect.top + 290))
    
    usage_text = f"用法: {game_state.current_herb['usage']}"
    usage_image = create_text_image(usage_text, 24, TEXT_COLOR)
    screen.blit(usage_image, (card_rect.left + 40, card_rect.top + 330))
    
    # 绘制提示
    hint_rect = hint_image.get_rect(center=(card_rect.centerx, card_rect.bottom - 30))
    screen.blit(hint_image, hint_rect)
    
    # 绘制详情信息
    if game_state.show_info:
        info_rect = pygame.Rect(card_rect.left + 40, card_rect.top + 370, 
                              card_rect.width - 80, 80)
        pygame.draw.rect(screen, (240, 255, 240), info_rect, border_radius=8)
        pygame.draw.rect(screen, (200, 230, 200), info_rect, 2, border_radius=8)
        
        info_text = f"{game_state.current_herb['name']}是中医常用药材，具有悠久历史，广泛应用于各种方剂中。"
        info_image = create_text_image(info_text, 18, TEXT_COLOR)
        screen.blit(info_image, (info_rect.left + 10, info_rect.top + 10))

# 绘制测试界面
def draw_test_screen():
    w, h = game_state.window_size
    
    # 绘制标题
    title_rect = title_image.get_rect(center=(w//2, 40))
    screen.blit(title_image, title_rect)
    
    # 绘制测试进度
    progress_text = f"测试进度: {game_state.current_question + 1}/{len(game_state.test_questions)}"
    progress_image = create_text_image(progress_text, 24, TEXT_COLOR)
    screen.blit(progress_image, (40, 40))
    
    if game_state.test_completed:
        # 绘制测试结果
        result_title = create_text_image("测试完成！", 36, TEXT_COLOR)
        result_rect = result_title.get_rect(center=(w//2, h//2 - 100))
        screen.blit(result_title, result_rect)
        
        score_text = f"你的得分: {game_state.test_score}/{len(game_state.test_questions)}"
        score_image = create_text_image(score_text, 32, TEXT_COLOR)
        score_rect = score_image.get_rect(center=(w//2, h//2 - 40))
        screen.blit(score_image, score_rect)
        
        # 根据得分显示评价
        percentage = (game_state.test_score / len(game_state.test_questions)) * 100
        if percentage >= 90:
            comment = "太棒了，你对中医药知识掌握得非常好！"
        elif percentage >= 70:
            comment = "不错，继续努力可以掌握得更好！"
        elif percentage >= 50:
            comment = "还可以，建议再复习一下学过的内容。"
        else:
            comment = "需要多复习哦，继续加油！"
        
        comment_image = create_text_image(comment, 24, TEXT_COLOR)
        comment_rect = comment_image.get_rect(center=(w//2, h//2 + 40))
        screen.blit(comment_image, comment_rect)
    else:
        # 绘制当前问题
        if game_state.current_question < len(game_state.test_questions):
            current_q = game_state.test_questions[game_state.current_question]
            question_image = create_text_image(current_q["text"], 28, TEXT_COLOR)
            question_rect = question_image.get_rect(center=(w//2, 90))
            screen.blit(question_image, question_rect)
            
            # 显示药材图片作为提示
            herb_image = current_q["target_herb"]["image"]
            image_rect = herb_image.get_rect(center=(w//2, 230))
            screen.blit(herb_image, image_rect)
            
            # 绘制手势提示
            hint_rect = test_hint_image.get_rect(center=(w//2, h - 150))
            screen.blit(test_hint_image, hint_rect)
            
            # 显示当前识别的手势
            gesture_text = f"当前手势: {game_state.hand_gesture}"
            gesture_image = create_text_image(gesture_text, 20, GESTURE_HINT_COLOR)
            screen.blit(gesture_image, (w - gesture_image.get_width() - 40, 40))

# 绘制分数
def draw_score():
    w, _ = game_state.window_size
    score_text = f"已学习: {game_state.learned_count}"
    score_image = create_text_image(score_text, 30, TEXT_COLOR)
    screen.blit(score_image, (w - score_image.get_width() - 40, 40))

# 绘制摄像头画面
def draw_camera_frame():
    if not cap.isOpened():
        if camera_error_img:
            error_rect = pygame.Rect(WIDTH - 260, 40, 240, 180)
            pygame.draw.rect(screen, (255, 240, 240), error_rect)
            pygame.draw.rect(screen, (200, 100, 100), error_rect, 2)
            screen.blit(camera_error_img, 
                       (error_rect.centerx - camera_error_img.get_width()//2,
                        error_rect.centery - camera_error_img.get_height()//2))
        return
        
    if game_state.camera_frame is not None:
        try:
            frame = cv2.cvtColor(game_state.camera_frame, cv2.COLOR_BGR2RGB)
            frame = cv2.flip(frame, 1)
            frame = np.rot90(frame)
            frame = pygame.surfarray.make_surface(frame)
            
            w, _ = game_state.window_size
            cam_rect = pygame.Rect(w - 260, 40, 240, 180)
            pygame.draw.rect(screen, (0, 0, 0), cam_rect)
            screen.blit(frame, (w - 260, 40))
            
            # 显示手势提示
            if game_state.in_test:
                # 修改测试模式手势提示：比耶改为张开手掌
                test_gest_text = "手势控制: 1-4选答案，张开手掌下一题"
            else:
                test_gest_text = "手势控制: 比耶详情，张开手掌下一个"
                
            gesture_image = create_text_image(test_gest_text, 16, (255, 255, 255))
            screen.blit(gesture_image, (w - 260, 20))
        except Exception as e:
            print(f"摄像头绘制错误: {e}")
            error_rect = pygame.Rect(WIDTH - 260, 40, 240, 180)
            pygame.draw.rect(screen, (255, 0, 0), error_rect)
            error_image = create_text_image("摄像头错误", 20, (255, 255, 255))
            error_image_rect = error_image.get_rect(center=error_rect.center)
            screen.blit(error_image, error_image_rect)

# 计算两点之间的欧氏距离
def distance(point1, point2):
    return np.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)** 2)

# 处理摄像头帧和手势识别
def process_camera_frame():
    if not cap.isOpened():
        return
        
    try:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            return
        
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                h, w, _ = frame.shape
                game_state.hand_position = (int(wrist.x * w), int(wrist.y * h))
                
                # 获取手指关键点
                landmarks = hand_landmarks.landmark
                thumb_tip = landmarks[mp_hands.HandLandmark.THUMB_TIP]
                index_tip = landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                middle_tip = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                ring_tip = landmarks[mp_hands.HandLandmark.RING_FINGER_TIP]
                pinky_tip = landmarks[mp_hands.HandLandmark.PINKY_TIP]
                
                # 获取指节位置（用于判断手指是否伸直）
                index_mcp = landmarks[mp_hands.HandLandmark.INDEX_FINGER_MCP]  # 掌指关节
                index_pip = landmarks[mp_hands.HandLandmark.INDEX_FINGER_PIP]  # 近端指间关节
                middle_mcp = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                middle_pip = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
                ring_mcp = landmarks[mp_hands.HandLandmark.RING_FINGER_MCP]
                ring_pip = landmarks[mp_hands.HandLandmark.RING_FINGER_PIP]
                pinky_mcp = landmarks[mp_hands.HandLandmark.PINKY_MCP]
                pinky_pip = landmarks[mp_hands.HandLandmark.PINKY_PIP]
                
                # 改进的手指伸直判断函数，增加容错率
                def is_finger_extended(tip, mcp, pip):
                    # 允许一定的误差范围，使判断更灵活
                    return tip.y < pip.y + 0.02 and pip.y < mcp.y + 0.02
                
                index_extended = is_finger_extended(index_tip, index_mcp, index_pip)
                middle_extended = is_finger_extended(middle_tip, middle_mcp, middle_pip)
                ring_extended = is_finger_extended(ring_tip, ring_mcp, ring_pip)
                pinky_extended = is_finger_extended(pinky_tip, pinky_mcp, pinky_pip)
                
                # 改进的拇指伸直判断
                thumb_base = landmarks[mp_hands.HandLandmark.THUMB_MCP]
                thumb_extended = distance(thumb_tip, thumb_base) > 0.1  # 基于拇指长度判断
                
                # 计算食指和中指之间的距离（用于比耶手势判断）
                index_middle_distance = distance(index_tip, middle_tip)
                # 计算食指长度（用于归一化距离）
                index_length = distance(index_tip, index_mcp)
                
                # 识别手势
                gesture = "其他手势"
                
                # 检测张开手掌手势（所有手指都伸直）
                if (index_extended and middle_extended and 
                    ring_extended and pinky_extended and thumb_extended):
                    gesture = "张开手掌"
                
                # 检测比耶手势
                elif (index_extended and middle_extended and 
                      not ring_extended and not pinky_extended and
                      index_middle_distance > 0.5 * index_length):  # 调整阈值
                    gesture = "比耶"
                
                # 数字2手势
                elif (index_extended and middle_extended and 
                      not ring_extended and not pinky_extended and
                      index_middle_distance <= 0.5 * index_length):
                    gesture = "数字2"
                
                # 数字1：只有食指伸直
                elif index_extended and not middle_extended and not ring_extended and not pinky_extended:
                    gesture = "数字1"
                
                # 数字3：食指、中指和无名指伸直
                elif index_extended and middle_extended and ring_extended and not pinky_extended:
                    gesture = "数字3"
                
                # 数字4：食指、中指、无名指和小指伸直
                elif index_extended and middle_extended and ring_extended and pinky_extended:
                    gesture = "数字4"
                
                game_state.hand_gesture = gesture
                
                # 根据当前模式处理手势
                if game_state.in_test and not game_state.test_completed:
                    # 测试模式下的手势处理
                    if game_state.test_gesture_cooldown <= 0:
                        # 数字手势选择答案（1-4对应选项0-3）
                        if gesture.startswith("数字"):
                            num = int(gesture.replace("数字", ""))
                            if 1 <= num <= 4 and game_state.selected_answer is None:
                                game_state.selected_answer = num - 1  # 转换为0-based索引
                                game_state.test_gesture_cooldown = 30
                        # 修改：张开手掌手势进入下一题（原为比耶）
                        elif gesture == "张开手掌" and game_state.selected_answer is not None:
                            next_question()
                            game_state.test_gesture_cooldown = 30
                else:
                    # 学习模式下的手势处理
                    if game_state.gesture_cooldown <= 0:
                        # 比耶手势查看详情
                        if gesture == "比耶":
                            toggle_info()
                            game_state.gesture_cooldown = 20
                        # 张开手掌手势切换下一个药材
                        elif gesture == "张开手掌":
                            next_herb()
                            game_state.gesture_cooldown = 20
        
        game_state.camera_frame = frame
    except Exception as e:
        print(f"摄像头处理错误: {e}")

# 初始化背景音乐
def init_background_music():
    """初始化背景音乐"""
    try:
        # 尝试加载背景音乐
        pygame.mixer.music.load("nb666.mp3")
        pygame.mixer.music.play(-1)  # -1表示循环播放
        pygame.mixer.music.set_volume(0.5)  # 设置音量
        return True
    except Exception as e:
        print(f"无法加载背景音乐: {e}")
        return False

# 主游戏循环
clock = pygame.time.Clock()
running = True
show_welcome = True

# 初始化混音器并加载背景音乐
pygame.mixer.init()
music_loaded = init_background_music()

while running:
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        elif event.type == MOUSEMOTION:
            if game_state.in_test:
                test_buttons = get_test_buttons()
                for button in test_buttons:
                    button.check_hover(event.pos)
            else:
                for button in buttons:
                    button.check_hover(event.pos)
        elif event.type == MOUSEBUTTONDOWN:
            if game_state.in_test:
                test_buttons = get_test_buttons()
                for button in test_buttons:
                    handled, answer_idx = button.handle_event(event)
                    if handled and answer_idx is not None:
                        game_state.selected_answer = answer_idx
                        break
            else:
                for button in buttons:
                    if button.handle_event(event)[0]:
                        break
                if show_welcome:
                    show_welcome = False
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                running = False
            if show_welcome:
                show_welcome = False
            # 添加空格键控制音乐播放/暂停
            elif event.key == K_SPACE:
                toggle_music()
        elif event.type == VIDEORESIZE:
            game_state.window_size = (event.w, event.h)
            buttons = update_buttons_position()
    
    process_camera_frame()
    
    # 更新冷却时间
    if game_state.gesture_cooldown > 0:
        game_state.gesture_cooldown -= 1
    if game_state.test_gesture_cooldown > 0:
        game_state.test_gesture_cooldown -= 1
    
    screen.fill(BACKGROUND)
    
    if show_welcome:
        w, h = game_state.window_size
        title_rect = title_image.get_rect(center=(w//2, h//2 - 80))
        screen.blit(title_image, title_rect)
        
        subtitle_rect = subtitle_image.get_rect(center=(w//2, h//2 - 20))
        screen.blit(subtitle_image, subtitle_rect)
        
        start_hint_rect = start_hint_image.get_rect(center=(w//2, h//2 + 80))
        screen.blit(start_hint_image, start_hint_rect)
        
        # 在欢迎界面显示音乐状态
        if music_loaded:
            music_status = "背景音乐已加载" if not game_state.music_paused else "背景音乐已暂停"
            music_image = create_text_image(music_status, 20, (100, 150, 100))
            music_rect = music_image.get_rect(center=(w//2, h//2 + 120))
            screen.blit(music_image, music_rect)
    else:
        if game_state.in_test:
            # 显示测试界面
            draw_test_screen()
            test_buttons = get_test_buttons()
            for button in test_buttons:
                button.draw(screen)
        else:
            # 显示学习界面
            w, h = game_state.window_size
            title_rect = title_image.get_rect(center=(w//2, 40))
            screen.blit(title_image, title_rect)
            
            subtitle_rect = subtitle_image.get_rect(center=(w//2, 80))
            screen.blit(subtitle_image, subtitle_rect)
            
            draw_herb_card()
            draw_score()
            draw_camera_frame()
            
            for button in buttons:
                button.draw(screen)
    
    pygame.display.flip()
    clock.tick(30)

# 清理资源
if cap.isOpened():
    cap.release()
hands.close()
pygame.quit()
sys.exit()