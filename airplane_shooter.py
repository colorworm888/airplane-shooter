# -*- coding: utf-8 -*-
"""
Airplane Shooter - Scrolling Vertical Shooter Game
Pygame-based flight shooting game

Controls:
  Arrow Keys / WASD  : Move aircraft
  SPACE / CTRL        : Fire bullets
  P                   : Pause / Resume
  ESC                 : Quit / Back to menu
"""

import pygame
import random
import sys
import math
import os

# ─── Init ──────────────────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init()

# ─── Constants ─────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 480
SCREEN_HEIGHT = 700
FPS = 60

# Colors
BLACK     = (0, 0, 0)
WHITE     = (255, 255, 255)
RED       = (255, 60, 60)
YELLOW    = (255, 230, 50)
GREEN     = (80, 220, 100)
BLUE      = (80, 160, 255)
GRAY      = (100, 100, 100)
DARK_GRAY = (40, 40, 40)
ORANGE    = (255, 140, 0)
CYAN      = (0, 220, 220)

# Screen
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Airplane Shooter")
CLOCK  = pygame.time.Clock()

# ─── Fonts (Microsoft YaHei for Chinese support) ───────────────────────────────
FONT_PATHS = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhl.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]
_chinese_font_path = None
for fp in FONT_PATHS:
    if os.path.exists(fp):
        _chinese_font_path = fp
        break

def _font(size):
    if _chinese_font_path:
        return pygame.font.Font(_chinese_font_path, size)
    return pygame.font.Font(None, size)

FONT_TITLE = _font(56)
FONT_LARGE = _font(36)
FONT_MID   = _font(28)
FONT_SMALL = _font(22)
FONT_SCORE = _font(26)

# ─── Sound Manager (procedural, no files needed) ───────────────────────────────
class SoundManager:
    def __init__(self):
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.enabled = True
        except Exception:
            self.enabled = False

    def _beep(self, freq_hz, duration_ms, volume=0.2):
        try:
            import numpy as np
            sr = 22050
            t  = np.linspace(0, duration_ms / 1000, int(sr * duration_ms / 1000), False)
            wave = np.sin(2 * math.pi * freq_hz * t)
            env = np.minimum(t / 0.01, np.ones_like(t))
            env *= np.maximum(1 - t / (duration_ms / 1000 - 0.01), 0)
            data = (wave * env * volume * 32767).astype(np.int16)
            stereo = np.column_stack((data, data))
            return pygame.sndarray.make_sound(stereo)
        except Exception:
            class Dummy:
                def play(self): pass
            return Dummy()

    def shoot(self):
        if self.enabled: self._beep(880, 60, 0.12).play()
    def explosion(self):
        if self.enabled: self._beep(120, 250, 0.22).play()
    def hit(self):
        if self.enabled: self._beep(200, 100, 0.18).play()
    def level_up(self):
        if self.enabled:
            self._beep(440, 80, 0.18).play()
            pygame.time.delay(90)
            self._beep(660, 100, 0.18).play()

SOUND = SoundManager()

# ─── Particle Effects ──────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color, speed, angle, size, life):
        self.x, self.y = x, y
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
        self.vy += 0.05
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def draw(self, surface):
        alpha = max(0, int(255 * self.life / self.max_life))
        r = max(1, int(self.size * self.life / self.max_life))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (r, r), r)
        surface.blit(surf, (int(self.x) - r, int(self.y) - r))

class Explosion:
    def __init__(self, x, y, color=ORANGE, count=20, speed=5):
        self.particles = [
            Particle(x, y, color,
                     random.uniform(speed * 0.4, speed * 1.5),
                     random.uniform(0, 2 * math.pi),
                     random.uniform(2, 5),
                     random.randint(20, 45))
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

# ─── Trail Effect ─────────────────────────────────────────────────────────────
class Trail:
    def __init__(self):
        self.points = []
        self.max_points = 14

    def add(self, x, y):
        self.points.append((x, y))
        if len(self.points) > self.max_points:
            self.points.pop(0)

    def draw(self, surface, color=(80, 160, 255)):
        for i, (px, py) in enumerate(self.points):
            alpha = int(200 * i / max(1, len(self.points)))
            size  = max(1, int(7 * i / max(1, len(self.points))))
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, alpha), (size, size), size)
            surface.blit(surf, (int(px) - size, int(py) - size))

# ─── Player Aircraft ──────────────────────────────────────────────────────────
class Player:
    def __init__(self):
        self.image = self._make_surface()
        self.rect  = self.image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80))
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)
        self.speed = 6
        self.hp = 3
        self.max_hp = 3
        self.invincible = 0
        self.trail = Trail()
        self.flame_timer = 0

    def _make_surface(self):
        surf = pygame.Surface((64, 72), pygame.SRCALPHA)
        # Fuselage
        pts = [(32, 2), (46, 28), (40, 68), (32, 63), (24, 68), (18, 28)]
        pygame.draw.polygon(surf, WHITE, pts)
        pygame.draw.polygon(surf, (100, 120, 150), pts, 1)
        # Wings
        pygame.draw.polygon(surf, (170, 195, 220), [(10, 44), (0, 60), (16, 60)])
        pygame.draw.polygon(surf, (170, 195, 220), [(54, 44), (64, 60), (48, 60)])
        # Cockpit
        pygame.draw.ellipse(surf, CYAN, (22, 14, 18, 22))
        return surf

    def update(self, keys):
        dx = dy = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += self.speed
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= self.speed
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += self.speed
        if dx and dy:
            dx *= 0.707; dy *= 0.707
        self.x = max(0, min(SCREEN_WIDTH - self.rect.width, self.x + dx))
        self.y = max(0, min(SCREEN_HEIGHT - self.rect.height, self.y + dy))
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        self.trail.add(self.rect.centerx, self.rect.bottom - 8)
        if self.invincible > 0:
            self.invincible -= 1
        self.flame_timer = (self.flame_timer + 1) % 6

    def draw(self, surface):
        self.trail.draw(surface)
        # Engine flame
        if self.flame_timer < 3:
            fx = self.rect.centerx + random.randint(-3, 3)
            fy = self.rect.bottom + 2
            fh = random.randint(8, 16)
            for c in [YELLOW, ORANGE, RED]:
                pygame.draw.circle(surface, c, (fx, fy), max(2, fh - random.randint(0, 4)))
        # Blink when invincible
        if self.invincible > 0 and (self.invincible // 4) % 2 == 0:
            tmp = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            tmp.set_alpha(80)
            tmp.blit(self.image, (0, 0))
            surface.blit(tmp, self.rect)
        else:
            surface.blit(self.image, self.rect)

    def get_center(self):
        return self.rect.centerx, self.rect.centery

# ─── Bullet ────────────────────────────────────────────────────────────────────
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, speed=-12, color=YELLOW):
        super().__init__()
        r = 4
        self.image = pygame.Surface((r * 2, r * 4), pygame.SRCALPHA)
        pygame.draw.rect(self.image, color, (0, 0, r * 2, r * 4))
        pygame.draw.rect(self.image, WHITE, (r - 1, 0, 2, r * 4))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = speed
        self.damage = 1

    def update(self):
        self.rect.y += self.speed
        if self.rect.bottom < 0:
            self.kill()

# ─── Enemy ─────────────────────────────────────────────────────────────────────
class Enemy(pygame.sprite.Sprite):
    TYPES = {
        "basic":   {"hp": 1, "speed": (2, 4),   "score": 10,  "color": RED,                       "w": 40, "h": 50},
        "fast":    {"hp": 1, "speed": (4, 6.5), "score": 15,  "color": ORANGE,                     "w": 30, "h": 40},
        "tank":    {"hp": 3, "speed": (1, 2),   "score": 30,  "color": (180, 60, 200),             "w": 55, "h": 65},
        "shooter": {"hp": 2, "speed": (1, 2.5), "score": 25,  "color": (200, 100, 200),             "w": 45, "h": 55},
    }

    def __init__(self, enemy_type="basic"):
        super().__init__()
        cfg = self.TYPES.get(enemy_type, self.TYPES["basic"])
        self.enemy_type = enemy_type
        self.max_hp   = cfg["hp"]
        self.hp       = self.max_hp
        self.score    = cfg["score"]
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
        self.wobble_phase = random.uniform(0, math.pi * 2)
        self.shoot_timer = random.randint(80, 180) if enemy_type == "shooter" else 0
        self.hit_flash = 0

    def _make_image(self, color):
        surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        cx = self.w // 2
        # Body: inverted triangle
        pts = [(cx, self.h), (self.w - 4, 4), (cx, 0), (4, 4)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, WHITE, pts, 1)
        # Cockpit
        pygame.draw.ellipse(surf, (80, 0, 0), (cx - 7, self.h // 2 - 10, 14, 18))
        # Details
        pygame.draw.line(surf, (200, 50, 50), (cx - 10, 6), (cx + 10, 6), 1)
        pygame.draw.line(surf, (200, 50, 50), (cx - 10, self.h - 6), (cx + 10, self.h - 6), 1)
        return surf

    def update(self, *args):
        self.y += self.speed
        self.wobble_phase += 0.04
        self.x += self.wobble * math.sin(self.wobble_phase)
        self.rect.y = int(self.y)
        self.rect.x = int(max(0, min(SCREEN_WIDTH - self.w, self.x)))
        if self.hit_flash > 0:
            self.hit_flash -= 1
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

    def draw(self, surface):
        img = self.image
        if self.hit_flash > 0 and self.hit_flash % 4 < 2:
            tmp = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            tmp.fill((255, 255, 255, 140))
            tmp.blit(self.image, (0, 0))
            img = tmp
        surface.blit(img, self.rect)
        # HP bar for multi-HP enemies
        if self.max_hp > 1:
            bw, bh = self.w, 4
            bx, by = self.rect.x, self.rect.y - 8
            pygame.draw.rect(surface, DARK_GRAY, (bx, by, bw, bh))
            bar_color = GREEN if self.hp == self.max_hp else YELLOW
            pygame.draw.rect(surface, bar_color, (bx, by, bw * self.hp // self.max_hp, bh))

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

# ─── Enemy Bullet ─────────────────────────────────────────────────────────────
class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, dx=0, dy=4, color=RED):
        super().__init__()
        r = 5
        self.image = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color,  (r, r), r)
        pygame.draw.circle(self.image, WHITE, (r, r), r - 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.dx = dx
        self.dy = dy

    def update(self):
        self.rect.x += int(self.dx)
        self.rect.y += int(self.dy)
        if self.rect.left < -10 or self.rect.right > SCREEN_WIDTH + 10 \
           or self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()

# ─── Star Background ──────────────────────────────────────────────────────────
class Star:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.size = random.choice([1, 1, 2])
        self.speed = random.uniform(0.5, 2.0)
        self.twinkle = random.randint(0, 100)

    def update(self):
        self.y += self.speed
        self.twinkle = (self.twinkle + 2) % 200
        if self.y > SCREEN_HEIGHT:
            self.y = 0
            self.x = random.randint(0, SCREEN_WIDTH)

    def draw(self, surface):
        a = 100 + int(80 * math.sin(self.twinkle * 0.05))
        color = (180, 200, 255) if self.size > 1 else (100, 120, 180)
        r = self.size
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, a), (r, r), r)
        surface.blit(s, (int(self.x), int(self.y)))

# ─── Health Pack ──────────────────────────────────────────────────────────────
class HealthPack(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((28, 28), pygame.SRCALPHA)
        pygame.draw.rect(self.image, RED,   (11, 0,  6, 28))
        pygame.draw.rect(self.image, RED,   (0,  11, 28, 6))
        pygame.draw.circle(self.image, (255, 80, 80), (14, 14), 14, 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 1.5

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

# ─── UI Helpers ────────────────────────────────────────────────────────────────
def draw_text(surface, text, x, y, font, color):
    img = font.render(text, True, color)
    surface.blit(img, (x, y))

def draw_hp_bar(surface, x, y, current, maximum, width=200, height=16):
    pygame.draw.rect(surface, DARK_GRAY, (x, y, width, height), border_radius=6)
    ratio = max(0, current / maximum)
    bar_color = GREEN if ratio > 0.5 else YELLOW if ratio > 0.25 else RED
    bx = x + 2
    by = y + 2
    bh = height - 4
    bw = int((width - 4) * ratio)
    if bw > 0:
        pygame.draw.rect(surface, bar_color, (bx, by, bw, bh), border_radius=5)
    pygame.draw.rect(surface, WHITE, (x, y, width, height), 1, border_radius=6)
    label = f"{current} / {maximum}"
    lbl = FONT_SMALL.render(label, True, WHITE)
    surface.blit(lbl, (x + (width - lbl.get_width()) // 2,
                        y + (height - lbl.get_height()) // 2))

# ─── Game Class ───────────────────────────────────────────────────────────────
class Game:
    STATES = {"menu", "playing", "paused", "gameover"}

    def __init__(self):
        self.state = "menu"
        self.reset()

    def reset(self):
        self.player          = Player()
        self.player_bullets  = pygame.sprite.Group()
        self.enemies         = pygame.sprite.Group()
        self.enemy_bullets   = pygame.sprite.Group()
        self.explosions      = []
        self.health_packs    = pygame.sprite.Group()
        self.stars           = [Star() for _ in range(80)]
        self.score           = 0
        self.high_score      = getattr(self, "high_score", 0)
        self.level           = 1
        self.level_floor     = 100
        self.shoot_cooldown  = 0
        self.enemy_spawn     = 0
        self.spawn_interval  = 65
        self.fps_display     = False
        self.last_time       = pygame.time.get_ticks()
        self.fps_smooth      = FPS

    def spawn_enemy(self):
        t = random.choices(
            ["basic", "fast", "tank", "shooter"],
            weights=[50, 25, 12, 13])[0]
        self.enemies.add(Enemy(t))

    def check_collisions(self):
        player = self.player

        # Player bullets vs enemies
        hits = pygame.sprite.groupcollide(
            self.player_bullets, self.enemies, True, False)
        for bullet, elist in hits.items():
            for enemy in elist:
                dead = enemy.hit(bullet.damage)
                SOUND.hit()
                self.explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, ORANGE, 8, 3))
                if dead:
                    SOUND.explosion()
                    self.explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, YELLOW, 25, 6))
                    self.score += enemy.score
                    if random.random() < 0.08:
                        self.health_packs.add(HealthPack(enemy.rect.centerx, enemy.rect.centery))
                    enemy.kill()
                    if self.score >= self.level_floor:
                        self.level += 1
                        self.level_floor += self.level * 100
                        self.spawn_interval = max(20, 65 - self.level * 3)
                        SOUND.level_up()

        # Enemies vs player
        if player.invincible == 0:
            for _ in pygame.sprite.spritecollide(player, self.enemies, True):
                SOUND.explosion()
                self.explosions.append(Explosion(player.rect.centerx, player.rect.centery, RED, 20, 5))
                player.hp -= 1
                player.invincible = 90
                if player.hp <= 0:
                    self.game_over()

        # Enemy bullets vs player
        if player.invincible == 0:
            for b in pygame.sprite.spritecollide(player, self.enemy_bullets, True):
                SOUND.hit()
                self.explosions.append(Explosion(b.rect.centerx, b.rect.centery, RED, 8, 3))
                player.hp -= 1
                player.invincible = 90
                if player.hp <= 0:
                    self.game_over()

        # Health packs
        for hp in pygame.sprite.spritecollide(player, self.health_packs, True):
            player.hp = min(player.max_hp, player.hp + 1)
            self.explosions.append(Explosion(hp.rect.centerx, hp.rect.centery, GREEN, 12, 4))
            SOUND.level_up()

    def game_over(self):
        self.state = "gameover"
        if self.score > self.high_score:
            self.high_score = self.score

    # ── Input handling ───────────────────────────────────────────────────────

    def _handle_quit(self, events):
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

    def handle_menu(self, events):
        self._handle_quit(events)
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.reset()
                    self.state = "playing"
                elif e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

    def handle_playing(self, events):
        self._handle_quit(events)
        keys = pygame.key.get_pressed()
        self.player.update(keys)

        # Shoot
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        shoot_keys = (pygame.K_SPACE, pygame.K_LCTRL, pygame.K_RCTRL)
        if any(keys[k] for k in shoot_keys) and self.shoot_cooldown == 0:
            cx, cy = self.player.get_center()
            self.player_bullets.add(Bullet(cx, cy - 30))
            if self.level >= 3:
                self.player_bullets.add(Bullet(cx - 15, cy - 20))
                self.player_bullets.add(Bullet(cx + 15, cy - 20))
            if self.level >= 6:
                self.player_bullets.add(Bullet(cx, cy - 30, -14, CYAN))
            cooldown = max(5, 12 - self.level)
            self.shoot_cooldown = cooldown
            SOUND.shoot()

        # Spawn enemies
        self.enemy_spawn += 1
        if self.enemy_spawn >= self.spawn_interval:
            self.enemy_spawn = 0
            self.spawn_enemy()

        # Enemy shooting
        for enemy in self.enemies:
            if enemy.can_shoot():
                self.enemy_bullets.add(EnemyBullet(enemy.rect.centerx, enemy.rect.bottom))

        # Update
        self.player_bullets.update()
        self.enemies.update()
        self.enemy_bullets.update()
        self.health_packs.update()
        for s in self.stars:
            s.update()
        for ex in self.explosions:
            ex.update()
        self.explosions = [e for e in self.explosions if e.alive]

        now = pygame.time.get_ticks()
        dt = max(1, now - self.last_time)
        self.last_time = now
        self.fps_smooth = 0.9 * self.fps_smooth + 0.1 * (1000 / dt)

        self.check_collisions()

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_p:
                    self.state = "paused"
                elif e.key == pygame.K_F1:
                    self.fps_display = not self.fps_display
                elif e.key == pygame.K_ESCAPE:
                    self.state = "menu"

    def handle_paused(self, events):
        self._handle_quit(events)
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_p, pygame.K_RETURN, pygame.K_SPACE):
                    self.state = "playing"
                    self.last_time = pygame.time.get_ticks()
                elif e.key == pygame.K_ESCAPE:
                    self.state = "menu"

    def handle_gameover(self, events):
        self._handle_quit(events)
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.reset()
                    self.state = "playing"
                elif e.key == pygame.K_ESCAPE:
                    self.state = "menu"

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render(self, surface):
        surface.fill(BLACK)
        for s in self.stars:
            s.draw(surface)

        {
            "menu":     self._render_menu,
            "playing":  self._render_playing,
            "paused":   self._render_playing,
            "gameover": self._render_gameover,
        }[self.state](surface)

        if self.state == "paused":
            self._render_paused_overlay(surface)

        pygame.display.flip()

    def _render_menu(self, surface):
        # Title
        t1 = FONT_TITLE.render("AIRPLANE", True, WHITE)
        t2 = FONT_LARGE.render("SHOOTER",  True, CYAN)
        surface.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, 140))
        surface.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 205))

        # Decorative plane
        surface.blit(self.player.image, (SCREEN_WIDTH // 2 - 32, 280))

        # Start prompt (blinking)
        if (pygame.time.get_ticks() // 600) % 2 == 0:
            prompt = FONT_MID.render(">>> PRESS SPACE TO START <<<", True, CYAN)
            surface.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 380))

        # Controls
        ctrl = [
            ("[ CONTROLS ]",         YELLOW),
            ("Move  : Arrow / WASD", WHITE),
            ("Fire  : SPACE / CTRL", WHITE),
            ("Pause : P",             WHITE),
            ("Menu  : ESC",           WHITE),
        ]
        for i, (txt, col) in enumerate(ctrl):
            img = FONT_SMALL.render(txt, True, col)
            surface.blit(img, (SCREEN_WIDTH // 2 - 140, 430 + i * 28))

        # High score
        if self.high_score > 0:
            hs = FONT_SMALL.render(f"High Score: {self.high_score}", True, YELLOW)
            surface.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2, 610))

    def _render_playing(self, surface):
        for ex in self.explosions:
            ex.draw(surface)
        for b in self.player_bullets:
            surface.blit(b.image, b.rect)
        for b in self.enemy_bullets:
            surface.blit(b.image, b.rect)
        for e in self.enemies:
            e.draw(surface)
        for hp in self.health_packs:
            surface.blit(hp.image, hp.rect)
        self.player.draw(surface)

        # HUD bar
        pygame.draw.rect(surface, (0, 0, 0, 130), (0, 0, SCREEN_WIDTH, 54))
        draw_text(surface, f"SCORE: {self.score}",         12,   8, FONT_SCORE, WHITE)
        draw_text(surface, f"HI: {self.high_score}",      12,  32, FONT_SMALL, YELLOW)
        draw_text(surface, f"LV.{self.level}", SCREEN_WIDTH - 80, 8, FONT_SCORE, ORANGE)
        draw_hp_bar(surface, SCREEN_WIDTH // 2 - 100, 8,
                    self.player.hp, self.player.max_hp)
        if self.fps_display:
            draw_text(surface, f"FPS: {int(self.fps_smooth)}",
                      SCREEN_WIDTH // 2 - 28, 34, FONT_SMALL, GRAY)

    def _render_paused_overlay(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        msg1 = FONT_LARGE.render("PAUSED", True, WHITE)
        msg2 = FONT_MID.render("Press P or SPACE to resume", True, GRAY)
        surface.blit(msg1, (SCREEN_WIDTH // 2 - msg1.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        surface.blit(msg2, (SCREEN_WIDTH // 2 - msg2.get_width() // 2, SCREEN_HEIGHT // 2 + 10))

    def _render_gameover(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        g1 = FONT_TITLE.render("GAME OVER", True, RED)
        g2 = FONT_LARGE.render(f"Score: {self.score}", True, WHITE)
        surface.blit(g1, (SCREEN_WIDTH // 2 - g1.get_width() // 2, 200))
        surface.blit(g2, (SCREEN_WIDTH // 2 - g2.get_width() // 2, 290))

        if self.score >= self.high_score and self.score > 0:
            hs = FONT_MID.render("NEW HIGH SCORE!", True, YELLOW)
            surface.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2, 345))

        best = FONT_MID.render(f"Best: {self.high_score}", True, YELLOW)
        surface.blit(best, (SCREEN_WIDTH // 2 - best.get_width() // 2, 385))

        r1 = FONT_MID.render("[ SPACE ] Play Again", True, CYAN)
        r2 = FONT_SMALL.render("[ ESC ] Back to Menu", True, GRAY)
        surface.blit(r1, (SCREEN_WIDTH // 2 - r1.get_width() // 2, 460))
        surface.blit(r2, (SCREEN_WIDTH // 2 - r2.get_width() // 2, 500))

    # ── Main Loop ─────────────────────────────────────────────────────────────

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

# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()
