"""
🛩️ Airplane Shooter - 打飞机游戏
Pygame 竖版飞行射击游戏

操作说明:
  ← → ↑ ↓ / WASD  : 控制飞机移动
  空格键            : 发射子弹
  P 键              : 暂停/继续
  ESC               : 退出游戏
"""

import pygame
import random
import sys
import math

# ─── 初始化 ───────────────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init()

# ─── 游戏常量 ──────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 480
SCREEN_HEIGHT = 700
FPS = 60

# 颜色
BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
RED        = (255, 60, 60)
YELLOW     = (255, 230, 50)
GREEN      = (80, 220, 100)
BLUE       = (80, 160, 255)
GRAY       = (100, 100, 100)
DARK_GRAY  = (40, 40, 40)
ORANGE     = (255, 140, 0)
CYAN       = (0, 220, 220)

# 屏幕
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("🛩️ Airplane Shooter - 打飞机")
CLOCK  = pygame.time.Clock()

# ─── 字体（使用 pygame 内置默认字体，避免系统字体兼容问题）────────────────────
def _font(size, bold=False):
    return pygame.font.Font(None, size)

FONT_TITLE = _font(56, True)
FONT_LARGE = _font(36, True)
FONT_MID   = _font(28)
FONT_SMALL = _font(22)
FONT_SCORE = _font(26)

# ─── 音效（内置生成，无需文件）─────────────────────────────────────────────────
class SoundManager:
    def __init__(self):
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.enabled = True
        except Exception:
            self.enabled = False

    def _make_sound(self, freq, duration_ms, volume=0.3, wave_type="square"):
        """用 numpy 生成简单音效（备用方案：直接静默）"""
        try:
            import numpy as np
            sample_rate = 22050
            t = np.linspace(0, duration_ms / 1000, int(sample_rate * duration_ms / 1000), False)
            if wave_type == "square":
                wave = np.sign(np.sin(2 * math.pi * freq * t))
            elif wave_type == "saw":
                wave = 2 * (t * freq % 1) - 1
            else:
                wave = np.sin(2 * math.pi * freq * t)
            # 包络
            envelope = np.minimum(t / 0.01, np.ones_like(t))
            envelope *= np.maximum(1 - (t / (duration_ms / 1000 - 0.05)), 0)
            wave = (wave * envelope * volume * 32767).astype(np.int16)
            stereo = np.column_stack((wave, wave))
            sound = pygame.sndarray.make_sound(stereo)
            return sound
        except Exception:
            class DummySound:
                def play(self): pass
            return DummySound()

    def shoot(self):
        if self.enabled:
            try:
                self._make_sound(880, 60, 0.15, "square").play()
            except Exception:
                pass

    def explosion(self):
        if self.enabled:
            try:
                self._make_sound(120, 200, 0.25, "saw").play()
            except Exception:
                pass

    def hit(self):
        if self.enabled:
            try:
                self._make_sound(200, 100, 0.2, "square").play()
            except Exception:
                pass

    def level_up(self):
        if self.enabled:
            try:
                s = self._make_sound(440, 80, 0.2, "square")
                s.play()
                pygame.time.delay(100)
                self._make_sound(660, 100, 0.2, "square").play()
            except Exception:
                pass

SOUND = SoundManager()

# ─── 粒子特效 ─────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color, speed, angle, size, life):
        self.x = x
        self.y = y
        self.color = color
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.size = size
        self.life = life
        self.max_life = life
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.vy += 0.05  # 轻微重力
        if self.life <= 0:
            self.alive = False

    def draw(self, surface):
        alpha = max(0, int(255 * self.life / self.max_life))
        size = max(1, int(self.size * self.life / self.max_life))
        color = tuple(min(255, c + (255 - c) * (1 - self.life / self.max_life) * 0.5) for c in self.color)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), size)

class Explosion:
    def __init__(self, x, y, color=ORANGE, count=20, speed=5):
        self.particles = [
            Particle(x, y, color,
                     random.uniform(speed * 0.5, speed * 1.5),
                     random.uniform(0, 2 * math.pi),
                     random.randint(2, 5),
                     random.randint(20, 40))
            for _ in range(count)
        ]

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

    @property
    def alive(self):
        return bool(self.particles)

# ─── 拖尾效果 ─────────────────────────────────────────────────────────────────
class Trail:
    def __init__(self):
        self.points = []
        self.max_points = 12

    def add(self, x, y):
        self.points.append((x, y))
        if len(self.points) > self.max_points:
            self.points.pop(0)

    def draw(self, surface, color):
        for i, (px, py) in enumerate(self.points):
            alpha = int(180 * i / max(1, len(self.points)))
            size  = max(1, int(8 * i / max(1, len(self.points))))
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, alpha), (size, size), size)
            surface.blit(s, (int(px) - size, int(py) - size))

# ─── 我方飞机 ─────────────────────────────────────────────────────────────────
class Player(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        # 创建飞机图像（三角形战斗机）
        self.image = self._make_plane_image()
        self.rect  = self.image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80))
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)
        self.speed = 6
        self.hp = 3
        self.max_hp = 3
        self.invincible = 0          # 无敌时间
        self.trail = Trail()
        self.engine_flame = 0

    def _make_plane_image(self):
        surf = pygame.Surface((60, 70), pygame.SRCALPHA)
        # 机身
        pts = [(30, 0), (45, 25), (40, 65), (30, 60), (20, 65), (15, 25)]
        pygame.draw.polygon(surf, WHITE, pts)
        # 机翼
        pygame.draw.polygon(surf, (180, 200, 220), [(10, 40), (0, 55), (15, 55)])
        pygame.draw.polygon(surf, (180, 200, 220), [(50, 40), (60, 55), (45, 55)])
        # 驾驶舱
        pygame.draw.ellipse(surf, CYAN, (22, 15, 16, 20))
        # 描边
        pygame.draw.polygon(surf, (100, 120, 150), pts, 1)
        return surf

    def update(self, keys):
        dx = dy = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += self.speed
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= self.speed
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += self.speed
        # 对角线归一化
        if dx and dy:
            dx *= 0.707; dy *= 0.707
        self.x = max(0, min(SCREEN_WIDTH - self.rect.width, self.x + dx))
        self.y = max(0, min(SCREEN_HEIGHT - self.rect.height, self.y + dy))
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        self.trail.add(self.rect.centerx, self.rect.bottom - 10)
        if self.invincible > 0:
            self.invincible -= 1
        self.engine_flame = (self.engine_flame + 1) % 8

    def draw(self, surface):
        self.trail.draw(surface, (80, 160, 255))
        # 引擎火焰
        if self.engine_flame < 4:
            fx = self.rect.centerx
            fy = self.rect.bottom
            fh = random.randint(8, 16)
            colors = [YELLOW, ORANGE, RED]
            for i, c in enumerate(colors):
                pygame.draw.circle(surface, c, (fx + random.randint(-3, 3), fy + 2), fh - i * 2)
        # 闪烁（无敌状态）
        if self.invincible > 0 and (self.invincible // 4) % 2 == 0:
            s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            s.set_alpha(80)
            s.blit(self.image, (0, 0))
            surface.blit(s, self.rect)
        else:
            surface.blit(self.image, self.rect)

    def get_center(self):
        return self.rect.centerx, self.rect.centery

# ─── 子弹 ─────────────────────────────────────────────────────────────────────
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, speed=-12, color=YELLOW, size=4):
        super().__init__()
        self.image = pygame.Surface((size, size * 3), pygame.SRCALPHA)
        pygame.draw.rect(self.image, color, self.image.get_rect())
        pygame.draw.rect(self.image, WHITE, (size // 2 - 1, 0, 2, size * 3))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = speed
        self.damage = 1

    def update(self):
        self.rect.y += self.speed
        if self.rect.bottom < 0:
            self.kill()

    def draw(self, surface):
        surface.blit(self.image, self.rect)

# ─── 敌机 ─────────────────────────────────────────────────────────────────────
class Enemy(pygame.sprite.Sprite):
    TYPES = {
        "basic":  {"hp": 1, "speed": (2, 4), "score": 10,  "color": RED,    "w": 40, "h": 50},
        "fast":   {"hp": 1, "speed": (4, 6), "score": 15,  "color": ORANGE, "w": 30, "h": 40},
        "tank":   {"hp": 3, "speed": (1, 2), "score": 30,  "color": (180, 60, 200), "w": 55, "h": 65},
        "shooter":{"hp": 2, "speed": (1, 2), "score": 25,  "color": (200, 100, 200), "w": 45, "h": 55},
    }

    def __init__(self, enemy_type="basic"):
        super().__init__()
        cfg = self.TYPES.get(enemy_type, self.TYPES["basic"])
        self.enemy_type = enemy_type
        self.max_hp = cfg["hp"]
        self.hp = self.max_hp
        self.score = cfg["score"]
        self.w, self.h = cfg["w"], cfg["h"]
        color = cfg["color"]
        self.speed_min, self.speed_max = cfg["speed"]
        self.speed = random.uniform(self.speed_min, self.speed_max)
        self.image = self._make_image(color)
        self.rect  = self.image.get_rect(
            center=(random.randint(self.w, SCREEN_WIDTH - self.w), -self.h))
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)
        self.wobble = random.uniform(-0.5, 0.5)
        self.wobble_speed = random.uniform(0.02, 0.06)
        self.shoot_timer = random.randint(60, 180) if enemy_type == "shooter" else 0
        self.hit_flash = 0

    def _make_image(self, color):
        surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        # 敌机样式（倒三角形）
        cx, cy = self.w // 2, self.h // 2
        pts = [(cx, self.h), (self.w - 4, 4), (cx, 0), (4, 4)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, WHITE, pts, 1)
        # 驾驶舱
        pygame.draw.ellipse(surf, (80, 0, 0), (cx - 7, cy - 8, 14, 16))
        # 细节线
        pygame.draw.line(surf, (200, 50, 50), (cx - 10, 8), (cx + 10, 8), 1)
        return surf

    def update(self, *args):
        self.y += self.speed
        self.x += self.wobble * math.sin(pygame.time.get_ticks() * self.wobble_speed / 16)
        self.rect.y = int(self.y)
        self.rect.x = int(self.x)
        if self.hit_flash > 0:
            self.hit_flash -= 1
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

    def draw(self, surface):
        if self.hit_flash > 0 and self.hit_flash % 4 < 2:
            s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            s.fill((255, 255, 255, 150))
            s.blit(self.image, (0, 0))
            surface.blit(s, self.rect)
        else:
            surface.blit(self.image, self.rect)
        # 血条
        if self.max_hp > 1:
            bar_w = self.w
            bar_h = 4
            bx, by = self.rect.x, self.rect.y - 8
            pygame.draw.rect(surface, DARK_GRAY, (bx, by, bar_w, bar_h))
            pygame.draw.rect(surface, GREEN if self.hp == self.max_hp else YELLOW,
                             (bx, by, bar_w * self.hp // self.max_hp, bar_h))

    def hit(self, dmg=1):
        self.hp -= dmg
        self.hit_flash = 8
        return self.hp <= 0

    def can_shoot(self):
        if self.shoot_timer > 0:
            self.shoot_timer -= 1
            return False
        self.shoot_timer = random.randint(90, 180)
        return True

# ─── 敌机子弹 ─────────────────────────────────────────────────────────────────
class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dx=0, dy=4, color=RED):
        super().__init__()
        r = 5
        self.image = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (r, r), r)
        pygame.draw.circle(self.image, WHITE, (r, r), r - 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.dx = dx
        self.dy = dy

    def update(self):
        self.rect.x += int(self.dx)
        self.rect.y += int(self.dy)
        if (self.rect.left < -10 or self.rect.right > SCREEN_WIDTH + 10
                or self.rect.top > SCREEN_HEIGHT + 10):
            self.kill()

# ─── 星星背景 ─────────────────────────────────────────────────────────────────
class Star:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.size = random.choice([1, 1, 1, 2])
        self.speed = random.uniform(0.5, 2.0)
        self.twinkle = random.randint(0, 100)

    def update(self):
        self.y += self.speed
        self.twinkle = (self.twinkle + 2) % 200
        if self.y > SCREEN_HEIGHT:
            self.y = 0
            self.x = random.randint(0, SCREEN_WIDTH)

    def draw(self, surface):
        alpha = 100 + int(80 * math.sin(self.twinkle * 0.05))
        color = (180, 200, 255) if self.size > 1 else (100, 120, 180)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (self.size, self.size), self.size)
        surface.blit(s, (int(self.x), int(self.y)))

# ─── 血量道具 ─────────────────────────────────────────────────────────────────
class HealthPack(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((28, 28), pygame.SRCALPHA)
        pygame.draw.rect(self.image, RED,    (10, 0, 8, 28))   # 竖
        pygame.draw.rect(self.image, RED,    (0, 10, 28, 8))   # 横
        pygame.draw.circle(self.image, (255, 80, 80), (14, 14), 14, 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 1.5

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

# ─── UI 绘制函数 ───────────────────────────────────────────────────────────────
def draw_text(surface, text, x, y, font, color, shadow=True, shadow_color=None):
    if shadow:
        shadow_c = shadow_color or (0, 0, 0)
        s = font.render(text, True, shadow_c)
        surface.blit(s, (x + 1, y + 1))
    img = font.render(text, True, color)
    surface.blit(img, (x, y))

def draw_hp_bar(surface, x, y, current, maximum, width=200, height=16):
    pygame.draw.rect(surface, DARK_GRAY, (x, y, width, height), border_radius=6)
    ratio = max(0, current / maximum)
    color = GREEN if ratio > 0.5 else YELLOW if ratio > 0.25 else RED
    pygame.draw.rect(surface, color, (x + 2, y + 2, int((width - 4) * ratio), height - 4), border_radius=5)
    pygame.draw.rect(surface, WHITE, (x, y, width, height), width=1, border_radius=6)
    label = f"{current} / {maximum}"
    lbl = FONT_SMALL.render(label, True, WHITE)
    surface.blit(lbl, (x + (width - lbl.get_width()) // 2, y + (height - lbl.get_height()) // 2))

def draw_button(surface, rect, text, mouse_pos, font, bg_color, fg_color, hover_color):
    hovered = rect.collidepoint(mouse_pos)
    color = hover_color if hovered else bg_color
    pygame.draw.rect(surface, color, rect, border_radius=10)
    pygame.draw.rect(surface, WHITE, rect, 1, border_radius=10)
    txt = font.render(text, True, WHITE)
    surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

# ─── 游戏主类 ─────────────────────────────────────────────────────────────────
class Game:
    STATES = {"menu", "playing", "paused", "gameover"}

    def __init__(self):
        self.state = "menu"
        self.reset()

    def reset(self):
        self.player        = Player()
        self.player_bullets= pygame.sprite.Group()
        self.enemies       = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.all_sprites   = pygame.sprite.Group()
        self.explosions    = []
        self.health_packs  = pygame.sprite.Group()
        self.stars         = [Star() for _ in range(80)]
        self.score         = 0
        self.high_score    = self.high_score if hasattr(self, "high_score") else 0
        self.level         = 1
        self.level_floor   = 100
        self.shoot_cooldown= 0
        self.enemy_spawn   = 0
        self.spawn_interval= 60
        self.fps_display   = False
        self.menu_selection= 0
        self.last_time     = pygame.time.get_ticks()
        self.fps_smooth    = FPS

    def spawn_enemy(self):
        t = random.choices(["basic", "fast", "tank", "shooter"],
                            weights=[50, 25, 12, 13])[0]
        enemy = Enemy(t)
        self.enemies.add(enemy)

    def check_collisions(self):
        player = self.player
        center = player.get_center()

        # 子弹 vs 敌机
        hits = pygame.sprite.groupcollide(
            self.player_bullets, self.enemies, True, False)
        for bullet, enemy_list in hits.items():
            for enemy in enemy_list:
                dead = enemy.hit(bullet.damage)
                SOUND.hit()
                self.explosions.append(Explosion(
                    enemy.rect.centerx, enemy.rect.centery, ORANGE, 8, 3))
                if dead:
                    SOUND.explosion()
                    self.explosions.append(Explosion(
                        enemy.rect.centerx, enemy.rect.centery, YELLOW, 25, 6))
                    self.score += enemy.score
                    if random.random() < 0.08:
                        hp = HealthPack(enemy.rect.centerx, enemy.rect.centery)
                        self.health_packs.add(hp)
                    enemy.kill()
                    # 升级
                    if self.score >= self.level_floor:
                        self.level += 1
                        self.level_floor += self.level * 100
                        self.spawn_interval = max(20, 60 - self.level * 3)
                        SOUND.level_up()

        # 敌机 vs 玩家
        if player.invincible == 0:
            for enemy in pygame.sprite.spritecollide(player, self.enemies, True):
                SOUND.explosion()
                self.explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, RED, 20, 5))
                player.hp -= 1
                player.invincible = 90
                if player.hp <= 0:
                    self.game_over()

        # 敌机子弹 vs 玩家
        if player.invincible == 0:
            for bullet in pygame.sprite.spritecollide(player, self.enemy_bullets, True):
                SOUND.hit()
                self.explosions.append(Explosion(bullet.rect.centerx, bullet.rect.centery, RED, 8, 3))
                player.hp -= 1
                player.invincible = 90
                if player.hp <= 0:
                    self.game_over()

        # 血包 vs 玩家
        for hp in pygame.sprite.spritecollide(player, self.health_packs, True):
            player.hp = min(player.max_hp, player.hp + 1)
            self.explosions.append(Explosion(hp.rect.centerx, hp.rect.centery, GREEN, 12, 4))
            SOUND.level_up()

    def game_over(self):
        self.state = "gameover"
        if self.score > self.high_score:
            self.high_score = self.score

    # ── 各状态处理 ──────────────────────────────────────────────────────────────

    def handle_menu(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.state = "playing"
                    self.reset()
                    self.state = "playing"
                elif e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
            elif e.type == pygame.QUIT:
                pygame.quit(); sys.exit()

    def handle_playing(self, events):
        keys = pygame.key.get_pressed()
        self.player.update(keys)

        # 射击
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if (keys[pygame.K_SPACE] or keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]) and self.shoot_cooldown == 0:
            cx, cy = self.player.get_center()
            self.player_bullets.add(Bullet(cx, cy - 30))
            if self.level >= 3:
                self.player_bullets.add(Bullet(cx - 15, cy - 20))
                self.player_bullets.add(Bullet(cx + 15, cy - 20))
            if self.level >= 6:
                self.player_bullets.add(Bullet(cx, cy - 30, -12, CYAN, 6))
            self.shoot_cooldown = 10 - min(5, self.level // 2)
            SOUND.shoot()

        # 敌机生成
        self.enemy_spawn += 1
        if self.enemy_spawn >= self.spawn_interval:
            self.enemy_spawn = 0
            self.spawn_enemy()

        # 敌机射击
        for enemy in self.enemies:
            if hasattr(enemy, "can_shoot") and enemy.can_shoot():
                self.enemy_bullets.add(
                    EnemyBullet(enemy.rect.centerx, enemy.rect.bottom))

        # 更新
        self.player_bullets.update()
        self.enemies.update()
        self.enemy_bullets.update()
        self.health_packs.update()
        for s in self.stars:
            s.update()
        for ex in self.explosions:
            ex.update()
        self.explosions = [e for e in self.explosions if e.alive]
        self.check_collisions()

        # FPS 平滑
        now = pygame.time.get_ticks()
        dt = max(1, now - self.last_time)
        self.last_time = now
        self.fps_smooth = 0.9 * self.fps_smooth + 0.1 * (1000 / dt)

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_p:
                    self.state = "paused"
                elif e.key == pygame.K_F1:
                    self.fps_display = not self.fps_display
                elif e.key == pygame.K_ESCAPE:
                    self.state = "menu"
            elif e.type == pygame.QUIT:
                pygame.quit(); sys.exit()

    def handle_paused(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_p, pygame.K_RETURN, pygame.K_SPACE):
                    self.state = "playing"
                    self.last_time = pygame.time.get_ticks()
                elif e.key == pygame.K_ESCAPE:
                    self.state = "menu"
            elif e.type == pygame.QUIT:
                pygame.quit(); sys.exit()

    def handle_gameover(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.reset()
                    self.state = "playing"
                elif e.key == pygame.K_ESCAPE:
                    self.state = "menu"
            elif e.type == pygame.QUIT:
                pygame.quit(); sys.exit()

    # ── 各状态渲染 ─────────────────────────────────────────────────────────────

    def render(self, surface):
        surface.fill(BLACK)
        for s in self.stars:
            s.draw(surface)

        if self.state == "menu":
            self._render_menu(surface)
        elif self.state == "playing":
            self._render_playing(surface)
        elif self.state == "paused":
            self._render_playing(surface)
            self._render_paused_overlay(surface)
        elif self.state == "gameover":
            self._render_gameover(surface)

        pygame.display.flip()

    def _render_menu(self, surface):
        # 标题
        title = FONT_TITLE.render("AIRPLANE", True, WHITE)
        sub   = FONT_LARGE.render("SHOOTER",  True, CYAN)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 160))
        surface.blit(sub,   (SCREEN_WIDTH // 2 - sub.get_width() // 2,   220))

        # 飞机装饰
        plane_surf = self.player.image.copy()
        plane_surf = pygame.transform.rotate(plane_surf, 0)
        surface.blit(plane_surf, (SCREEN_WIDTH // 2 - 30, 300))

        # 操作说明
        info_lines = [
            (">>> 按 SPACE / ENTER 开始游戏 <<<", CYAN),
            ("", WHITE),
            ("Controls  操作说明", YELLOW),
            ("Arrow Keys / WASD  移动飞机", GRAY),
            ("SPACE / CTRL        发射子弹", GRAY),
            ("P                   暂停游戏", GRAY),
            ("ESC                 返回菜单", GRAY),
        ]
        for i, (txt, col) in enumerate(info_lines):
            draw_text(surface, txt, SCREEN_WIDTH // 2 - 160, 390 + i * 28, FONT_MID, col, shadow=False)

        # 高分
        if self.high_score > 0:
            hs = FONT_SMALL.render(f"High Score: {self.high_score}", True, YELLOW)
            surface.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2, 610))

    def _render_playing(self, surface):
        # 粒子爆炸
        for ex in self.explosions:
            ex.draw(surface)

        # 子弹
        for b in self.player_bullets:
            surface.blit(b.image, b.rect)
        for b in self.enemy_bullets:
            surface.blit(b.image, b.rect)

        # 敌机
        for e in self.enemies:
            e.draw(surface)

        # 血包
        for hp in self.health_packs:
            surface.blit(hp.image, hp.rect)

        # 玩家
        self.player.draw(surface)

        # HUD
        pygame.draw.rect(surface, (0, 0, 0, 120), (0, 0, SCREEN_WIDTH, 52))
        draw_text(surface, f"SCORE: {self.score}", 12, 8, FONT_SCORE, WHITE)
        draw_text(surface, f"HI: {self.high_score}", 12, 30, FONT_SMALL, YELLOW)
        draw_text(surface, f"LV.{self.level}", SCREEN_WIDTH - 90, 8, FONT_SCORE, ORANGE)
        draw_hp_bar(SCREEN, SCREEN_WIDTH // 2 - 100, 8, self.player.hp, self.player.max_hp)

        if self.fps_display:
            draw_text(surface, f"FPS: {int(self.fps_smooth)}", SCREEN_WIDTH // 2 - 30, 32, FONT_SMALL, GRAY)

    def _render_paused_overlay(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        draw_text(surface, "PAUSED", SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 - 40, FONT_LARGE, WHITE)
        draw_text(surface, "Press P or SPACE to resume", SCREEN_WIDTH // 2 - 140, SCREEN_HEIGHT // 2 + 10, FONT_MID, GRAY)

    def _render_gameover(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))
        draw_text(surface, "GAME OVER", SCREEN_WIDTH // 2 - 120, 200, FONT_TITLE, RED)
        draw_text(surface, f"Score: {self.score}", SCREEN_WIDTH // 2 - 80, 290, FONT_LARGE, WHITE)
        if self.score >= self.high_score:
            draw_text(surface, "NEW HIGH SCORE!", SCREEN_WIDTH // 2 - 100, 340, FONT_MID, YELLOW)
        draw_text(surface, f"Best: {self.high_score}", SCREEN_WIDTH // 2 - 60, 380, FONT_MID, YELLOW)
        draw_text(surface, "[ SPACE / ENTER ] Play Again", SCREEN_WIDTH // 2 - 160, 460, FONT_MID, CYAN)
        draw_text(surface, "[ ESC ] Back to Menu", SCREEN_WIDTH // 2 - 110, 500, FONT_MID, GRAY)

    # ── 主循环 ─────────────────────────────────────────────────────────────────

    def run(self):
        while True:
            events = pygame.event.get()
            {
                "menu":     self.handle_menu,
                "playing":  self.handle_playing,
                "paused":   self.handle_paused,
                "gameover": self.handle_gameover,
            }[self.state](events)
            self.render(SCREEN)
            CLOCK.tick(FPS)

# ─── 入口 ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    game = Game()
    game.run()
