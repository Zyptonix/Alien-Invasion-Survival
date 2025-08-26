from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import math
from OpenGL.GLUT import (
    GLUT_BITMAP_HELVETICA_18,
    GLUT_BITMAP_HELVETICA_12,
    GLUT_BITMAP_HELVETICA_10,
    GLUT_BITMAP_9_BY_15,
)

# =============================
# Global / Config
# =============================
camera_pos = [0.0, 400.0, 400.0]
fovY = 60
GRID_LENGTH = 400

# Theme colors
SPACE_BLUE    = (0.1, 0.1, 0.3)
NEON_CYAN     = (0.0, 1.0, 1.0)
NEON_GREEN    = (0.0, 1.0, 0.2)
NEON_PINK     = (1.0, 0.0, 0.8)
ALIEN_GREEN   = (0.2, 1.0, 0.2)
WARNING_RED   = (1.0, 0.2, 0.2)
ENERGY_YELLOW = (1.0, 1.0, 0.0)

# Player
player_pos = [0.0, 0.0, 20.0]
player_angle = 0.0
player_health = 100
player_max_health = 100
player_speed = 4.0

# Game state
current_score = 0
game_time = 0
ui_pulse = 0.0
star_positions = []

# Weapon / bullets
bullets = []
weapon_cooldown = 0
max_weapon_cooldown = 15
bullet_speed = 8
muzzle_flash_timer = 0

# Evasion (Q/E)
is_evading = False
evade_timer = 0
evade_cooldown = 0
evade_direction = 0  # -1 = left, +1 = right
EVADE_DISTANCE = 40
EVADE_DURATION = 10
EVADE_COOLDOWN_MAX = 50

# Enemies / combat
BULLET_DAMAGE = 15           # a bit stronger for snappier kills
ENEMY_SPEED = 0.35           # slowed down from 0.6
ENEMY_RADIUS = 7.0           # slightly larger to feel fairer
TARGET_ENEMY_COUNT = 5       # keep this many enemies alive (auto-respawn)

# =============================
# Classes
# =============================
class Bullet:
    def __init__(self, x, y, z, angle):
        self.x = x
        self.y = y
        self.z = z
        self.angle = angle
        self.speed = bullet_speed
        self.life = 150
        self.active = True

    def update(self):
        if not self.active:
            return
        self.x += math.cos(math.radians(self.angle)) * self.speed
        self.y += math.sin(math.radians(self.angle)) * self.speed
        self.life -= 1
        if self.life <= 0:
            self.active = False
        # Out of bounds
        if abs(self.x) > GRID_LENGTH * 1.8 or abs(self.y) > GRID_LENGTH * 1.8:
            self.active = False

    def draw(self):
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glow = 0.8 + 0.2 * math.sin(game_time * 0.5)
        glColor3f(0.0, glow, 1.0)  # cyan energy core
        gluSphere(gluNewQuadric(), 1.6, 10, 8)
        # Tiny trail
        glColor3f(0.3, 0.6, 1.0)
        for i in range(3):
            trail_offset = i * 3.0
            tx = self.x - math.cos(math.radians(self.angle)) * trail_offset
            ty = self.y - math.sin(math.radians(self.angle)) * trail_offset
            glPushMatrix()
            glTranslatef(tx - self.x, ty - self.y, 0.0)
            alpha = max(0.0, 0.6 - i * 0.2)
            glColor3f(0.0, alpha, min(1.0, alpha * 1.5))
            gluSphere(gluNewQuadric(), max(0.1, 1.0 - i * 0.2), 6, 4)
            glPopMatrix()
        glPopMatrix()

class Enemy:
    def __init__(self, x, y, z=20.0, hp=30):
        self.x = x
        self.y = y
        self.z = z
        self.hp = hp
        self.alive = True
        self.radius = ENEMY_RADIUS

    def update(self):
        if not self.alive:
            return
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist = math.hypot(dx, dy) + 1e-6
        step = ENEMY_SPEED
        self.x += (dx / dist) * step
        self.y += (dy / dist) * step
        # clamp inside arena
        self.x = max(-GRID_LENGTH + 25, min(GRID_LENGTH - 25, self.x))
        self.y = max(-GRID_LENGTH + 25, min(GRID_LENGTH - 25, self.y))

    def draw(self):
        if not self.alive:
            return
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        # body
        glColor3f(0.9, 0.2, 0.2)      # red alien core
        gluSphere(gluNewQuadric(), self.radius, 12, 10)
        # antenna
        glColor3f(1.0, 0.7, 0.2)
        glPushMatrix()
        glTranslatef(0.0, 0.0, 5.0)
        gluCylinder(gluNewQuadric(), 1.2, 0.3, 6.0, 8, 2)
        glPopMatrix()
        glPopMatrix()

enemies = []

# =============================
# Enemy helpers
# =============================
def _random_edge_spawn():
    """Return (x, y) near an arena edge for spawning."""
    side = random.choice([-1, 1])
    if random.random() < 0.5:
        x = side * random.uniform(GRID_LENGTH * 0.6, GRID_LENGTH * 0.9)
        y = random.uniform(-GRID_LENGTH * 0.9, GRID_LENGTH * 0.9)
    else:
        x = random.uniform(-GRID_LENGTH * 0.9, GRID_LENGTH * 0.9)
        y = side * random.uniform(GRID_LENGTH * 0.6, GRID_LENGTH * 0.9)
    return x, y

def spawn_enemies(n=TARGET_ENEMY_COUNT):
    """Spawn up to n enemies (replaces the list)."""
    global enemies
    enemies = []
    for _ in range(n):
        x, y = _random_edge_spawn()
        enemies.append(Enemy(x, y))

def spawn_one_enemy():
    """Spawn a single enemy at the edge."""
    x, y = _random_edge_spawn()
    enemies.append(Enemy(x, y))

def update_enemies():
    for e in enemies:
        e.update()

def draw_enemies():
    for e in enemies:
        e.draw()

# =============================
# Stars / background
# =============================
def init_stars():
    global star_positions
    star_positions = []
    for _ in range(100):
        x = random.uniform(-GRID_LENGTH * 2, GRID_LENGTH * 2)
        y = random.uniform(-GRID_LENGTH * 2, GRID_LENGTH * 2)
        z = random.uniform(50, 200)
        size = random.uniform(1, 3)  # kept for extensibility
        star_positions.append([x, y, z, size])

def draw_stars():
    glPointSize(2.0)
    glBegin(GL_POINTS)
    for star in star_positions:
        alpha = 0.5 + 0.3 * math.sin(game_time * 0.1 + star[0] * 0.01)
        glColor3f(alpha, alpha, min(1.0, alpha * 1.2))
        glVertex3f(star[0], star[1], star[2])
    glEnd()

def draw_space_grid():
    glLineWidth(1.0)
    grid = 50
    glColor3f(0.3, 0.6, 1.0)
    glBegin(GL_LINES)
    for i in range(-GRID_LENGTH, GRID_LENGTH + 1, grid):
        glVertex3f(i, -GRID_LENGTH, 0.0)
        glVertex3f(i,  GRID_LENGTH, 0.0)
    for i in range(-GRID_LENGTH, GRID_LENGTH + 1, grid):
        glVertex3f(-GRID_LENGTH, i, 0.0)
        glVertex3f( GRID_LENGTH, i, 0.0)
    glEnd()
    glLineWidth(3.0)
    pulse = 0.7 + 0.3 * math.sin(game_time * 0.05)
    glColor3f(0.0, pulse, pulse)
    glBegin(GL_LINES)
    glVertex3f(-100, 0, 1); glVertex3f(100, 0, 1)
    glVertex3f(0, -100, 1); glVertex3f(0, 100, 1)
    glEnd()
    glLineWidth(1.0)

def draw_arena_boundaries():
    glLineWidth(4.0)
    pulse = 0.5 + 0.5 * math.sin(game_time * 0.08)
    glColor3f(pulse, 0.0, pulse)
    glBegin(GL_LINE_LOOP)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 10.0)
    glVertex3f( GRID_LENGTH, -GRID_LENGTH, 10.0)
    glVertex3f( GRID_LENGTH,  GRID_LENGTH, 10.0)
    glVertex3f(-GRID_LENGTH,  GRID_LENGTH, 10.0)
    glEnd()
    # Corners
    corner = 30
    glBegin(GL_LINES)
    # TL
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 10); glVertex3f(-GRID_LENGTH + corner, GRID_LENGTH, 10)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 10); glVertex3f(-GRID_LENGTH, GRID_LENGTH - corner, 10)
    # TR
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 10); glVertex3f(GRID_LENGTH - corner, GRID_LENGTH, 10)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 10); glVertex3f(GRID_LENGTH, GRID_LENGTH - corner, 10)
    # BR
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 10); glVertex3f(GRID_LENGTH - corner, -GRID_LENGTH, 10)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 10); glVertex3f(GRID_LENGTH, -GRID_LENGTH + corner, 10)
    # BL
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 10); glVertex3f(-GRID_LENGTH + corner, -GRID_LENGTH, 10)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 10); glVertex3f(-GRID_LENGTH, -GRID_LENGTH + corner, 10)
    glEnd()
    glLineWidth(1.0)

# =============================
# Weapon / bullets
# =============================
def fire_weapon():
    """Spawn bullet from the NOSE (front-center) aligned with ship facing."""
    global weapon_cooldown, muzzle_flash_timer
    if weapon_cooldown > 0:
        return False
    nose_forward = 18.0  # a bit ahead of the cockpit
    bx = player_pos[0] + math.cos(math.radians(player_angle)) * nose_forward
    by = player_pos[1] + math.sin(math.radians(player_angle)) * nose_forward
    bz = player_pos[2]
    bullets.append(Bullet(bx, by, bz, player_angle))
    weapon_cooldown = max_weapon_cooldown
    muzzle_flash_timer = 5
    return True

def _segment_point_dist2(x1, y1, x2, y2, px, py):
    """Squared distance from point P to segment [P1,P2] in 2D."""
    vx, vy = x2 - x1, y2 - y1
    wx, wy = px - x1, py - y1
    seg_len2 = vx*vx + vy*vy
    if seg_len2 <= 1e-9:
        dx, dy = px - x1, py - y1
        return dx*dx + dy*dy
    t = (wx*vx + wy*vy) / seg_len2
    if t < 0.0:   t = 0.0
    elif t > 1.0: t = 1.0
    cx, cy = x1 + t*vx, y1 + t*vy
    dx, dy = px - cx, py - cy
    return dx*dx + dy*dy

def draw_bullets():
    """Update bullets, check swept collisions vs enemies, then draw."""
    global bullets, current_score
    for bullet in bullets[:]:
        prev_x, prev_y, prev_z = bullet.x, bullet.y, bullet.z
        bullet.update()

        if bullet.active:
            for e in enemies:
                if not e.alive:
                    continue
                # generous radius for arcade feel
                hit_r = e.radius + 2.0
                d2 = _segment_point_dist2(prev_x, prev_y, bullet.x, bullet.y, e.x, e.y)
                if d2 <= (hit_r * hit_r):
                    e.hp -= BULLET_DAMAGE
                    bullet.active = False
                    if e.hp <= 0:
                        e.alive = False
                        current_score += 10
                        # auto-respawn a new enemy at an edge
                        spawn_one_enemy()
                    break

        if bullet.active:
            bullet.draw()
        else:
            bullets.remove(bullet)

def draw_weapon_effects():
    """Single center muzzle flash at the nose."""
    global muzzle_flash_timer
    if muzzle_flash_timer <= 0:
        return
    flash = muzzle_flash_timer / 5.0
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(player_angle, 0.0, 0.0, 1.0)
    glColor3f(1.0, flash, 0.0)
    glPushMatrix()
    glTranslatef(0.0, 14.0, -1.0)  # slightly ahead
    gluSphere(gluNewQuadric(), 2.0 * flash, 10, 8)
    glPopMatrix()
    glPopMatrix()
    muzzle_flash_timer -= 1

# =============================
# Player draw / HUD
# =============================
def draw_3d_player():
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(player_angle, 0.0, 0.0, 1.0)

    # Flash during evasion
    if is_evaving := is_evading:
        glColor3f(1.0, 1.0, 0.3)
    else:
        glColor3f(0.2, 0.8, 1.0)

    # Hull
    glPushMatrix()
    glScalef(1.5, 3.0, 0.8)
    gluSphere(gluNewQuadric(), 8.0, 12, 8)
    glPopMatrix()

    # Cockpit
    glColor3f(0.1, 0.3, 0.8)
    glPushMatrix(); glTranslatef(0.0, 12.0, 3.0); glScalef(0.8, 1.2, 0.6)
    gluSphere(gluNewQuadric(), 6.0, 10, 8); glPopMatrix()

    # Wings
    glColor3f(0.15, 0.6, 0.9)
    glPushMatrix(); glTranslatef(-12.0, -2.0, 0.0); glRotatef(90, 0, 1, 0); glScalef(0.3, 1.8, 2.0); glutSolidCube(8.0); glPopMatrix()
    glPushMatrix(); glTranslatef( 12.0, -2.0, 0.0); glRotatef(90, 0, 1, 0); glScalef(0.3, 1.8, 2.0); glutSolidCube(8.0); glPopMatrix()

    # Engines
    glColor3f(0.3, 0.3, 0.3)
    glPushMatrix(); glTranslatef(-8.0, -12.0, 0.0); glRotatef(90, 1, 0, 0); gluCylinder(gluNewQuadric(), 3.0, 2.0, 8.0, 8, 4); glPopMatrix()
    glPushMatrix(); glTranslatef( 8.0, -12.0, 0.0); glRotatef(90, 1, 0, 0); gluCylinder(gluNewQuadric(), 3.0, 2.0, 8.0, 8, 4); glPopMatrix()

    glow = 0.6 + 0.4 * math.sin(game_time * 0.2)
    glColor3f(0.0, glow, 1.0); glPushMatrix(); glTranslatef(-8.0, -18.0, 0.0); gluSphere(gluNewQuadric(), 4.0, 8, 6); glPopMatrix()
    glPushMatrix(); glTranslatef( 8.0, -18.0, 0.0); gluSphere(gluNewQuadric(), 4.0, 8, 6); glPopMatrix()
    glColor3f(glow, glow * 0.8, 1.0); glPushMatrix(); glTranslatef(0.0, -16.0, 1.0); gluSphere(gluNewQuadric(), 2.5, 8, 6); glPopMatrix()

    # Weapons (visual mounts)
    glColor3f(0.8, 0.8, 0.8)
    glPushMatrix(); glTranslatef(-6.0, 8.0, -1.0); glRotatef(90, 1, 0, 0); gluCylinder(gluNewQuadric(), 1.0, 0.5, 4.0, 6, 4); glPopMatrix()
    glPushMatrix(); glTranslatef( 6.0, 8.0, -1.0); glRotatef(90, 1, 0, 0); gluCylinder(gluNewQuadric(), 1.0, 0.5, 4.0, 6, 4); glPopMatrix()

    # Wingtip strobes
    strobe = (math.sin(game_time * 0.4) > 0.5)
    if strobe: glColor3f(1.0, 0.0, 0.0)
    else:      glColor3f(0.3, 0.0, 0.0)
    glPushMatrix(); glTranslatef(-15.0, -2.0, 1.0); gluSphere(gluNewQuadric(), 1.2, 6, 6); glPopMatrix()
    if strobe: glColor3f(0.0, 1.0, 0.0)
    else:      glColor3f(0.0, 0.3, 0.0)
    glPushMatrix(); glTranslatef(15.0, -2.0, 1.0);  gluSphere(gluNewQuadric(), 1.2, 6, 6); glPopMatrix()

    # Cockpit window
    glColor3f(0.2, 0.4, 0.8)
    glPushMatrix(); glTranslatef(0.0, 15.0, 4.0); glScalef(0.6, 0.8, 0.3)
    gluSphere(gluNewQuadric(), 4.0, 8, 6); glPopMatrix()

    # Fin
    glColor3f(0.1, 0.5, 0.8)
    glPushMatrix(); glTranslatef(0.0, 0.0, 8.0); glRotatef(90, 1, 0, 0); glScalef(0.2, 1.5, 1.0); glutSolidCube(6.0); glPopMatrix()

    # Shadow quad
    glColor3f(0.05, 0.05, 0.15)
    glPushMatrix(); glTranslatef(0.0, 0.0, -2.0); glScalef(1.8, 3.5, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(-5, -8, 0); glVertex3f(5, -8, 0); glVertex3f(5, 8, 0); glVertex3f(-5, 8, 0)
    glEnd()
    glPopMatrix()
    glPopMatrix()

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_12):
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_space_hud():
    global ui_pulse
    ui_pulse += 0.1

    # Left panel
    glColor3f(*NEON_CYAN); draw_text(15, 750, "=== SHIP STATUS ===", GLUT_BITMAP_HELVETICA_18)
    health_ratio = player_health / float(player_max_health)
    if health_ratio > 0.6:   glColor3f(*NEON_GREEN);    status_text = "OPTIMAL"
    elif health_ratio > 0.3: glColor3f(*ENERGY_YELLOW); status_text = "DAMAGED"
    else:                    glColor3f(*WARNING_RED);   status_text = "CRITICAL"
    draw_text(15, 720, f"HULL INTEGRITY: {int(health_ratio * 100)}%", GLUT_BITMAP_HELVETICA_12)
    draw_text(15, 700, f"STATUS: {status_text}", GLUT_BITMAP_HELVETICA_12)

    # Weapons
    if weapon_cooldown > 0:
        glColor3f(*WARNING_RED); draw_text(15, 680, "WEAPONS: CHARGING", GLUT_BITMAP_HELVETICA_12)
    else:
        glColor3f(*NEON_GREEN);  draw_text(15, 680, "WEAPONS: READY", GLUT_BITMAP_HELVETICA_12)

    # Evade status
    if evade_cooldown > 0:
        glColor3f(*ENERGY_YELLOW); draw_text(15, 660, f"EVADE: COOLDOWN {evade_cooldown}", GLUT_BITMAP_HELVETICA_12)
    else:
        glColor3f(*NEON_GREEN);    draw_text(15, 660, "EVADE: READY (Q/E)", GLUT_BITMAP_HELVETICA_12)

    # Center top
    glColor3f(*NEON_PINK);      draw_text(400, 750, "ALIEN INVASION SURVIVAL", GLUT_BITMAP_HELVETICA_18)
    glColor3f(*ENERGY_YELLOW);  draw_text(420, 720, f"WAVE: 1  |  SCORE: {current_score}", GLUT_BITMAP_HELVETICA_12)
    pulse = 0.7 + 0.3 * math.sin(ui_pulse)
    glColor3f(pulse, 1.0, pulse); draw_text(450, 700, "MISSION: SURVIVE", GLUT_BITMAP_HELVETICA_12)

    # Right panel
    live_count = sum(1 for e in enemies if e.alive)
    glColor3f(*NEON_CYAN);   draw_text(720, 750, "=== TACTICAL ===", GLUT_BITMAP_HELVETICA_18)
    glColor3f(*ALIEN_GREEN); draw_text(720, 720, f"ENEMIES: {live_count} ACTIVE", GLUT_BITMAP_HELVETICA_12)
    threat = "LOW" if live_count <= 2 else ("MEDIUM" if live_count <= 5 else "HIGH")
    draw_text(720, 700, f"THREAT LEVEL: {threat}", GLUT_BITMAP_HELVETICA_12)
    draw_text(720, 680, f"PROJECTILES: {len(bullets)}", GLUT_BITMAP_HELVETICA_12)

    # Help
    glColor3f(0.7, 0.7, 1.0)
    draw_text(15, 150, "=== CONTROLS ===", GLUT_BITMAP_HELVETICA_12)
    draw_text(15, 130, "WASD: Navigate Ship", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 110, "SPACE / LMB: Fire Weapons", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 90,  "Q/E: Evasive Maneuvers", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 70,  "ARROWS: Camera Control", GLUT_BITMAP_HELVETICA_10)

# =============================
# Input
# =============================
def keyboardListener(key, x, y):
    global player_pos, player_angle, is_evading, evade_timer, evade_cooldown, evade_direction
    # Movement
    if key == b'w':
        nx = player_pos[0] + math.cos(math.radians(player_angle)) * player_speed
        ny = player_pos[1] + math.sin(math.radians(player_angle)) * player_speed
        if abs(nx) < GRID_LENGTH - 30 and abs(ny) < GRID_LENGTH - 30:
            player_pos[0], player_pos[1] = nx, ny
    if key == b's':
        nx = player_pos[0] - math.cos(math.radians(player_angle)) * player_speed
        ny = player_pos[1] - math.sin(math.radians(player_angle)) * player_speed
        if abs(nx) < GRID_LENGTH - 30 and abs(ny) < GRID_LENGTH - 30:
            player_pos[0], player_pos[1] = nx, ny
    if key == b'a':
        player_angle += 3.0
    if key == b'd':
        player_angle -= 3.0
    if key == b' ':
        fire_weapon()

    # Evasion
    if key == b'q' and evade_cooldown <= 0 and not is_evading:
        is_evading = True
        evade_timer = EVADE_DURATION
        evade_cooldown = EVADE_COOLDOWN_MAX
        evade_direction = -1
    if key == b'e' and evade_cooldown <= 0 and not is_evading:
        is_evading = True
        evade_timer = EVADE_DURATION
        evade_cooldown = EVADE_COOLDOWN_MAX
        evade_direction = 1

def specialKeyListener(key, x, y):
    global camera_pos
    cx, cy, cz = camera_pos
    if key == GLUT_KEY_UP:    cz += 15
    if key == GLUT_KEY_DOWN:  cz = max(100, cz - 15)
    if key == GLUT_KEY_LEFT:  cx -= 15
    if key == GLUT_KEY_RIGHT: cx += 15
    camera_pos = [cx, cy, cz]

def mouseListener(button, state, x, y):
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        fire_weapon()

# =============================
# Camera / Loop / Display
# =============================
def setupCamera():
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 2000.0)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    x, y, z = camera_pos
    gluLookAt(x, y, z, player_pos[0], player_pos[1], 0.0, 0.0, 0.0, 1.0)

def idle():
    global game_time, weapon_cooldown, is_evading, evade_timer, evade_cooldown
    game_time += 1

    # ROF cooldown
    if weapon_cooldown > 0:
        weapon_cooldown -= 1

    # Evasion slide (perpendicular to facing)
    if is_evading:
        angle_rad = math.radians(player_angle + 90 * evade_direction)
        step = EVADE_DISTANCE / float(EVADE_DURATION)
        player_pos[0] += math.cos(angle_rad) * step
        player_pos[1] += math.sin(angle_rad) * step
        # clamp
        player_pos[0] = max(-GRID_LENGTH + 30, min(GRID_LENGTH - 30, player_pos[0]))
        player_pos[1] = max(-GRID_LENGTH + 30, min(GRID_LENGTH - 30, player_pos[1]))
        evade_timer -= 1
        if evade_timer <= 0:
            is_evading = False
    if evade_cooldown > 0:
        evade_cooldown -= 1

    # Enemies
    update_enemies()

    glutPostRedisplay()

def showScreen():
    glClearColor(*SPACE_BLUE, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)

    setupCamera()
    draw_stars()
    draw_space_grid()
    draw_arena_boundaries()
    draw_enemies()       # enemies under ship
    draw_3d_player()
    draw_bullets()
    draw_weapon_effects()
    draw_space_hud()
    glutSwapBuffers()

# =============================
# Main
# =============================
def main():
    init_stars()
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Alien Invasion Survival - Space Combat")
    glEnable(GL_DEPTH_TEST)  # allowed for visualization

    spawn_enemies(TARGET_ENEMY_COUNT)  # keep a baseline number

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()

if __name__ == "__main__":
    main()

