import asyncio
import platform
import pygame
import random
import time
import numpy as np

# Initialize pygame
pygame.init()
pygame.mixer.init()

# Constants
SCREEN_INFO = pygame.display.Info()
WIDTH, HEIGHT = SCREEN_INFO.current_w, SCREEN_INFO.current_h
GRID_SIZE = min(WIDTH, HEIGHT) // 30
GRID_WIDTH = WIDTH // GRID_SIZE
GRID_HEIGHT = (HEIGHT - GRID_SIZE * 2) // GRID_SIZE
BASE_FPS = 10
POWER_UP_DURATION = 5

# Colors
BACKGROUND = (255, 235, 243)
GRID_COLOR = (255, 204, 229)
SNAKE_HEAD = (76, 187, 23)
SNAKE_BODY1 = (102, 204, 0)
SNAKE_BODY2 = (153, 255, 51)
FOOD_COLORS = [
    (255, 0, 0),
    (0, 0, 255),
    (255, 51, 153)
]
POWER_UP_COLOR = (255, 215, 0)
SCORE_BG = (255, 255, 255)
SCORE_TEXT = (255, 102, 102)
GAME_OVER_BG = (255, 255, 255, 200)
GAME_OVER_TEXT = (255, 0, 0)
PAUSE_TEXT = (0, 0, 255)
LEVEL_UP_TEXT = (0, 255, 0)

# Create screen in full-screen mode
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Cartoon Snake Game")
clock = pygame.time.Clock()

# Fonts
font_name = 'comicsansms' if 'comicsansms' in pygame.font.get_fonts() else None
font_large = pygame.font.SysFont(font_name, max(48, HEIGHT // 20))
font_medium = pygame.font.SysFont(font_name, max(36, HEIGHT // 25))
font_small = pygame.font.SysFont(font_name, max(24, HEIGHT // 30))

# Sound Effects
def create_beep(frequency, duration):
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = 0.5 * np.sin(2 * np.pi * frequency * t)
    sound_array = (wave * 32767).astype(np.int16)
    stereo_array = np.column_stack((sound_array, sound_array))
    return pygame.mixer.Sound(stereo_array)

eat_sound = create_beep(600, 0.1)
game_over_sound = create_beep(200, 0.5)
pause_sound = create_beep(400, 0.2)
power_up_sound = create_beep(800, 0.15)
level_up_sound = create_beep(1000, 0.2)

# High Score Management (in-memory for Pyodide compatibility)
high_score = 0

class Snake:
    def __init__(self):
        self.positions = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
        self.direction = (1, 0)
        self.length = 1
        self.score = 0
        self.color_head = SNAKE_HEAD
        self.color_body1 = SNAKE_BODY1
        self.color_body2 = SNAKE_BODY2
        self.power_up_active = False
        self.power_up_end_time = 0
        
    def get_head_position(self):
        return self.positions[0]
        
    def update(self):
        head = self.get_head_position()
        x, y = self.direction
        new_head = (head[0] + x, head[1] + y)
        
        if (new_head[0] < 0 or new_head[0] >= GRID_WIDTH or
            new_head[1] < 0 or new_head[1] >= GRID_HEIGHT):
            return False, "Wall Collision"
            
        if new_head in self.positions[1:]:
            return False, "Self-Collision"
            
        if self.power_up_active and time.time() > self.power_up_end_time:
            self.power_up_active = False
            
        self.positions.insert(0, new_head)
        if len(self.positions) > self.length:
            self.positions.pop()
            
        return True, None
        
    def reset(self):
        self.positions = [(GRID_WIDTH // 2, GRID_HEIGHT // 2)]
        self.direction = (1, 0)
        self.length = 1
        self.score = 0
        self.power_up_active = False
        self.power_up_end_time = 0
        
    def render(self, surface):
        for i, pos in enumerate(self.positions):
            color = self.color_head if i == 0 else self.color_body1 if i % 2 == 0 else self.color_body2
            if self.power_up_active:
                color = (min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] + 50))
            rect = pygame.Rect(pos[0] * GRID_SIZE, pos[1] * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            pygame.draw.rect(surface, color, rect, border_radius=GRID_SIZE//4)
            pygame.draw.rect(surface, (0, 100, 0), rect, 2, border_radius=GRID_SIZE//4)
            if i == 0:
                eye_size = GRID_SIZE // 5
                eye_offset_x = self.direction[0] * (GRID_SIZE // 4)
                eye_offset_y = self.direction[1] * (GRID_SIZE // 4)
                pygame.draw.circle(
                    surface,
                    (255, 255, 255),
                    (pos[0] * GRID_SIZE + GRID_SIZE//2 - eye_size - eye_offset_x,
                     pos[1] * GRID_SIZE + GRID_SIZE//3 - eye_offset_y),
                    eye_size
                )
                pygame.draw.circle(
                    surface,
                    (0, 0, 0),
                    (pos[0] * GRID_SIZE + GRID_SIZE//2 - eye_size - eye_offset_x,
                     pos[1] * GRID_SIZE + GRID_SIZE//3 - eye_offset_y),
                    eye_size//2
                )
                pygame.draw.circle(
                    surface,
                    (255, 255, 255),
                    (pos[0] * GRID_SIZE + GRID_SIZE//2 + eye_size - eye_offset_x,
                     pos[1] * GRID_SIZE + GRID_SIZE//3 - eye_offset_y),
                    eye_size
                )
                pygame.draw.circle(
                    surface,
                    (0, 0, 0),
                    (pos[0] * GRID_SIZE + GRID_SIZE//2 + eye_size - eye_offset_x,
                     pos[1] * GRID_SIZE + GRID_SIZE//3 - eye_offset_y),
                    eye_size//2
                )

class Food:
    def __init__(self):
        self.position = (0, 0)
        self.type = 0
        self.colors = FOOD_COLORS.copy()
        self.spawn_time = time.time()
        
    def randomize_position(self, snake):
        while True:
            self.position = (
                random.randint(0, GRID_WIDTH - 1),
                random.randint(0, GRID_HEIGHT - 1)
            )
            if self.position not in snake.positions:
                break
        if random.random() < 0.1 and snake.score >= 50:
            self.type = 3
        else:
            self.type = random.randint(0, 2)
        if self.type != 3:
            random.shuffle(self.colors)
        self.spawn_time = time.time()
        
    def render(self, surface):
        elapsed = min(time.time() - self.spawn_time, 0.5)
        scale = 0.1 + 0.9 * (elapsed / 0.5)
        rect = pygame.Rect(
            self.position[0] * GRID_SIZE,
            self.position[1] * GRID_SIZE,
            GRID_SIZE * scale,
            GRID_SIZE * scale
        )
        rect.center = (
            self.position[0] * GRID_SIZE + GRID_SIZE // 2,
            self.position[1] * GRID_SIZE + GRID_SIZE // 2
        )
        
        if self.type == 3:
            pygame.draw.circle(surface, POWER_UP_COLOR, rect.center, GRID_SIZE//2 * scale)
        elif self.type == 0:
            pygame.draw.circle(surface, self.colors[0], rect.center, (GRID_SIZE//2 - 2) * scale)
            if scale > 0.5:
                pygame.draw.line(
                    surface, (0, 100, 0),
                    (rect.centerx, rect.top + 2 * scale),
                    (rect.centerx - GRID_SIZE//4 * scale, rect.top - GRID_SIZE//4 * scale),
                    max(1, int(3 * scale))
                )
                pygame.draw.ellipse(
                    surface, (0, 200, 0),
                    (rect.centerx - GRID_SIZE//4 * scale, rect.top - GRID_SIZE//3 * scale,
                     GRID_SIZE//2 * scale, GRID_SIZE//4 * scale)
                )
        elif self.type == 1:
            points = [
                (rect.left + GRID_SIZE//4 * scale, rect.top + GRID_SIZE//3 * scale),
                (rect.centerx, rect.top + GRID_SIZE//4 * scale),
                (rect.right - GRID_SIZE//4 * scale, rect.top + GRID_SIZE//3 * scale),
                (rect.right - GRID_SIZE//6 * scale, rect.bottom - GRID_SIZE//3 * scale),
                (rect.centerx, rect.bottom - GRID_SIZE//4 * scale),
                (rect.left + GRID_SIZE//3 * scale, rect.bottom - GRID_SIZE//3 * scale)
            ]
            pygame.draw.polygon(surface, self.colors[1], points)
            if scale > 0.5:
                pygame.draw.line(
                    surface, (100, 100, 0),
                    (rect.left + GRID_SIZE//4 * scale, rect.top + GRID_SIZE//3 * scale),
                    (rect.left, rect.top),
                    max(1, int(2 * scale))
                )
        else:
            pygame.draw.circle(surface, self.colors[2], rect.center, (GRID_SIZE//2 - 2) * scale)
            if scale > 0.5:
                pygame.draw.line(
                    surface, (0, 100, 0),
                    (rect.centerx, rect.top + 2 * scale),
                    (rect.centerx + GRID_SIZE//3 * scale, rect.top - GRID_SIZE//4 * scale),
                    max(1, int(2 * scale))
                )
                pygame.draw.line(
                    surface, (0, 100, 0),
                    (rect.centerx, rect.top + 2 * scale),
                    (rect.centerx - GRID_SIZE//3 * scale, rect.top - GRID_SIZE//4 * scale),
                    max(1, int(2 * scale))
                )

def draw_grid(surface):
    surface.fill(BACKGROUND)
    for x in range(0, WIDTH, GRID_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, HEIGHT - GRID_SIZE * 2), 1)
    for y in range(0, HEIGHT - GRID_SIZE * 2, GRID_SIZE):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (WIDTH, y), 1)
    pygame.draw.rect(surface, SCORE_BG, (0, HEIGHT - GRID_SIZE * 2, WIDTH, GRID_SIZE * 2))
    pygame.draw.line(surface, (200, 200, 200), (0, HEIGHT - GRID_SIZE * 2), (WIDTH, HEIGHT - GRID_SIZE * 2), 2)

def show_score(surface, score, high_score):
    score_text = font_medium.render(f"Score: {score}  High Score: {high_score}", True, SCORE_TEXT)
    score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT - GRID_SIZE))
    surface.blit(score_text, score_rect)

def show_game_over(surface, score, high_score, reason):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    surface.blit(overlay, (0, 0))
    game_over_text = font_large.render("GAME OVER!", True, GAME_OVER_TEXT)
    game_over_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - HEIGHT // 10))
    surface.blit(game_over_text, game_over_rect)
    reason_text = font_medium.render(f"Reason: {reason}", True, GAME_OVER_TEXT)
    reason_rect = reason_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - HEIGHT // 20))
    surface.blit(reason_text, reason_rect)
    score_text = font_medium.render(f"Final Score: {score}  High Score: {high_score}", True, GAME_OVER_TEXT)
    score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + HEIGHT // 20))
    surface.blit(score_text, score_rect)
    restart_text = font_small.render("Press SPACE to play again or ESC to exit", True, GAME_OVER_TEXT)
    restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + HEIGHT // 10))
    surface.blit(restart_text, restart_rect)

def show_pause(surface):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    surface.blit(overlay, (0, 0))
    pause_text = font_large.render("PAUSED", True, PAUSE_TEXT)
    pause_rect = pause_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    surface.blit(pause_text, pause_rect)
    continue_text = font_small.render("Press P to continue", True, PAUSE_TEXT)
    continue_rect = continue_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + HEIGHT // 20))
    surface.blit(continue_text, continue_rect)

def show_level_up(surface, level):
    text = font_medium.render(f"Level Up! {level}", True, LEVEL_UP_TEXT)
    rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    surface.blit(text, rect)

def show_start_menu(surface):
    surface.fill(BACKGROUND)
    title_text = font_large.render("Cartoon Snake Game", True, SCORE_TEXT)
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    surface.blit(title_text, title_rect)
    start_text = font_medium.render("Press SPACE to Start", True, SCORE_TEXT)
    start_rect = start_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    surface.blit(start_text, start_rect)
    instructions = [
        "Use ARROW KEYS to move",
        "Eat food to grow and score",
        "Avoid walls and self",
        "P to pause, SPACE to restart",
        "Gold power-up boosts speed"
    ]
    for i, line in enumerate(instructions):
        instr_text = font_small.render(line, True, SCORE_TEXT)
        instr_rect = instr_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + HEIGHT // 20 + i * HEIGHT // 30))
        surface.blit(instr_text, instr_rect)

async def main():
    snake = Snake()
    food = Food()
    game_over = False
    paused = False
    in_start_menu = True
    global high_score
    level = 1
    level_up_time = 0
    game_over_reason = ""
    
    food.randomize_position(snake)
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if in_start_menu:
                    if event.key == pygame.K_SPACE:
                        in_start_menu = False
                elif game_over:
                    if event.key == pygame.K_SPACE:
                        snake.reset()
                        food.randomize_position(snake)
                        game_over = False
                        paused = False
                        level = 1
                else:
                    if event.key == pygame.K_UP and snake.direction != (0, 1):
                        snake.direction = (0, -1)
                    elif event.key == pygame.K_DOWN and snake.direction != (0, -1):
                        snake.direction = (0, 1)
                    elif event.key == pygame.K_LEFT and snake.direction != (1, 0):
                        snake.direction = (-1, 0)
                    elif event.key == pygame.K_RIGHT and snake.direction != (-1, 0):
                        snake.direction = (1, 0)
                    elif event.key == pygame.K_p:
                        paused = not paused
                        pause_sound.play()
        
        if in_start_menu:
            show_start_menu(screen)
        elif not game_over and not paused:
            success, reason = snake.update()
            if not success:
                high_score = max(high_score, snake.score)
                game_over = True
                game_over_reason = reason
                game_over_sound.play()
                
            if snake.get_head_position() == food.position:
                snake.length += 1
                score_increase = 50 if food.type == 3 else (food.type + 1) * 10
                snake.score += score_increase
                if food.type == 3:
                    snake.power_up_active = True
                    snake.power_up_end_time = time.time() + POWER_UP_DURATION
                    power_up_sound.play()
                else:
                    eat_sound.play()
                food.randomize_position(snake)
                
                new_level = 1 + snake.score // 50
                if new_level > level:
                    level = new_level
                    level_up_time = time.time()
                    level_up_sound.play()
                    
            draw_grid(screen)
            snake.render(screen)
            food.render(screen)
            show_score(screen, snake.score, high_score)
            if level_up_time and time.time() - level_up_time < 1:
                show_level_up(screen, level)
        elif game_over:
            draw_grid(screen)
            snake.render(screen)
            food.render(screen)
            show_score(screen, snake.score, high_score)
            show_game_over(screen, snake.score, high_score, game_over_reason)
        elif paused:
            draw_grid(screen)
            snake.render(screen)
            food.render(screen)
            show_score(screen, snake.score, high_score)
            show_pause(screen)
            
        pygame.display.flip()
        current_fps = (BASE_FPS + snake.score // 50) * (2 if snake.power_up_active else 1)
        clock.tick(current_fps)
        await asyncio.sleep(1.0 / current_fps)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())