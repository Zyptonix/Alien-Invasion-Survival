from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import math
import os
from datetime import datetime
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
camera_shake_timer = 0
camera_shake_intensity = 0.0
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
player_radius = 12.0  # Added player collision radius

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
BULLET_DAMAGE = 15           # base damage, now modified by skills
ENEMY_SPEED = 0.35           
ENEMY_RADIUS = 7.0           
TARGET_ENEMY_COUNT = 5
ENEMY_DAMAGE = 15            # Damage enemies deal to player

# Overheat system
heat_level = 0
heat_max = 100
heat_per_shot = 12
heat_cool_rate = 1
overheated = False

# High-Score System
HIGHSCORE_FILE = "highscores.txt"
high_scores = []
max_highscores = 10
game_over = False
player_name = ""
name_input_mode = False

# Stamina System
stamina_level = 100
stamina_max = 100
stamina_regen_rate = 0.8
stamina_sprint_drain = 2.0
stamina_evade_cost = 25
is_sprinting = False
fatigued = False
fatigue_threshold = 20
sprint_speed_multiplier = 1.8
sprint_accuracy_penalty = 0.7
fatigue_speed_penalty = 0.6

# Skill System
player_level = 1
experience_points = 0
experience_to_next_level = 100
skill_points = 0
skill_faster_evasion = 0
skill_weapon_power = 0
skill_heat_management = 0
skill_stamina_efficiency = 0
skill_health_boost = 0
special_ability_meter = 0
special_ability_max = 100
special_ability_active = False
special_ability_timer = 0
current_special = "DAMAGE_BOOST"
skill_menu_open = False

SKILL_COSTS = {
    'faster_evasion': [1, 2, 3],
    'weapon_power': [1, 2, 4],
    'heat_management': [1, 2, 3],
    'stamina_efficiency': [1, 3, 4],
    'health_boost': [2, 3, 5]
}

SPECIAL_ABILITIES = ["DAMAGE_BOOST", "TELEPORT", "INVINCIBILITY"]

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
        self.damage = get_weapon_damage() if 'get_weapon_damage' in globals() else BULLET_DAMAGE

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
        
        # Check for invincibility special ability
        if special_ability_active and current_special == "INVINCIBILITY":
            return  # Don't move toward invincible player
            
        # Calculate movement toward player - ALWAYS move toward player
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist = math.hypot(dx, dy) + 1e-6
        
        step = ENEMY_SPEED
        self.x += (dx / dist) * step
        self.y += (dy / dist) * step
        
        # Clamp inside arena with better bounds
        bound_limit = GRID_LENGTH - 25
        self.x = max(-bound_limit, min(bound_limit, self.x))
        self.y = max(-bound_limit, min(bound_limit, self.y))

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
# Player-Enemy Collision Function
# =============================
def check_player_enemy_collision():
    """Check for collisions between player and enemies with camera shake instead of knockback."""
    global player_health, enemies, camera_shake_timer, camera_shake_intensity
    
    # Skip collision if player is invincible
    if special_ability_active and current_special == "INVINCIBILITY":
        return
    
    # Skip collision during evasion (brief invincibility frames)
    if is_evading:
        return
    
    enemies_to_remove = []  # Track enemies to remove
    
    for i, enemy in enumerate(enemies):
        if not enemy.alive:
            continue
            
        # Calculate distance between player and enemy
        dx = player_pos[0] - enemy.x
        dy = player_pos[1] - enemy.y
        distance = math.hypot(dx, dy)
        
        # Precise collision detection
        collision_distance = player_radius + enemy.radius
        
        if distance <= collision_distance:
            # Player takes damage
            player_health -= ENEMY_DAMAGE
            
            # Trigger camera shake instead of player knockback
            camera_shake_timer = 30  # Shake for 30 frames (0.5 seconds at 60fps)
            camera_shake_intensity = 15.0  # Shake intensity
            
            # Mark enemy for removal
            enemies_to_remove.append(i)
            
            # Only process one collision per frame
            break
    
    # Remove collided enemies and spawn replacements
    for i in reversed(enemies_to_remove):
        if i < len(enemies):
            enemies[i].alive = False
            spawn_enemy_at_safe_distance()

def update_camera_shake():
    """Update camera shake effect."""
    global camera_shake_timer, camera_shake_intensity
    
    if camera_shake_timer > 0:
        camera_shake_timer -= 1
        # Gradually reduce shake intensity
        camera_shake_intensity *= 0.9
        
        if camera_shake_timer <= 0:
            camera_shake_intensity = 0.0

def spawn_enemy_at_safe_distance():
    """Spawn an enemy at a safe distance from the player."""
    max_attempts = 10
    min_safe_distance = 100.0  # Minimum distance from player
    
    for _ in range(max_attempts):
        x, y = _random_edge_spawn()
        
        # Check distance from player
        dx = player_pos[0] - x
        dy = player_pos[1] - y
        distance = math.hypot(dx, dy)
        
        if distance >= min_safe_distance:
            enemies.append(Enemy(x, y))
            return
    
    # Fallback: force spawn at a guaranteed safe location
    angle = random.uniform(0, 2 * math.pi)
    safe_distance = min_safe_distance + 50
    x = player_pos[0] + math.cos(angle) * safe_distance
    y = player_pos[1] + math.sin(angle) * safe_distance
    
    # Clamp to arena bounds
    x = max(-GRID_LENGTH + 25, min(GRID_LENGTH - 25, x))
    y = max(-GRID_LENGTH + 25, min(GRID_LENGTH - 25, y))
    
    enemies.append(Enemy(x, y))

# =============================
# High-Score Functions
# =============================
def load_high_scores():
    """Load high scores from file."""
    global high_scores
    high_scores = []
    
    if not os.path.exists(HIGHSCORE_FILE):
        return
    
    try:
        with open(HIGHSCORE_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 3:
                    score = int(parts[0])
                    name = parts[1]
                    date = parts[2]
                    high_scores.append((score, name, date))
        
        # Sort by score (highest first)
        high_scores.sort(key=lambda x: x[0], reverse=True)
        high_scores = high_scores[:max_highscores]  # Keep only top 10
        
    except Exception as e:
        print(f"Error loading high scores: {e}")
        high_scores = []

def save_high_score(score, name):
    """Save a new high score."""
    global high_scores
    
    # Add current score
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    high_scores.append((score, name, current_date))
    
    # Sort and keep top scores
    high_scores.sort(key=lambda x: x[0], reverse=True)
    high_scores = high_scores[:max_highscores]
    
    # Write to file
    try:
        with open(HIGHSCORE_FILE, 'w') as f:
            for score, name, date in high_scores:
                f.write(f"{score}|{name}|{date}\n")
    except Exception as e:
        print(f"Error saving high scores: {e}")

def is_high_score(score):
    """Check if the current score qualifies as a high score."""
    if len(high_scores) < max_highscores:
        return True
    return score > high_scores[-1][0] if high_scores else True

def draw_high_scores():
    """Draw the high scores table on screen."""
    if not high_scores:
        return
    
    # Title
    glColor3f(*NEON_PINK)
    draw_text(720, 600, "=== HIGH SCORES ===", GLUT_BITMAP_HELVETICA_18)
    
    # Scores
    y_pos = 570
    for i, (score, name, date) in enumerate(high_scores[:5]):  # Show top 5
        if i == 0:
            glColor3f(*ENERGY_YELLOW)  # Gold for #1
        elif i <= 2:
            glColor3f(*NEON_CYAN)      # Cyan for top 3
        else:
            glColor3f(0.7, 0.7, 0.7)   # Gray for others
        
        # Truncate name if too long
        display_name = name[:8] if len(name) > 8 else name
        score_text = f"{i+1}. {display_name}: {score}"
        draw_text(720, y_pos, score_text, GLUT_BITMAP_HELVETICA_10)
        y_pos -= 20

def draw_game_over_screen():
    """Draw game over text overlay without clearing the background."""
    global name_input_mode, player_name
    
    # Game Over text with pulsing effect (no background overlay)
    pulse = 0.7 + 0.3 * math.sin(game_time * 0.1)
    glColor3f(pulse, 0.0, 0.0)
    draw_text(350, 500, "GAME OVER", GLUT_BITMAP_HELVETICA_18)
    
    glColor3f(*NEON_CYAN)
    draw_text(400, 460, f"FINAL SCORE: {current_score}", GLUT_BITMAP_HELVETICA_12)
    
    if is_high_score(current_score):
        if name_input_mode:
            glColor3f(*ENERGY_YELLOW)
            draw_text(300, 420, "NEW HIGH SCORE! Enter your name:", GLUT_BITMAP_HELVETICA_12)
            glColor3f(*NEON_GREEN)
            draw_text(350, 390, f"Name: {player_name}_", GLUT_BITMAP_HELVETICA_12)
            glColor3f(0.9, 0.9, 0.9)
            draw_text(320, 360, "Press ENTER to save, BACKSPACE to delete", GLUT_BITMAP_HELVETICA_10)
        else:
            glColor3f(*NEON_GREEN)
            draw_text(380, 420, "High Score Saved!", GLUT_BITMAP_HELVETICA_12)
    
    glColor3f(0.9, 0.9, 0.9)
    draw_text(400, 300, "Press R to restart", GLUT_BITMAP_HELVETICA_12)
    draw_text(400, 280, "Press ESC to quit", GLUT_BITMAP_HELVETICA_12)

def handle_player_death():
    """Handle when player dies."""
    global game_over, name_input_mode, player_health, camera_shake_timer, camera_shake_intensity
    
    if player_health <= 0 and not game_over:
        # Clamp health to 0 so it doesn't go negative
        player_health = 0
        game_over = True
        
        # Stop camera shake when game ends
        camera_shake_timer = 0
        camera_shake_intensity = 0.0
        
        if is_high_score(current_score):
            name_input_mode = True

# =============================
# Stamina Functions
# =============================
def update_stamina():
    """Update stamina levels and fatigue state."""
    global stamina_level, fatigued, is_sprinting
    
    if is_sprinting and stamina_level > 0:
        stamina_level -= stamina_sprint_drain
        if stamina_level < 0:
            stamina_level = 0
            is_sprinting = False  # Auto-stop sprinting when exhausted
    else:
        # Regenerate stamina when not sprinting
        if stamina_level < stamina_max:
            stamina_level += stamina_regen_rate
            if stamina_level > stamina_max:
                stamina_level = stamina_max
    
    # Update fatigue state
    fatigued = stamina_level < fatigue_threshold

def get_current_speed():
    """Get player speed based on sprint/fatigue state."""
    base_speed = player_speed
    
    if fatigued:
        return base_speed * fatigue_speed_penalty
    elif is_sprinting:
        return base_speed * sprint_speed_multiplier
    else:
        return base_speed

def can_evade():
    """Check if player has enough stamina to evade."""
    return stamina_level >= stamina_evade_cost

def consume_evade_stamina():
    """Consume stamina for evasion."""
    global stamina_level
    stamina_level -= stamina_evade_cost
    if stamina_level < 0:
        stamina_level = 0

# =============================
# Skill System Functions
# =============================
def gain_experience(points):
    """Gain experience points and handle leveling up."""
    global experience_points, player_level, experience_to_next_level, skill_points
    
    experience_points += points
    
    # Check for level up
    while experience_points >= experience_to_next_level:
        experience_points -= experience_to_next_level
        player_level += 1
        skill_points += 1
        experience_to_next_level = int(experience_to_next_level * 1.2)  # Increase XP requirement

def can_upgrade_skill(skill_name):
    """Check if a skill can be upgraded."""
    skill_level = globals()[f'skill_{skill_name}']
    if skill_level >= 3:  # Max level
        return False
    cost = SKILL_COSTS[skill_name][skill_level]
    return skill_points >= cost

def upgrade_skill(skill_name):
    """Upgrade a skill if possible."""
    global skill_points
    
    if not can_upgrade_skill(skill_name):
        return False
    
    skill_level = globals()[f'skill_{skill_name}']
    cost = SKILL_COSTS[skill_name][skill_level]
    
    globals()[f'skill_{skill_name}'] += 1
    skill_points -= cost
    
    # Apply skill effects
    apply_skill_effects()
    return True

def apply_skill_effects():
    """Apply all skill effects to game variables."""
    global player_max_health, heat_cool_rate, stamina_regen_rate, stamina_sprint_drain
    
    # Health boost
    base_health = 100
    player_max_health = base_health + (skill_health_boost * 25)
    
    # Heat management
    base_cool_rate = 1
    heat_cool_rate = base_cool_rate + (skill_heat_management * 0.5)
    
    # Stamina efficiency
    base_regen = 0.8
    base_drain = 2.0
    stamina_regen_rate = base_regen + (skill_stamina_efficiency * 0.3)
    stamina_sprint_drain = max(0.5, base_drain - (skill_stamina_efficiency * 0.4))

def get_weapon_damage():
    """Get current weapon damage with skill modifiers."""
    base_damage = 15
    return base_damage + (skill_weapon_power * 5)

def get_evade_cooldown():
    """Get evade cooldown with skill modifiers."""
    base_cooldown = 50
    return max(20, base_cooldown - (skill_faster_evasion * 10))

def charge_special_ability(amount):
    """Charge the special ability meter."""
    global special_ability_meter
    special_ability_meter = min(special_ability_max, special_ability_meter + amount)

def can_use_special_ability():
    """Check if special ability can be used."""
    return special_ability_meter >= special_ability_max and not special_ability_active

def activate_special_ability():
    """Activate the current special ability."""
    global special_ability_active, special_ability_timer, special_ability_meter
    
    if not can_use_special_ability():
        return False
    
    special_ability_active = True
    special_ability_timer = 180  # 3 seconds at 60 FPS
    special_ability_meter = 0
    
    return True

def update_special_ability():
    """Update special ability timer."""
    global special_ability_active, special_ability_timer
    
    if special_ability_active:
        special_ability_timer -= 1
        if special_ability_timer <= 0:
            special_ability_active = False

def cycle_special_ability():
    """Cycle through available special abilities."""
    global current_special
    
    current_index = SPECIAL_ABILITIES.index(current_special)
    current_special = SPECIAL_ABILITIES[(current_index + 1) % len(SPECIAL_ABILITIES)]

def enhanced_evasion():
    """Enhanced evasion with skill effects."""
    global is_evading, evade_timer, evade_cooldown
    
    if not can_evade():
        return False
    
    is_evading = True
    evade_timer = EVADE_DURATION
    evade_cooldown = get_evade_cooldown()  # Use skill-modified cooldown
    consume_evade_stamina()
    
    # Special teleport ability
    if special_ability_active and current_special == "TELEPORT":
        # Instant teleport to a safe location
        safe_x = random.uniform(-GRID_LENGTH * 0.5, GRID_LENGTH * 0.5)
        safe_y = random.uniform(-GRID_LENGTH * 0.5, GRID_LENGTH * 0.5)
        player_pos[0] = safe_x
        player_pos[1] = safe_y
        is_evading = False  # No roll animation needed
    
    return True

def draw_skill_menu():
    """Draw the skill upgrade menu."""
    if not skill_menu_open:
        return
    
    # Dark overlay
    glColor3f(0.0, 0.0, 0.0)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    
    glBegin(GL_QUADS)
    glVertex2f(200, 150)
    glVertex2f(800, 150)
    glVertex2f(800, 650)
    glVertex2f(200, 650)
    glEnd()
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    
    # Title
    glColor3f(*NEON_CYAN)
    draw_text(450, 620, "SKILL UPGRADES", GLUT_BITMAP_HELVETICA_18)
    
    glColor3f(*ENERGY_YELLOW)
    draw_text(220, 590, f"Level: {player_level} | Skill Points: {skill_points} | XP: {experience_points}/{experience_to_next_level}", GLUT_BITMAP_HELVETICA_12)
    
    # Skills
    y_pos = 550
    skills = [
        ("faster_evasion", "Faster Evasion", "Reduces evasion cooldown"),
        ("weapon_power", "Weapon Power", "Increases bullet damage"),
        ("heat_management", "Heat Management", "Better weapon cooling"),
        ("stamina_efficiency", "Stamina Boost", "Improved stamina system"),
        ("health_boost", "Health Boost", "Increases maximum health")
    ]
    
    for i, (skill_name, display_name, description) in enumerate(skills):
        skill_level = globals()[f'skill_{skill_name}']
        can_upgrade = can_upgrade_skill(skill_name)
        
        if can_upgrade:
            glColor3f(*NEON_GREEN)
        elif skill_level >= 3:
            glColor3f(*NEON_PINK)  # Max level
        else:
            glColor3f(0.6, 0.6, 0.6)  # Can't afford
        
        # Skill info
        level_text = "MAX" if skill_level >= 3 else f"{skill_level}/3"
        cost_text = "" if skill_level >= 3 else f"Cost: {SKILL_COSTS[skill_name][skill_level]}"
        
        draw_text(220, y_pos, f"{i+1}. {display_name} [{level_text}] {cost_text}", GLUT_BITMAP_HELVETICA_12)
        glColor3f(0.8, 0.8, 0.8)
        draw_text(240, y_pos - 15, description, GLUT_BITMAP_HELVETICA_10)
        y_pos -= 50
    
    # Special ability section
    glColor3f(*NEON_PINK)
    draw_text(220, 300, "SPECIAL ABILITY", GLUT_BITMAP_HELVETICA_18)
    
    ability_color = NEON_GREEN if can_use_special_ability() else (0.6, 0.6, 0.6)
    glColor3f(*ability_color)
    draw_text(220, 270, f"Current: {current_special} | Charge: {int(special_ability_meter)}/{special_ability_max}", GLUT_BITMAP_HELVETICA_12)
    
    glColor3f(0.7, 0.7, 0.7)
    draw_text(220, 220, "Controls:", GLUT_BITMAP_HELVETICA_12)
    draw_text(220, 200, "1-5: Upgrade Skills | TAB: Cycle Special | F: Use Special", GLUT_BITMAP_HELVETICA_10)
    draw_text(220, 180, "ESC: Close Menu", GLUT_BITMAP_HELVETICA_10)

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
        size = random.uniform(1, 3)
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
    global weapon_cooldown, muzzle_flash_timer, heat_level, overheated
    if weapon_cooldown > 0 or overheated:
        return False

    # Calculate accuracy based on sprint state
    accuracy_modifier = 0.0
    if is_sprinting:
        accuracy_modifier = random.uniform(-15, 15) * (1.0 - sprint_accuracy_penalty)
    elif fatigued:
        accuracy_modifier = random.uniform(-8, 8)
    
    bullet_angle = player_angle + accuracy_modifier

    nose_forward = 18.0
    bx = player_pos[0] + math.cos(math.radians(player_angle)) * nose_forward
    by = player_pos[1] + math.sin(math.radians(player_angle)) * nose_forward
    bz = player_pos[2]
    bullets.append(Bullet(bx, by, bz, bullet_angle))

    weapon_cooldown = max_weapon_cooldown
    muzzle_flash_timer = 5

    # Add heat
    heat_level += heat_per_shot
    if heat_level >= heat_max:
        overheated = True
        heat_level = heat_max

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

def enhanced_bullet_enemy_collision():
    """Enhanced collision detection with XP and special ability charging."""
    global bullets, current_score
    
    for bullet in bullets[:]:
        prev_x, prev_y, prev_z = bullet.x, bullet.y, bullet.z
        bullet.update()

        if bullet.active:
            for e in enemies:
                if not e.alive:
                    continue
                
                hit_r = e.radius + 2.0
                d2 = _segment_point_dist2(prev_x, prev_y, bullet.x, bullet.y, e.x, e.y)
                if d2 <= (hit_r * hit_r):
                    # Use enhanced bullet damage
                    damage = bullet.damage
                    
                    # Special ability effects
                    if special_ability_active and current_special == "DAMAGE_BOOST":
                        damage *= 2
                    
                    e.hp -= damage
                    bullet.active = False
                    
                    if e.hp <= 0:
                        e.alive = False
                        current_score += 10
                        
                        # Gain experience and charge special ability
                        gain_experience(5)
                        charge_special_ability(8)
                        
                        # Auto-respawn a new enemy
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

    # Color based on state
    if special_ability_active and current_special == "INVINCIBILITY":
        glow = 0.5 + 0.5 * math.sin(game_time * 0.5)
        glColor3f(1.0, glow, 1.0)  # Pink invincibility glow
    elif is_evading:
        glColor3f(1.0, 1.0, 0.3)  # Yellow during evasion
    elif is_sprinting:
        glow = 0.7 + 0.3 * math.sin(game_time * 0.3)
        glColor3f(0.2, glow, 1.0)  # Pulsing blue during sprint
    elif fatigued:
        glColor3f(0.8, 0.4, 0.4)  # Reddish when fatigued
    else:
        glColor3f(0.2, 0.8, 1.0)  # Normal cyan

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

    # Enhanced engine effects based on state
    glow = 0.6 + 0.4 * math.sin(game_time * 0.2)
    if is_sprinting:
        # Brighter, more intense engine glow when sprinting
        glColor3f(0.2, glow * 1.5, 1.0)
        engine_size = 5.0
    elif fatigued:
        # Dimmer engines when fatigued
        glColor3f(0.1, glow * 0.5, 0.6)
        engine_size = 3.0
    else:
        glColor3f(0.0, glow, 1.0)
        engine_size = 4.0
    
    # Engine glows
    glPushMatrix(); glTranslatef(-8.0, -18.0, 0.0); gluSphere(gluNewQuadric(), engine_size, 8, 6); glPopMatrix()
    glPushMatrix(); glTranslatef( 8.0, -18.0, 0.0); gluSphere(gluNewQuadric(), engine_size, 8, 6); glPopMatrix()
    glColor3f(glow, glow * 0.8, 1.0); glPushMatrix(); glTranslatef(0.0, -16.0, 1.0); gluSphere(gluNewQuadric(), 2.5, 8, 6); glPopMatrix()

    # Sprint trail effect
    if is_sprinting:
        glColor3f(0.3, 0.7, 1.0)
        for i in range(5):
            trail_offset = (i + 1) * 8.0
            trail_alpha = max(0.1, 0.8 - i * 0.15)
            glColor3f(0.0, trail_alpha, trail_alpha * 1.2)
            glPushMatrix()
            glTranslatef(0.0, -16.0 - trail_offset, 1.0)
            glScalef(0.8 - i * 0.1, 0.8 - i * 0.1, 0.1)
            gluSphere(gluNewQuadric(), 3.0, 8, 6)
            glPopMatrix()

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

def draw_enhanced_hud():
    """Enhanced HUD with all new systems."""
    global ui_pulse
    ui_pulse += 0.1

    # Left panel - Ship Status
    glColor3f(*NEON_CYAN); draw_text(15, 750, "=== SHIP STATUS ===", GLUT_BITMAP_HELVETICA_18)
    
    # Health
    health_ratio = player_health / float(player_max_health)
    if health_ratio > 0.6:   glColor3f(*NEON_GREEN);    status_text = "OPTIMAL"
    elif health_ratio > 0.3: glColor3f(*ENERGY_YELLOW); status_text = "DAMAGED"
    else:                    glColor3f(*WARNING_RED);   status_text = "CRITICAL"
    draw_text(15, 720, f"HULL INTEGRITY: {int(health_ratio * 100)}%", GLUT_BITMAP_HELVETICA_12)
    draw_text(15, 700, f"STATUS: {status_text}", GLUT_BITMAP_HELVETICA_12)

    # Stamina
    stamina_ratio = stamina_level / float(stamina_max)
    if fatigued:
        glColor3f(*WARNING_RED)
        stamina_status = "FATIGUED"
    elif stamina_ratio > 0.6:
        glColor3f(*NEON_GREEN)
        stamina_status = "ENERGIZED"
    else:
        glColor3f(*ENERGY_YELLOW)
        stamina_status = "TIRED"
    
    draw_text(15, 680, f"STAMINA: {int(stamina_level)} / {stamina_max}", GLUT_BITMAP_HELVETICA_12)
    draw_text(15, 660, f"CONDITION: {stamina_status}", GLUT_BITMAP_HELVETICA_12)
    
    # Sprint indicator
    if is_sprinting:
        glColor3f(*NEON_PINK)
        draw_text(15, 640, "SPRINT: ACTIVE", GLUT_BITMAP_HELVETICA_12)
    else:
        glColor3f(0.6, 0.6, 0.6)
        draw_text(15, 640, "SPRINT: INACTIVE (C)", GLUT_BITMAP_HELVETICA_12)

    # Weapons
    if weapon_cooldown > 0:
        glColor3f(*WARNING_RED); draw_text(15, 620, "WEAPONS: CHARGING", GLUT_BITMAP_HELVETICA_12)
    else:
        glColor3f(*NEON_GREEN);  draw_text(15, 620, "WEAPONS: READY", GLUT_BITMAP_HELVETICA_12)

    # Evade status
    if evade_cooldown > 0:
        glColor3f(*ENERGY_YELLOW); draw_text(15, 600, f"EVADE: COOLDOWN {evade_cooldown}", GLUT_BITMAP_HELVETICA_12)
    elif not can_evade():
        glColor3f(*WARNING_RED);   draw_text(15, 600, "EVADE: LOW STAMINA", GLUT_BITMAP_HELVETICA_12)
    else:
        glColor3f(*NEON_GREEN);    draw_text(15, 600, "EVADE: READY (Q/E)", GLUT_BITMAP_HELVETICA_12)

    # Heat status
    if overheated:
        glColor3f(1.0, 0.2, 0.2)
        draw_text(15, 580, "WEAPON: OVERHEATED!", GLUT_BITMAP_HELVETICA_12)
    else:
        glColor3f(*ENERGY_YELLOW)
        draw_text(15, 580, f"HEAT: {int(heat_level)} / {heat_max}", GLUT_BITMAP_HELVETICA_12)

    # Center top
    glColor3f(*NEON_PINK);      draw_text(400, 750, "ALIEN INVASION SURVIVAL", GLUT_BITMAP_HELVETICA_18)
    glColor3f(*ENERGY_YELLOW);  draw_text(420, 720, f"WAVE: 1  |  SCORE: {current_score}", GLUT_BITMAP_HELVETICA_12)
    pulse = 0.7 + 0.3 * math.sin(ui_pulse)
    glColor3f(pulse, 1.0, pulse); draw_text(450, 700, "MISSION: SURVIVE", GLUT_BITMAP_HELVETICA_12)

    # Right panel - Tactical
    live_count = sum(1 for e in enemies if e.alive)
    glColor3f(*NEON_CYAN);   draw_text(720, 750, "=== TACTICAL ===", GLUT_BITMAP_HELVETICA_18)
    glColor3f(*ALIEN_GREEN); draw_text(720, 720, f"ENEMIES: {live_count} ACTIVE", GLUT_BITMAP_HELVETICA_12)
    threat = "LOW" if live_count <= 2 else ("MEDIUM" if live_count <= 5 else "HIGH")
    draw_text(720, 700, f"THREAT LEVEL: {threat}", GLUT_BITMAP_HELVETICA_12)
    draw_text(720, 680, f"PROJECTILES: {len(bullets)}", GLUT_BITMAP_HELVETICA_12)

    # Skill info section
    glColor3f(*NEON_PINK)
    draw_text(720, 450, "=== PILOT SKILLS ===", GLUT_BITMAP_HELVETICA_12)
    
    glColor3f(*ENERGY_YELLOW)
    draw_text(720, 430, f"Level: {player_level}", GLUT_BITMAP_HELVETICA_10)
    draw_text(720, 410, f"XP: {experience_points}/{experience_to_next_level}", GLUT_BITMAP_HELVETICA_10)
    draw_text(720, 390, f"Skill Points: {skill_points}", GLUT_BITMAP_HELVETICA_10)
    
    # Special ability status
    ability_color = NEON_GREEN if can_use_special_ability() else (0.6, 0.6, 0.6)
    glColor3f(*ability_color)
    draw_text(720, 360, f"Special: {current_special}", GLUT_BITMAP_HELVETICA_10)
    
    meter_percent = int((special_ability_meter / special_ability_max) * 100)
    draw_text(720, 340, f"Charge: {meter_percent}%", GLUT_BITMAP_HELVETICA_10)
    
    if special_ability_active:
        glColor3f(*WARNING_RED)
        draw_text(720, 320, "ABILITY ACTIVE!", GLUT_BITMAP_HELVETICA_10)

    # Enhanced Controls Help
    glColor3f(0.7, 0.7, 1.0)
    draw_text(15, 190, "=== CONTROLS ===", GLUT_BITMAP_HELVETICA_12)
    draw_text(15, 170, "WASD: Navigate Ship", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 150, "C: Sprint Toggle", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 130, "SPACE / LMB: Fire Weapons", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 110, "Q/E: Evasive Maneuvers", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 90,  "V: Skill Menu | F: Special | TAB: Cycle", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 70,  "ARROWS: Camera Control", GLUT_BITMAP_HELVETICA_10)

def reset_game():
    """Reset all game variables to start a new game."""
    global current_score, game_time, player_health, player_pos, player_angle
    global bullets, enemies, heat_level, overheated, weapon_cooldown
    global is_evading, evade_timer, evade_cooldown, game_over, name_input_mode, player_name
    global stamina_level, is_sprinting, fatigued, skill_menu_open
    global special_ability_meter, special_ability_active, special_ability_timer
    global camera_shake_timer, camera_shake_intensity
    
    current_score = 0
    game_time = 0
    player_pos = [0.0, 0.0, 20.0]
    player_angle = 0.0
    bullets = []
    heat_level = 0
    overheated = False
    weapon_cooldown = 0
    is_evading = False
    evade_timer = 0
    evade_cooldown = 0
    game_over = False
    name_input_mode = False
    player_name = ""
    skill_menu_open = False
    
    # Reset camera shake
    camera_shake_timer = 0
    camera_shake_intensity = 0.0
    
    # Reset stamina system
    stamina_level = stamina_max
    is_sprinting = False
    fatigued = False
    
    # Reset special abilities but keep progress
    special_ability_meter = 0
    special_ability_active = False
    special_ability_timer = 0
    
    # Apply skill effects to ensure proper values
    apply_skill_effects()
    player_health = player_max_health  # Use potentially upgraded max health
    
    spawn_enemies(TARGET_ENEMY_COUNT)

# =============================
# Input
# =============================
def keyboardListener(key, x, y):
    global player_pos, player_angle, is_evading, evade_timer, evade_cooldown, evade_direction
    global game_over, name_input_mode, player_name, is_sprinting, skill_menu_open
    
    # Skill menu handling
    if skill_menu_open:
        if key == b'\x1b':  # ESC
            skill_menu_open = False
        elif key == b'\t':  # TAB
            cycle_special_ability()
        elif key == b'f' or key == b'F':
            activate_special_ability()
        elif key in [b'1', b'2', b'3', b'4', b'5']:
            skill_index = int(key.decode()) - 1
            skill_names = ['faster_evasion', 'weapon_power', 'heat_management', 'stamina_efficiency', 'health_boost']
            if skill_index < len(skill_names):
                upgrade_skill(skill_names[skill_index])
        return
    
    # Game over state handling
    if game_over:
        if name_input_mode:
            if key == b'\r' or key == b'\n':  # Enter key
                if player_name.strip():
                    save_high_score(current_score, player_name.strip())
                    name_input_mode = False
            elif key == b'\b':  # Backspace
                if player_name:
                    player_name = player_name[:-1]
            elif key == b'\x1b':  # ESC
                exit()
            elif len(player_name) < 15 and (key.isalpha() or key.isdigit()):
                player_name += key.decode('ascii').upper()
        else:
            if key == b'r' or key == b'R':
                reset_game()
            elif key == b'\x1b':  # ESC
                exit()
        return
    
    # Open skill menu
    if key == b'v' or key == b'V':
        skill_menu_open = True
        return
    
    # Special ability activation
    if key == b'f' or key == b'F':
        activate_special_ability()
    
    # Cycle special ability
    if key == b'\t':
        cycle_special_ability()
    
    # Sprint toggle
    if key == b'c' or key == b'C':
        if stamina_level > 10:
            is_sprinting = not is_sprinting
        else:
            is_sprinting = False
    
    # Get current movement speed
    current_speed = get_current_speed()
    
    # Movement with speed modifiers
    if key == b'w':
        nx = player_pos[0] + math.cos(math.radians(player_angle)) * current_speed
        ny = player_pos[1] + math.sin(math.radians(player_angle)) * current_speed
        if abs(nx) < GRID_LENGTH - 30 and abs(ny) < GRID_LENGTH - 30:
            player_pos[0], player_pos[1] = nx, ny
    if key == b's':
        nx = player_pos[0] - math.cos(math.radians(player_angle)) * current_speed
        ny = player_pos[1] - math.sin(math.radians(player_angle)) * current_speed
        if abs(nx) < GRID_LENGTH - 30 and abs(ny) < GRID_LENGTH - 30:
            player_pos[0], player_pos[1] = nx, ny
    if key == b'a':
        player_angle += 3.0
    if key == b'd':
        player_angle -= 3.0
    if key == b' ':
        fire_weapon()

    # Enhanced evasion with skills
    if key == b'q' and evade_cooldown <= 0 and not is_evading and can_evade():
        evade_direction = -1
        enhanced_evasion()
    if key == b'e' and evade_cooldown <= 0 and not is_evading and can_evade():
        evade_direction = 1
        enhanced_evasion()

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
    
    # Apply camera shake effect
    shake_x, shake_y, shake_z = 0.0, 0.0, 0.0
    if camera_shake_timer > 0:
        # Random shake offset based on intensity
        shake_x = random.uniform(-camera_shake_intensity, camera_shake_intensity)
        shake_y = random.uniform(-camera_shake_intensity, camera_shake_intensity)
        shake_z = random.uniform(-camera_shake_intensity * 0.5, camera_shake_intensity * 0.5)
    
    x, y, z = camera_pos
    gluLookAt(x + shake_x, y + shake_y, z + shake_z, 
              player_pos[0], player_pos[1], 0.0, 
              0.0, 0.0, 1.0)

def idle():
    global game_time, weapon_cooldown, heat_level, overheated, evade_timer, is_evading, evade_cooldown
    
    if game_over:
        glutPostRedisplay()
        return
    
    game_time += 1

    if weapon_cooldown > 0:
        weapon_cooldown -= 1

    # Update stamina system
    update_stamina()

    # Update special abilities
    update_special_ability()
    
    # Update camera shake effect
    update_camera_shake()

    # Cool down heat each frame
    if heat_level > 0:
        heat_level -= heat_cool_rate
        if heat_level < 0:
            heat_level = 0
    # Reset overheated if cooled enough
    if overheated and heat_level <= (heat_max * 0.5):
        overheated = False

    # Evasion update
    if is_evading:
        angle_rad = math.radians(player_angle + 90 * evade_direction)
        step = EVADE_DISTANCE / float(EVADE_DURATION)
        player_pos[0] += math.cos(angle_rad) * step
        player_pos[1] += math.sin(angle_rad) * step
        player_pos[0] = max(-GRID_LENGTH + 30, min(GRID_LENGTH - 30, player_pos[0]))
        player_pos[1] = max(-GRID_LENGTH + 30, min(GRID_LENGTH - 30, player_pos[1]))
        evade_timer -= 1
        if evade_timer <= 0:
            is_evading = False
    if evade_cooldown > 0:
        evade_cooldown -= 1

    update_enemies()
    
    # Check for player-enemy collisions (NEW!)
    check_player_enemy_collision()
    
    # Check if player died
    handle_player_death()
    
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
    draw_enemies()
    draw_3d_player()
    enhanced_bullet_enemy_collision()  # Enhanced collision with XP
    draw_weapon_effects()
    draw_enhanced_hud()
    draw_high_scores()
    draw_skill_menu()
    
    if game_over:
        draw_game_over_screen()
    
    glutSwapBuffers()

# =============================
# Main
# =============================
def main():
    load_high_scores()  # Load scores on startup
    init_stars()
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Alien Invasion Survival - Space Combat")
    glEnable(GL_DEPTH_TEST)

    apply_skill_effects()  # Apply any loaded skills
    spawn_enemies(TARGET_ENEMY_COUNT)

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()

if __name__ == "__main__":
    main()
