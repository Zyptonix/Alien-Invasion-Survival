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
player_radius = 12.0

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
rapid_fire_mode = False
rapid_fire_timer = 0
rapid_fire_stamina_cost = 3.0

# Evasion (Q/E)
is_evading = False
evade_timer = 0
evade_cooldown = 0
evade_direction = 0  # -1 = left, +1 = right
EVADE_DISTANCE = 40
EVADE_DURATION = 10
EVADE_COOLDOWN_MAX = 50

# Enemies / combat
BULLET_DAMAGE = 15
ENEMY_SPEED = 0.05           
ENEMY_RADIUS = 7.0
TARGET_ENEMY_COUNT = 10      
ENEMY_DAMAGE = 15

# Threat logic
THREAT_RADIUS = 80.0         # Enemies within this distance are considered "too close"

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

# Enhanced Stamina System
stamina_level = 100
stamina_max = 100
stamina_regen_rate = 0.8
stamina_sprint_drain = 2.0
stamina_evade_cost = 25
stamina_heavy_attack_cost = 15
is_sprinting = False
fatigued = False
fatigue_threshold = 20
sprint_speed_multiplier = 1.8
sprint_accuracy_penalty = 0.3  # Higher penalty for balance
fatigue_speed_penalty = 0.6
fatigue_accuracy_penalty = 0.7  # New: affects shooting when tired

# Enhanced Skill System
player_level = 1
experience_points = 0
experience_to_next_level = 50  # Reduced from 100 to 50 for easier progression
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

# Enhanced feedback system
upgrade_message = ""
upgrade_message_timer = 0
skill_effect_timer = 0

SKILL_COSTS = {
    'faster_evasion': [1, 2, 3],
    'weapon_power': [1, 2, 4],
    'heat_management': [1, 2, 3],
    'stamina_efficiency': [1, 3, 4],
    'health_boost': [2, 3, 5]
}

SPECIAL_ABILITIES = ["DAMAGE_BOOST", "TELEPORT", "INVINCIBILITY", "SHIELD_BUBBLE", "TIME_SLOW"]

# =============================
# Classes
# =============================
class Bullet:
    def __init__(self, x, y, z, angle, is_heavy=False):
        self.x = x
        self.y = y
        self.z = z
        self.angle = angle
        self.speed = bullet_speed
        self.life = 150
        self.active = True
        self.is_heavy = is_heavy
        self.damage = get_weapon_damage() * (1.5 if is_heavy else 1.0)

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

        if self.is_heavy:
            glow = 0.8 + 0.2 * math.sin(game_time * 0.5)
            glColor3f(1.0, glow * 0.5, 0.0)  # Orange heavy bullets
            gluSphere(gluNewQuadric(), 2.5, 12, 10)
        else:
            glow = 0.8 + 0.2 * math.sin(game_time * 0.5)
            glColor3f(0.0, glow, 1.0)  # cyan energy core
            gluSphere(gluNewQuadric(), 1.6, 10, 8)

        # Trail effect
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
    def __init__(self, x, y, z=20.0, hp=15):  # Reduced HP to match bullet damage for 1-hit kills
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
        if special_ability_active and current_special in ["INVINCIBILITY", "SHIELD_BUBBLE"]:
            return  # Don't move toward invincible player

        # Calculate movement toward player
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist = math.hypot(dx, dy) + 1e-6

        # Slow down if time is slowed
        speed_modifier = 0.3 if (special_ability_active and current_special == "TIME_SLOW") else 1.0
        step = ENEMY_SPEED * speed_modifier

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

        # Time slow effect
        if special_ability_active and current_special == "TIME_SLOW":
            glColor3f(0.5, 0.1, 0.1)  # Darkened when slowed
        else:
            glColor3f(0.9, 0.2, 0.2)  # Normal red

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
# Enhanced Player-Enemy Collision
# =============================
def check_player_enemy_collision():
    """Enhanced collision detection with shield protection."""
    global player_health, enemies, camera_shake_timer, camera_shake_intensity

    # Skip collision if player is invincible or has shield
    if special_ability_active and current_special in ["INVINCIBILITY", "SHIELD_BUBBLE"]:
        return

    # Skip collision during evasion
    if is_evading:
        return

    enemies_to_remove = []

    for i, enemy in enumerate(enemies):
        if not enemy.alive:
            continue

        dx = player_pos[0] - enemy.x
        dy = player_pos[1] - enemy.y
        distance = math.hypot(dx, dy)

        collision_distance = player_radius + enemy.radius

        if distance <= collision_distance:
            player_health -= ENEMY_DAMAGE

            # Enhanced camera shake
            camera_shake_timer = 30
            camera_shake_intensity = 15.0

            enemies_to_remove.append(i)
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
        camera_shake_intensity *= 0.9

        if camera_shake_timer <= 0:
            camera_shake_intensity = 0.0

def spawn_enemy_at_safe_distance():
    """Spawn an enemy at a safe distance from the player."""
    max_attempts = 10
    min_safe_distance = 100.0

    for _ in range(max_attempts):
        x, y = _random_edge_spawn()

        dx = player_pos[0] - x
        dy = player_pos[1] - y
        distance = math.hypot(dx, dy)

        if distance >= min_safe_distance:
            enemies.append(Enemy(x, y))
            return

    # Fallback
    angle = random.uniform(0, 2 * math.pi)
    safe_distance = min_safe_distance + 50
    x = player_pos[0] + math.cos(angle) * safe_distance
    y = player_pos[1] + math.sin(angle) * safe_distance

    x = max(-GRID_LENGTH + 25, min(GRID_LENGTH - 25, x))
    y = max(-GRID_LENGTH + 25, min(GRID_LENGTH - 25, y))

    enemies.append(Enemy(x, y))

# =============================
# High-Score Functions
# =============================
def load_high_scores():
    """Load high scores from file with level support."""
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
                if len(parts) >= 4:  # New format with level
                    score = int(parts[0])
                    name = parts[1]
                    date = parts[2]
                    level = int(parts[3])
                    high_scores.append((score, name, date, level))
                elif len(parts) >= 3:  # Old format compatibility
                    score = int(parts[0])
                    name = parts[1]
                    date = parts[2]
                    level = 1  # Default level for old entries
                    high_scores.append((score, name, date, level))

        high_scores.sort(key=lambda x: x[0], reverse=True)
        high_scores = high_scores[:max_highscores]

    except Exception as e:
        print(f"Error loading high scores: {e}")
        high_scores = []

def save_high_score(score, name):
    """Save a new high score with player level."""
    global high_scores

    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    high_scores.append((score, name, current_date, player_level))

    high_scores.sort(key=lambda x: x[0], reverse=True)
    high_scores = high_scores[:max_highscores]

    try:
        with open(HIGHSCORE_FILE, 'w') as f:
            for entry in high_scores:
                if len(entry) == 4:  # New format with level
                    score, name, date, level = entry
                    f.write(f"{score}|{name}|{date}|{level}\n")
                else:  # Old format compatibility
                    score, name, date = entry
                    f.write(f"{score}|{name}|{date}|1\n")  # Default level 1 for old entries
    except Exception as e:
        print(f"Error saving high scores: {e}")

def is_high_score(score):
    """Check if the current score qualifies as a high score."""
    if len(high_scores) < max_highscores:
        return True
    return score > high_scores[-1][0] if high_scores else True

def draw_high_scores():
    """Draw the high scores table with player levels only during game over."""
    # Only show high scores when game is over
    if not game_over or not high_scores:
        return

    glColor3f(*NEON_PINK)
    draw_text(720, 600, "=== HIGH SCORES ===", GLUT_BITMAP_HELVETICA_18)

    y_pos = 570
    for i, entry in enumerate(high_scores[:5]):
        if i == 0:
            glColor3f(*ENERGY_YELLOW)
        elif i <= 2:
            glColor3f(*NEON_CYAN)
        else:
            glColor3f(0.7, 0.7, 0.7)

        # Handle both old and new format entries
        if len(entry) == 4:
            score, name, date, level = entry
            display_name = name[:8] if len(name) > 8 else name
            score_text = f"{i+1}. {display_name}: {score} (L{level})"
        else:  # Old format compatibility
            score, name, date = entry
            display_name = name[:8] if len(name) > 8 else name
            score_text = f"{i+1}. {display_name}: {score} (L1)"

        draw_text(720, y_pos, score_text, GLUT_BITMAP_HELVETICA_10)
        y_pos -= 20

def draw_game_over_screen():
    """Draw game over screen."""
    global name_input_mode, player_name

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
        player_health = 0
        game_over = True

        camera_shake_timer = 0
        camera_shake_intensity = 0.0

        if is_high_score(current_score):
            name_input_mode = True

# =============================
# Enhanced Stamina System
# =============================
def update_stamina():
    """Enhanced stamina system with multiple drain sources."""
    global stamina_level, fatigued, is_sprinting, rapid_fire_mode

    # Stamina drains
    if is_sprinting and stamina_level > 0:
        stamina_level -= stamina_sprint_drain
        if stamina_level < 0:
            stamina_level = 0
            is_sprinting = False

    if rapid_fire_mode and stamina_level > 0:
        stamina_level -= rapid_fire_stamina_cost
        if stamina_level < 0:
            stamina_level = 0
            rapid_fire_mode = False

    # Stamina regeneration (affected by skills)
    if not is_sprinting and not rapid_fire_mode:
        if stamina_level < stamina_max:
            regen_rate = stamina_regen_rate
            # Skill bonus
            if skill_stamina_efficiency > 0:
                regen_rate += skill_stamina_efficiency * 0.3

            stamina_level += regen_rate
            if stamina_level > stamina_max:
                stamina_level = stamina_max

    # Update fatigue state
    fatigued = stamina_level < fatigue_threshold

def get_current_speed():
    """Enhanced speed calculation with skill effects."""
    base_speed = player_speed

    if fatigued:
        return base_speed * fatigue_speed_penalty
    elif is_sprinting:
        multiplier = sprint_speed_multiplier
        # Skill bonus for stamina efficiency
        if skill_stamina_efficiency >= 2:
            multiplier += 0.2
        return base_speed * multiplier
    else:
        return base_speed

def get_shooting_accuracy():
    """Calculate current shooting accuracy based on player state."""
    base_accuracy = 1.0

    if is_sprinting:
        base_accuracy *= sprint_accuracy_penalty

    if fatigued:
        base_accuracy *= fatigue_accuracy_penalty

    # Skill bonus
    if skill_weapon_power >= 2:
        base_accuracy += 0.1

    return base_accuracy

def can_evade():
    """Enhanced evade checking."""
    return stamina_level >= stamina_evade_cost and evade_cooldown <= 0

def consume_evade_stamina():
    """Consume stamina for evasion with skill efficiency."""
    global stamina_level
    cost = stamina_evade_cost

    # Skill reduction
    if skill_faster_evasion >= 2:
        cost = max(15, cost - 5)

    stamina_level -= cost
    if stamina_level < 0:
        stamina_level = 0

def can_heavy_attack():
    """Check if player can perform heavy attack."""
    return stamina_level >= stamina_heavy_attack_cost and not overheated

def consume_heavy_attack_stamina():
    """Consume stamina for heavy attack."""
    global stamina_level
    stamina_level -= stamina_heavy_attack_cost
    if stamina_level < 0:
        stamina_level = 0

# =============================
# Enhanced Skill System
# =============================
def gain_experience(points):
    """Enhanced experience system with skill effects."""
    global experience_points, player_level, experience_to_next_level, skill_points, skill_effect_timer

    # Bonus XP from high health skill
    if skill_health_boost >= 3:
        points = int(points * 1.2)

    experience_points += points

    while experience_points >= experience_to_next_level:
        experience_points -= experience_to_next_level
        player_level += 1
        skill_points += 1
        skill_effect_timer = 180  # Show level up effect
        experience_to_next_level = int(experience_to_next_level * 1.2)

def can_upgrade_skill(skill_name):
    """Enhanced skill upgrade checking."""
    skill_level = globals()[f'skill_{skill_name}']
    if skill_level >= 3:
        return False
    cost = SKILL_COSTS[skill_name][skill_level]
    return skill_points >= cost

def upgrade_skill(skill_name):
    """Enhanced skill upgrade with better feedback."""
    global skill_points, upgrade_message, upgrade_message_timer

    if not can_upgrade_skill(skill_name):
        skill_level = globals()[f'skill_{skill_name}']
        if skill_level >= 3:
            upgrade_message = f"{skill_name.upper().replace('_', ' ')}: MAX LEVEL REACHED"
        else:
            cost = SKILL_COSTS[skill_name][skill_level]
            upgrade_message = f"INSUFFICIENT SKILL POINTS! NEED {cost}, HAVE {skill_points}"
        upgrade_message_timer = 120
        return False

    skill_level = globals()[f'skill_{skill_name}']
    cost = SKILL_COSTS[skill_name][skill_level]

    globals()[f'skill_{skill_name}'] += 1
    skill_points -= cost

    upgrade_message = f"{skill_name.upper().replace('_', ' ')} UPGRADED TO LEVEL {skill_level + 1}!"
    upgrade_message_timer = 120

    apply_skill_effects()
    return True

def apply_skill_effects():
    """Enhanced skill effects application."""
    global player_max_health, heat_cool_rate, stamina_regen_rate, stamina_sprint_drain

    # Health boost (more significant)
    base_health = 100
    player_max_health = base_health + (skill_health_boost * 30)

    # Heat management (more effective)
    base_cool_rate = 1
    heat_cool_rate = base_cool_rate + (skill_heat_management * 0.7)

    # Stamina efficiency (more noticeable)
    base_regen = 0.8
    base_drain = 2.0
    stamina_regen_rate = base_regen + (skill_stamina_efficiency * 0.4)
    stamina_sprint_drain = max(0.5, base_drain - (skill_stamina_efficiency * 0.5))

def get_weapon_damage():
    """Enhanced weapon damage calculation."""
    base_damage = 15
    skill_bonus = skill_weapon_power * 7  # Increased from 5

    # Special ability bonus
    if special_ability_active and current_special == "DAMAGE_BOOST":
        return int((base_damage + skill_bonus) * 2.5)

    return base_damage + skill_bonus

def get_evade_cooldown():
    """Enhanced evade cooldown with better skill scaling."""
    base_cooldown = 50
    reduction = skill_faster_evasion * 12  # Increased from 10
    return max(20, base_cooldown - reduction)

def charge_special_ability(amount):
    """Enhanced special ability charging."""
    global special_ability_meter

    # Skill bonus charging
    if skill_weapon_power >= 3:
        amount = int(amount * 1.3)

    special_ability_meter = min(special_ability_max, special_ability_meter + amount)

def can_use_special_ability():
    """Check if special ability can be used."""
    return special_ability_meter >= special_ability_max and not special_ability_active

def activate_special_ability():
    """Enhanced special ability activation."""
    global special_ability_active, special_ability_timer, special_ability_meter

    if not can_use_special_ability():
        return False

    special_ability_active = True

    # Different durations for different abilities
    if current_special == "TIME_SLOW":
        special_ability_timer = 300  # 5 seconds
    elif current_special == "SHIELD_BUBBLE":
        special_ability_timer = 240  # 4 seconds
    else:
        special_ability_timer = 180  # 3 seconds

    special_ability_meter = 0
    return True

def update_special_ability():
    """Enhanced special ability updates."""
    global special_ability_active, special_ability_timer

    if special_ability_active:
        special_ability_timer -= 1
        if special_ability_timer <= 0:
            special_ability_active = False

def cycle_special_ability():
    """Enhanced special ability cycling."""
    global current_special

    current_index = SPECIAL_ABILITIES.index(current_special)
    current_special = SPECIAL_ABILITIES[(current_index + 1) % len(SPECIAL_ABILITIES)]

def enhanced_evasion():
    """Enhanced evasion with multiple skill effects."""
    global is_evading, evade_timer, evade_cooldown

    if not can_evade():
        return False

    is_evading = True
    evade_timer = EVADE_DURATION
    evade_cooldown = get_evade_cooldown()
    consume_evade_stamina()

    # Special teleport ability
    if special_ability_active and current_special == "TELEPORT":
        safe_x = random.uniform(-GRID_LENGTH * 0.5, GRID_LENGTH * 0.5)
        safe_y = random.uniform(-GRID_LENGTH * 0.5, GRID_LENGTH * 0.5)
        player_pos[0] = safe_x
        player_pos[1] = safe_y
        is_evading = False

    return True

def draw_enhanced_skill_menu():
    """Enhanced skill menu with better visuals and feedback."""
    global upgrade_message_timer

    if not skill_menu_open:
        return

    if upgrade_message_timer > 0:
        upgrade_message_timer -= 1

    glDisable(GL_DEPTH_TEST)

    # Enhanced background effect
    glColor3f(0.0, 0.0, 0.1)
    glBegin(GL_QUADS)
    glVertex2f(150, 100)
    glVertex2f(850, 100)
    glVertex2f(850, 700)
    glVertex2f(150, 700)
    glEnd()

    # Title with glow effect
    pulse = 0.7 + 0.3 * math.sin(game_time * 0.05)
    glColor3f(0.0, pulse, 1.0)
    draw_text(400, 680, "═══ PILOT SKILL UPGRADES ═══", GLUT_BITMAP_HELVETICA_18)

    # Player stats
    glColor3f(*ENERGY_YELLOW)
    draw_text(180, 650, f"PILOT LEVEL: {player_level} │ SKILL POINTS: {skill_points} │ XP: {experience_points}/{experience_to_next_level}", GLUT_BITMAP_HELVETICA_12)

    # Show upgrade feedback message
    if upgrade_message_timer > 0:
        message_pulse = 0.5 + 0.5 * math.sin(upgrade_message_timer * 0.15)
        if "INSUFFICIENT" in upgrade_message or "MAX LEVEL" in upgrade_message:
            glColor3f(1.0, message_pulse * 0.3, 0.0)
        else:
            glColor3f(0.0, 1.0, message_pulse)
        draw_text(180, 620, upgrade_message, GLUT_BITMAP_HELVETICA_12)

    # Enhanced skills list
    y_pos = 580
    skills = [
        ("faster_evasion", "Enhanced Mobility", "Reduces evasion cooldown by 12 frames per level"),
        ("weapon_power", "Weapon Mastery", "Increases bullet damage by 7 per level + accuracy boost"),
        ("heat_management", "Thermal Control", "Improves weapon cooling by 0.7 per level"),
        ("stamina_efficiency", "Physical Conditioning", "Better stamina (+0.4 regen, -0.5 drain per level)"),
        ("health_boost", "Hull Reinforcement", "Increases maximum health by 30 per level + XP bonus")
    ]

    for i, (skill_name, display_name, description) in enumerate(skills):
        skill_level = globals()[f'skill_{skill_name}']
        can_upgrade = can_upgrade_skill(skill_name)

        # Enhanced visual indicators
        if can_upgrade and skill_points > 0:
            glow = 0.7 + 0.3 * math.sin(game_time * 0.1 + i)
            glColor3f(0.0, glow, 0.5)
            prefix = ">>> "
        elif skill_level >= 3:
            glColor3f(1.0, 0.0, 0.8)
            prefix = "[MAX] "
        else:
            glColor3f(0.5, 0.5, 0.5)
            prefix = "    "

        # Skill info line
        level_text = "MAX" if skill_level >= 3 else f"{skill_level}/3"
        cost_text = "" if skill_level >= 3 else f"Cost: {SKILL_COSTS[skill_name][skill_level]} SP"
        skill_text = f"{prefix}{i+1}. {display_name} [{level_text}] {cost_text}"

        draw_text(180, y_pos, skill_text, GLUT_BITMAP_HELVETICA_12)

        # Description line
        glColor3f(0.8, 0.8, 0.8)
        draw_text(200, y_pos - 15, description, GLUT_BITMAP_HELVETICA_10)

        y_pos -= 50

    # Enhanced special ability section
    glColor3f(*NEON_PINK)
    draw_text(180, 330, "═══ SPECIAL ABILITIES ═══", GLUT_BITMAP_HELVETICA_18)

    ability_color = NEON_GREEN if can_use_special_ability() else (0.6, 0.6, 0.6)
    glColor3f(*ability_color)
    ability_text = f"ACTIVE: {current_special} │ CHARGE: {int(special_ability_meter)}/{special_ability_max}"
    draw_text(180, 300, ability_text, GLUT_BITMAP_HELVETICA_12)

    if can_use_special_ability():
        pulse = 0.7 + 0.3 * math.sin(game_time * 0.2)
        glColor3f(pulse, 1.0, 0.0)
        draw_text(180, 280, ">>> READY TO ACTIVATE! Press F <<<", GLUT_BITMAP_HELVETICA_12)

    # Special ability descriptions
    glColor3f(0.7, 0.7, 1.0)
    descriptions = {
        "DAMAGE_BOOST": "2.5x weapon damage for 3 seconds",
        "TELEPORT": "Instant evasion teleport to safe location",
        "INVINCIBILITY": "Complete immunity to damage for 3 seconds",
        "SHIELD_BUBBLE": "Protective barrier for 4 seconds",
        "TIME_SLOW": "Slows enemy movement for 5 seconds"
    }
    draw_text(180, 260, descriptions[current_special], GLUT_BITMAP_HELVETICA_10)

    # Enhanced controls help
    glColor3f(0.9, 0.9, 0.9)
    draw_text(180, 220, "═══ MENU CONTROLS ═══", GLUT_BITMAP_HELVETICA_12)
    glColor3f(*NEON_GREEN)
    draw_text(180, 200, "Keys 1-5: Upgrade Corresponding Skill", GLUT_BITMAP_HELVETICA_10)
    draw_text(180, 180, "TAB: Cycle Through Special Abilities", GLUT_BITMAP_HELVETICA_10)
    draw_text(180, 160, "F: Activate Special Ability (when ready)", GLUT_BITMAP_HELVETICA_10)
    draw_text(180, 140, "V or ESC: Close This Menu", GLUT_BITMAP_HELVETICA_10)

    glEnable(GL_DEPTH_TEST)

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
    """Spawn up to n enemies."""
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
# Enhanced Weapon System
# =============================
def fire_weapon(is_heavy=False):
    """Enhanced weapon firing with stamina integration."""
    global weapon_cooldown, muzzle_flash_timer, heat_level, overheated

    if weapon_cooldown > 0 or overheated:
        return False

    # Check if heavy attack is possible
    if is_heavy and not can_heavy_attack():
        return False

    # Consume stamina for heavy attacks
    if is_heavy:
        consume_heavy_attack_stamina()

    # Calculate accuracy based on player state and skills
    accuracy = get_shooting_accuracy()
    base_spread = 5.0
    spread_range = base_spread * (2.0 - accuracy)
    accuracy_modifier = random.uniform(-spread_range, spread_range)

    bullet_angle = player_angle + accuracy_modifier

    nose_forward = 18.0
    bx = player_pos[0] + math.cos(math.radians(player_angle)) * nose_forward
    by = player_pos[1] + math.sin(math.radians(player_angle)) * nose_forward
    bz = player_pos[2]

    bullets.append(Bullet(bx, by, bz, bullet_angle, is_heavy))

    # Enhanced weapon cooldown with skills
    base_cooldown = max_weapon_cooldown
    if skill_weapon_power >= 3:
        base_cooldown = max(8, base_cooldown - 3)

    weapon_cooldown = base_cooldown
    muzzle_flash_timer = 8 if is_heavy else 5

    # Enhanced heat system
    heat_cost = heat_per_shot * (1.8 if is_heavy else 1.0)
    if skill_heat_management > 0:
        heat_cost *= (1.0 - skill_heat_management * 0.15)

    heat_level += heat_cost
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
    """Enhanced collision detection with skill effects."""
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
                    damage = bullet.damage

                    # Special ability effects
                    if special_ability_active and current_special == "DAMAGE_BOOST":
                        damage = int(damage * 2.5)

                    e.hp -= damage
                    bullet.active = False

                    if e.hp <= 0:
                        e.alive = False

                        # Enhanced scoring with skill bonuses
                        base_score = 10
                        if skill_weapon_power >= 2:
                            base_score += 3

                        current_score += base_score

                        # Enhanced XP and special ability charging
                        base_xp = 5
                        if skill_health_boost >= 3:
                            base_xp = int(base_xp * 1.2)

                        gain_experience(base_xp)
                        charge_special_ability(8)

                        spawn_one_enemy()
                    break

        if bullet.active:
            bullet.draw()
        else:
            bullets.remove(bullet)

def draw_weapon_effects():
    """Enhanced muzzle flash with heavy attack effects."""
    global muzzle_flash_timer
    if muzzle_flash_timer <= 0:
        return

    flash = muzzle_flash_timer / 8.0
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(player_angle, 0.0, 0.0, 1.0)

    # Different effects for heavy vs normal shots
    if muzzle_flash_timer > 5:  # Heavy shot
        glColor3f(1.0, flash * 0.5, 0.0)
        size = 3.0 * flash
    else:  # Normal shot
        glColor3f(1.0, flash, 0.0)
        size = 2.0 * flash

    glPushMatrix()
    glTranslatef(0.0, 14.0, -1.0)
    gluSphere(gluNewQuadric(), size, 10, 8)
    glPopMatrix()
    glPopMatrix()
    muzzle_flash_timer -= 1

# =============================
# Enhanced Player Visual
# =============================
def draw_3d_player():
    """Enhanced player with visual skill effects."""
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(player_angle, 0.0, 0.0, 1.0)

    # Enhanced color system based on state and skills
    base_color = [0.2, 0.8, 1.0]

    # Special ability effects
    if special_ability_active:
        if current_special == "INVINCIBILITY":
            glow = 0.5 + 0.5 * math.sin(game_time * 0.5)
            base_color = [1.0, glow, 1.0]
        elif current_special == "DAMAGE_BOOST":
            glow = 0.7 + 0.3 * math.sin(game_time * 0.4)
            base_color = [1.0, glow * 0.3, 0.0]
        elif current_special == "SHIELD_BUBBLE":
            base_color = [0.0, 1.0, 1.0]
        elif current_special == "TIME_SLOW":
            glow = 0.6 + 0.4 * math.sin(game_time * 0.2)
            base_color = [0.8, 0.8, glow]
    elif is_evading:
        base_color = [1.0, 1.0, 0.3]
    elif is_sprinting:
        glow = 0.7 + 0.3 * math.sin(game_time * 0.3)
        base_color = [0.2, glow, 1.0]
    elif fatigued:
        base_color = [0.8, 0.4, 0.4]

    # Skill level glow enhancement
    if skill_weapon_power >= 3:
        base_color[0] = min(1.0, base_color[0] + 0.2)
    if skill_stamina_efficiency >= 3:
        base_color[1] = min(1.0, base_color[1] + 0.2)
    if skill_health_boost >= 3:
        base_color[2] = min(1.0, base_color[2] + 0.2)

    glColor3f(*base_color)

    # Hull with skill-based size modifications
    hull_scale = 1.0
    if skill_health_boost >= 2:
        hull_scale += 0.1

    glPushMatrix()
    glScalef(1.5 * hull_scale, 3.0 * hull_scale, 0.8)
    gluSphere(gluNewQuadric(), 8.0, 12, 8)
    glPopMatrix()

    # Enhanced cockpit
    glColor3f(0.1, 0.3, 0.8)
    glPushMatrix()
    glTranslatef(0.0, 12.0, 3.0)
    glScalef(0.8, 1.2, 0.6)
    gluSphere(gluNewQuadric(), 6.0, 10, 8)
    glPopMatrix()

    # Enhanced wings with skill indicators
    wing_color = [0.15, 0.6, 0.9]
    if skill_faster_evasion >= 2:
        wing_color[1] = min(1.0, wing_color[1] + 0.3)  # Brighter wings for mobility

    glColor3f(*wing_color)
    glPushMatrix(); glTranslatef(-12.0, -2.0, 0.0); glRotatef(90, 0, 1, 0); glScalef(0.3, 1.8, 2.0); glutSolidCube(8.0); glPopMatrix()
    glPushMatrix(); glTranslatef( 12.0, -2.0, 0.0); glRotatef(90, 0, 1, 0); glScalef(0.3, 1.8, 2.0); glutSolidCube(8.0); glPopMatrix()

    # Enhanced engines with stamina-based effects
    glColor3f(0.3, 0.3, 0.3)
    glPushMatrix(); glTranslatef(-8.0, -12.0, 0.0); glRotatef(90, 1, 0, 0); gluCylinder(gluNewQuadric(), 3.0, 2.0, 8.0, 8, 4); glPopMatrix()
    glPushMatrix(); glTranslatef( 8.0, -12.0, 0.0); glRotatef(90, 1, 0, 0); gluCylinder(gluNewQuadric(), 3.0, 2.0, 8.0, 8, 4); glPopMatrix()

    # Enhanced engine effects
    glow = 0.6 + 0.4 * math.sin(game_time * 0.2)
    if is_sprinting:
        intensity = 1.5 if skill_stamina_efficiency >= 2 else 1.2
        glColor3f(0.2, glow * intensity, 1.0)
        engine_size = 6.0
    elif fatigued:
        glColor3f(0.1, glow * 0.5, 0.6)
        engine_size = 3.0
    else:
        glColor3f(0.0, glow, 1.0)
        engine_size = 4.0

    # Engine glows
    glPushMatrix(); glTranslatef(-8.0, -18.0, 0.0); gluSphere(gluNewQuadric(), engine_size, 8, 6); glPopMatrix()
    glPushMatrix(); glTranslatef( 8.0, -18.0, 0.0); gluSphere(gluNewQuadric(), engine_size, 8, 6); glPopMatrix()
    glColor3f(glow, glow * 0.8, 1.0); glPushMatrix(); glTranslatef(0.0, -16.0, 1.0); gluSphere(gluNewQuadric(), 2.5, 8, 6); glPopMatrix()

    # Enhanced sprint trail
    if is_sprinting:
        trail_length = 7 if skill_stamina_efficiency >= 3 else 5
        for i in range(trail_length):
            trail_offset = (i + 1) * 8.0
            trail_alpha = max(0.1, 0.8 - i * 0.15)
            glColor3f(0.0, trail_alpha, trail_alpha * 1.2)
            glPushMatrix()
            glTranslatef(0.0, -16.0 - trail_offset, 1.0)
            glScalef(0.8 - i * 0.1, 0.8 - i * 0.1, 0.1)
            gluSphere(gluNewQuadric(), 3.0, 8, 6)
            glPopMatrix()

    # Enhanced weapons with skill indicators
    weapon_color = [0.8, 0.8, 0.8]
    if skill_weapon_power >= 2:
        weapon_color = [1.0, 0.8, 0.2]  # Golden weapons

    glColor3f(*weapon_color)
    glPushMatrix(); glTranslatef(-6.0, 8.0, -1.0); glRotatef(90, 1, 0, 0); gluCylinder(gluNewQuadric(), 1.0, 0.5, 4.0, 6, 4); glPopMatrix()
    glPushMatrix(); glTranslatef( 6.0, 8.0, -1.0); glRotatef(90, 1, 0, 0); gluCylinder(gluNewQuadric(), 1.0, 0.5, 4.0, 6, 4); glPopMatrix()

    # Shield bubble for special ability
    if special_ability_active and current_special == "SHIELD_BUBBLE":
        glColor3f(0.0, 0.8, 1.0)
        shield_pulse = 0.3 + 0.4 * math.sin(game_time * 0.3)
        glColor4f(0.0, shield_pulse, 1.0, 0.3)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        gluSphere(gluNewQuadric(), 25.0, 16, 12)
        glDisable(GL_BLEND)

    # Enhanced strobes
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

    # Enhanced shadow
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

# =============================
# Threat helper (distance-based)
# =============================
def get_threat_level():
    """Determine threat level based on how many enemies are within THREAT_RADIUS."""
    close_enemies = 0
    for e in enemies:
        if e.alive:
            dx = player_pos[0] - e.x
            dy = player_pos[1] - e.y
            if math.hypot(dx, dy) <= THREAT_RADIUS:
                close_enemies += 1

    # HIGH only if more than 4 enemies are 'too close'
    if close_enemies > 4:
        return "HIGH", WARNING_RED
    elif close_enemies > 1:
        return "MEDIUM", ENERGY_YELLOW
    else:
        return "LOW", NEON_GREEN

def draw_enhanced_hud():
    """Fully enhanced HUD with all systems."""
    global ui_pulse, skill_effect_timer
    ui_pulse += 0.1

    if skill_effect_timer > 0:
        skill_effect_timer -= 1

    # Left panel - Enhanced Ship Status
    glColor3f(*NEON_CYAN); draw_text(15, 750, "═══ SHIP STATUS ═══", GLUT_BITMAP_HELVETICA_18)

    # Enhanced health display
    health_ratio = player_health / float(player_max_health)
    if health_ratio > 0.6:
        glColor3f(*NEON_GREEN)
        status_text = "OPTIMAL"
    elif health_ratio > 0.3:
        glColor3f(*ENERGY_YELLOW)
        status_text = "DAMAGED"
    else:
        glColor3f(*WARNING_RED)
        status_text = "CRITICAL"

    draw_text(15, 720, f"HULL: {player_health}/{player_max_health} ({int(health_ratio * 100)}%)", GLUT_BITMAP_HELVETICA_12)
    draw_text(15, 700, f"STATUS: {status_text}", GLUT_BITMAP_HELVETICA_12)

    # Enhanced stamina display
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

    draw_text(15, 680, f"STAMINA: {int(stamina_level)}/{stamina_max}", GLUT_BITMAP_HELVETICA_12)
    draw_text(15, 660, f"CONDITION: {stamina_status}", GLUT_BITMAP_HELVETICA_12)

    # Enhanced movement status
    if is_sprinting:
        sprint_color = NEON_PINK if stamina_level > 30 else WARNING_RED
        glColor3f(*sprint_color)
        draw_text(15, 640, "ENGINES: AFTERBURNER", GLUT_BITMAP_HELVETICA_12)
    else:
        glColor3f(0.6, 0.6, 0.6)
        draw_text(15, 640, "ENGINES: STANDARD (C to boost)", GLUT_BITMAP_HELVETICA_12)

    # Enhanced weapon status
    if weapon_cooldown > 0:
        glColor3f(*WARNING_RED)
        draw_text(15, 620, f"WEAPONS: CHARGING ({weapon_cooldown})", GLUT_BITMAP_HELVETICA_12)
    elif overheated:
        glColor3f(*WARNING_RED)
        draw_text(15, 620, "WEAPONS: OVERHEATED!", GLUT_BITMAP_HELVETICA_12)
    else:
        weapon_color = NEON_GREEN
        if skill_weapon_power >= 3:
            weapon_color = ENERGY_YELLOW
        glColor3f(*weapon_color)
        draw_text(15, 620, "WEAPONS: READY", GLUT_BITMAP_HELVETICA_12)

    # Enhanced evasion status
    if evade_cooldown > 0:
        glColor3f(*ENERGY_YELLOW)
        draw_text(15, 600, f"EVASION: COOLDOWN ({evade_cooldown})", GLUT_BITMAP_HELVETICA_12)
    elif not can_evade():
        glColor3f(*WARNING_RED)
        draw_text(15, 600, "EVASION: INSUFFICIENT STAMINA", GLUT_BITMAP_HELVETICA_12)
    else:
        evasion_color = NEON_GREEN
        if skill_faster_evasion >= 3:
            evasion_color = ENERGY_YELLOW
        glColor3f(*evasion_color)
        draw_text(15, 600, "EVASION: READY (Q/E)", GLUT_BITMAP_HELVETICA_12)

    # Enhanced heat status
    if overheated:
        glColor3f(1.0, 0.2, 0.2)
        draw_text(15, 580, "THERMAL: CRITICAL OVERLOAD!", GLUT_BITMAP_HELVETICA_12)
    else:
        heat_ratio = heat_level / heat_max
        if heat_ratio > 0.8:
            glColor3f(*WARNING_RED)
        elif heat_ratio > 0.6:
            glColor3f(*ENERGY_YELLOW)
        else:
            glColor3f(*NEON_GREEN)
        draw_text(15, 580, f"THERMAL: {int(heat_level)}/{heat_max}", GLUT_BITMAP_HELVETICA_12)

    # Center top - Enhanced mission status
    glColor3f(*NEON_PINK)
    draw_text(380, 750, "═══ ALIEN INVASION SURVIVAL ═══", GLUT_BITMAP_HELVETICA_18)
    glColor3f(*ENERGY_YELLOW)
    draw_text(400, 720, f"WAVE: 1 │ SCORE: {current_score} │ THREAT LEVEL: EXTREME", GLUT_BITMAP_HELVETICA_12)

    pulse = 0.7 + 0.3 * math.sin(ui_pulse)
    glColor3f(pulse, 1.0, pulse)
    draw_text(450, 700, "MISSION: SURVIVE AT ALL COSTS", GLUT_BITMAP_HELVETICA_12)

    # Right panel - Enhanced tactical info
    live_count = sum(1 for e in enemies if e.alive)
    glColor3f(*NEON_CYAN)
    draw_text(720, 750, "═══ TACTICAL ═══", GLUT_BITMAP_HELVETICA_18)
    glColor3f(*ALIEN_GREEN)
    draw_text(720, 720, f"HOSTILES: {live_count} ACTIVE", GLUT_BITMAP_HELVETICA_12)

    # Distance-aware threat
    threat, threat_color = get_threat_level()
    glColor3f(*threat_color)
    draw_text(720, 700, f"THREAT: {threat}", GLUT_BITMAP_HELVETICA_12)

    draw_text(720, 680, f"PROJECTILES: {len(bullets)}", GLUT_BITMAP_HELVETICA_12)

    # Enhanced pilot skills display
    glColor3f(*NEON_PINK)
    draw_text(720, 450, "═══ PILOT PROFILE ═══", GLUT_BITMAP_HELVETICA_12)

    glColor3f(*ENERGY_YELLOW)
    draw_text(720, 430, f"RANK: LEVEL {player_level}", GLUT_BITMAP_HELVETICA_10)
    draw_text(720, 410, f"XP: {experience_points}/{experience_to_next_level}", GLUT_BITMAP_HELVETICA_10)

    # Show skill points with pulsing effect if available
    if skill_points > 0:
        skill_pulse = 0.5 + 0.5 * math.sin(game_time * 0.2)
        glColor3f(skill_pulse, 1.0, 0.0)
        draw_text(720, 390, f"SKILL POINTS: {skill_points} AVAILABLE!", GLUT_BITMAP_HELVETICA_10)
    else:
        glColor3f(0.6, 0.6, 0.6)
        draw_text(720, 390, f"SKILL POINTS: {skill_points}", GLUT_BITMAP_HELVETICA_10)

    # Special ability status with enhanced visuals
    ability_color = NEON_GREEN if can_use_special_ability() else (0.6, 0.6, 0.6)
    glColor3f(*ability_color)
    draw_text(720, 360, f"SPECIAL: {current_special}", GLUT_BITMAP_HELVETICA_10)

    meter_percent = int((special_ability_meter / special_ability_max) * 100)
    draw_text(720, 340, f"CHARGE: {meter_percent}%", GLUT_BITMAP_HELVETICA_10)

    if special_ability_active:
        ability_pulse = 0.5 + 0.5 * math.sin(game_time * 0.3)
        glColor3f(ability_pulse, 0.0, ability_pulse)
        draw_text(720, 320, f"ABILITY ACTIVE! ({special_ability_timer})", GLUT_BITMAP_HELVETICA_10)

    # Level up effect
    if skill_effect_timer > 0:
        level_pulse = 0.3 + 0.7 * math.sin(skill_effect_timer * 0.1)
        glColor3f(level_pulse, 1.0, 0.0)
        draw_text(400, 600, "LEVEL UP! SKILL POINT EARNED!", GLUT_BITMAP_HELVETICA_18)

    # Enhanced Controls Help
    glColor3f(0.7, 0.7, 1.0)
    draw_text(15, 220, "═══ SHIP CONTROLS ═══", GLUT_BITMAP_HELVETICA_12)
    glColor3f(0.9, 0.9, 0.9)
    draw_text(15, 200, "WASD: Navigate │ C: Afterburner Toggle", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 180, "SPACE/LMB: Fire │ SHIFT+SPACE: Heavy Shot", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 160, "Q/E: Evasive Maneuvers", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 140, "V: Pilot Skills │ F: Special │ TAB: Cycle", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 120, "ARROWS: Camera Control", GLUT_BITMAP_HELVETICA_10)

def reset_game():
    """Enhanced game reset with skill preservation."""
    global current_score, game_time, player_health, player_pos, player_angle
    global bullets, enemies, heat_level, overheated, weapon_cooldown
    global is_evading, evade_timer, evade_cooldown, game_over, name_input_mode, player_name
    global stamina_level, is_sprinting, fatigued, skill_menu_open, rapid_fire_mode
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
    rapid_fire_mode = False

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

    # Apply skill effects and restore health
    apply_skill_effects()
    player_health = player_max_health

    spawn_enemies(TARGET_ENEMY_COUNT)

# =============================
# Enhanced Input System
# =============================
def keyboardListener(key, x, y):
    """Enhanced keyboard input with all new features."""
    global player_pos, player_angle, is_evading, evade_timer, evade_cooldown, evade_direction
    global game_over, name_input_mode, player_name, is_sprinting, skill_menu_open
    global rapid_fire_mode

    # Skill menu handling
    if skill_menu_open:
        if key == b'\x1b' or key == b'v' or key == b'V':  # ESC or V to close
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

    # Enhanced sprint toggle
    if key == b'c' or key == b'C':
        if stamina_level > 10:
            is_sprinting = not is_sprinting
        else:
            is_sprinting = False

    # Rapid fire toggle (R key)
    if key == b'r' or key == b'R':
        if not game_over:
            if stamina_level > 20:
                rapid_fire_mode = not rapid_fire_mode
            else:
                rapid_fire_mode = False

    # Get current movement speed
    current_speed = get_current_speed()

    # Enhanced movement
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

    # Enhanced firing
    if key == b' ':
        fire_weapon()

    # Enhanced evasion
    if key == b'q' and can_evade():
        evade_direction = -1
        enhanced_evasion()
    if key == b'e' and can_evade():
        evade_direction = 1
        enhanced_evasion()

def specialKeyListener(key, x, y):
    """Enhanced special key handling."""
    global camera_pos

    # Heavy attack with SHIFT + SPACE would be handled here if needed
    # For now, just camera controls
    cx, cy, cz = camera_pos
    if key == GLUT_KEY_UP:    cz += 15
    if key == GLUT_KEY_DOWN:  cz = max(100, cz - 15)
    if key == GLUT_KEY_LEFT:  cx -= 15
    if key == GLUT_KEY_RIGHT: cx += 15
    camera_pos = [cx, cy, cz]

def mouseListener(button, state, x, y):
    """Enhanced mouse input."""
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        fire_weapon()
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        # Right click for heavy attack
        fire_weapon(is_heavy=True)

# =============================
# Enhanced Camera System
# =============================
def setupCamera():
    """Enhanced camera with shake effects."""
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 2000.0)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()

    # Enhanced camera shake
    shake_x, shake_y, shake_z = 0.0, 0.0, 0.0
    if camera_shake_timer > 0 and not game_over:
        shake_x = random.uniform(-camera_shake_intensity, camera_shake_intensity)
        shake_y = random.uniform(-camera_shake_intensity, camera_shake_intensity)
        shake_z = random.uniform(-camera_shake_intensity * 0.5, camera_shake_intensity * 0.5)

    x, y, z = camera_pos
    gluLookAt(x + shake_x, y + shake_y, z + shake_z,
              player_pos[0], player_pos[1], 0.0,
              0.0, 0.0, 1.0)

def idle():
    """Enhanced main game loop."""
    global game_time, weapon_cooldown, heat_level, overheated, evade_timer, is_evading, evade_cooldown
    global rapid_fire_timer

    if game_over:
        glutPostRedisplay()
        return

    game_time += 1

    # Enhanced weapon cooldown
    if weapon_cooldown > 0:
        weapon_cooldown -= 1

    # Rapid fire handling
    if rapid_fire_mode and weapon_cooldown == 0:
        fire_weapon()

    # Update enhanced stamina system
    update_stamina()

    # Update special abilities
    update_special_ability()

    # Update camera shake
    update_camera_shake()

    # Enhanced heat system
    if heat_level > 0:
        cool_rate = heat_cool_rate
        if skill_heat_management > 0:
            cool_rate += skill_heat_management * 0.3
        heat_level -= cool_rate
        if heat_level < 0:
            heat_level = 0

    # Enhanced overheat recovery
    if overheated and heat_level <= (heat_max * 0.4):
        overheated = False

    # Enhanced evasion update
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
    check_player_enemy_collision()
    handle_player_death()

    glutPostRedisplay()

def showScreen():
    """Enhanced main display function."""
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
    enhanced_bullet_enemy_collision()
    draw_weapon_effects()
    draw_enhanced_hud()
    draw_high_scores()
    draw_enhanced_skill_menu()

    if game_over:
        draw_game_over_screen()

    glutSwapBuffers()

# =============================
# Main Function
# =============================
def main():
    """Enhanced main function."""
    print("═══════════════════════════════════════")
    print("    ALIEN INVASION SURVIVAL")
    print("    Enhanced Edition v2.0")
    print("═══════════════════════════════════════")
    print("Loading high scores...")

    load_high_scores()
    init_stars()

    print("Initializing OpenGL...")
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Alien Invasion Survival - Enhanced Space Combat Simulator")
    glEnable(GL_DEPTH_TEST)

    print("Applying initial skill configurations...")
    apply_skill_effects()
    spawn_enemies(TARGET_ENEMY_COUNT)

    print("Setting up input handlers...")
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    print("═══════════════════════════════════════")
    print("CONTROLS:")
    print("WASD: Navigate Ship")
    print("C: Toggle Afterburner")
    print("SPACE/LMB: Fire Weapons")
    print("RMB: Heavy Attack")
    print("Q/E: Evasive Maneuvers")
    print("V: Skill Menu")
    print("F: Activate Special")
    print("TAB: Cycle Special")
    print("═══════════════════════════════════════")
    print("LAUNCHING GAME...")

    glutMainLoop()

if __name__ == "__main__":
    main()
