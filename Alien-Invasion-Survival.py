
"""
Alien Invasion Survival 
-------------------------------------
"""

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import math
import os
from datetime import datetime
import sys

# =============================
# Global / Config
# =============================
# --- World & Camera ---
camera_angle = 0.0
camera_distance = 220.0
camera_height = 90.0
camera_mode = "FOLLOW" 
camera_shake_intensity = 0.0  
camera_shake_duration = 0     
camera_pos = [0.0, 0.0, 0.0] 
fovY = 75
ARENA_WIDTH = 1000
ARENA_HEIGHT = 500
ARENA_DEPTH = 3000.0

# --- Testing Flag ---
INVINCIBLE_MODE = False 

# --- Theme colors ---
SPACE_BLUE    = (0.05, 0.05, 0.15)
NEON_CYAN     = (0.0, 1.0, 1.0)
NEON_GREEN    = (0.0, 1.0, 0.2)
NEON_PINK     = (1.0, 0.0, 0.8)
WARNING_RED   = (1.0, 0.2, 0.2)
ENERGY_YELLOW = (1.0, 1.0, 0.0)
ENEMY_PURPLE  = (0.8, 0.4, 1.0)
ASTEROID_GREY = (0.5, 0.5, 0.5)

# --- Game State Management ---
game_state = "START_MENU" 
pre_game_timer = 0
PRE_GAME_DURATION = 600
wave_transition_timer = 0
WAVE_TRANSITION_DURATION = 180
player_flash_timer = 0 

# --- Wave System ---
current_wave = 0
enemies_per_wave = 5
enemy_bullet_speed_multiplier = 2.0

# --- Player ---
player_pos = [0.0, 0.0, 0.0]
player_max_health = 100
player_health = 100
player_speed = 3.0 
# --- Radius for collision detection ---
# (Increased to account for wind damage and make the game harder)
player_radius = 20.0

# --- Input Timers for Fluid Movement ---
INPUT_TIMEOUT = 7 
player_move_y_timer = 0; player_move_y_dir = 0
player_move_x_timer = 0; player_move_x_dir = 0
crosshair_move_y_timer = 0; crosshair_move_y_dir = 0
crosshair_move_x_timer = 0; crosshair_move_x_dir = 0
fire_timer = 0



# --- Crosshair ---
crosshair_pos = [0.0, 0.0, ARENA_DEPTH - 800] 
crosshair_speed = 4.0

# --- Game state ---
current_score = 0
game_time = 0
star_positions = []

# --- Weapon / bullets ---
bullets = []
weapon_cooldown = 0
max_weapon_cooldown = 15
bullet_speed = 45.0 

# --- Evasion (Q/E) ---
is_evading = False
evade_timer = 0
evade_cooldown = 0
evade_direction = 0
EVADE_DISTANCE_BASE = 200 
EVADE_DURATION = 8
EVADE_COOLDOWN_MAX = 50

# --- Overheat system ---
heat_level = 0
heat_max = 100
heat_per_shot = 20
heat_cool_rate = 0.08
overheated = False

# --- High-Score System ---
HIGHSCORE_FILE = "highscores.txt"
high_scores = []
max_highscores = 10
player_name = ""
name_input_mode = False

# --- Stamina System ---
stamina_level = 100
stamina_max = 100
stamina_regen_rate = 0.03
stamina_sprint_drain = 0.25
stamina_evade_cost = 50
is_sprinting = False 
fatigued = False
fatigue_threshold = 20
sprint_speed_multiplier = 3.0
fatigue_speed_penalty = 0.3

# --- Skill System ---
player_level = 1
experience_points = 0
experience_to_next_level = 50
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
SKILL_COSTS = {
    'faster_evasion': [1, 2, 3], 'weapon_power': [1, 2, 4],
    'heat_management': [1, 2, 3], 'stamina_efficiency': [1, 3, 4],
    'health_boost': [2, 3, 5]
    
}
SPECIAL_ABILITIES = ["DAMAGE_BOOST", "SHIELD_BUBBLE", "TELEPORT", "TIME_SLOW"]

# Current player levels (0 = not upgraded yet)
skill_levels = {name: 0 for name in SKILL_COSTS}

# Temporary skills (only unlock once, last for 2 minutes)
temp_skills = {
    'mobility_boost': {"cost": 1, "active": False, "duration": 0},
    'weapon_mastery': {"cost": 1, "active": False, "duration": 0}
}


# --- Time Slow Powerup variable ---
time_scale = 1.0 

# --- V-Menu Abilities ---
mobility_boost_active = False
mobility_boost_timer = 0
MOBILITY_BOOST_DURATION = 2 * 60 * 60 
MOBILITY_BOOST_MULTIPLIER = 5.0
weapon_mastery_active = False
weapon_mastery_timer = 0
WEAPON_MASTERY_DURATION = 2 * 60 * 60 
WEAPON_MASTERY_DAMAGE_MULT = 1.5

# --- Enemy AI ---
enemies = []
enemy_bullets = []
asteroids = []
boss = None
max_enemies = 10
obstacles = [] 

# =============================
# Classes
# =============================
class Obstacle:
    def __init__(self, pos, size, type):
        self.pos = list(pos)
        self.original_pos = list(pos) # Store original position for respawn
        self.size = size
        self.type = type # 'DESTRUCTIBLE' or 'PUSHABLE'
        self.active = True
     
        self.health = 100
        self.respawn_timer = -1 # -1 means not waiting to respawn

    def take_damage(self, amount):
        if self.type == 'DESTRUCTIBLE':
            self.health -= amount
            if self.health <= 0:
                self.active = False
                self.respawn_timer = 600 # Start a 10-second timer (600 frames)
                trigger_camera_shake(8.0, 12)

    def update(self):
        # If waiting to respawn, count down the timer
        if self.respawn_timer > 0:
            self.respawn_timer -= 1
            if self.respawn_timer == 0:
                # Timer finished, reset the obstacle
                self.active = True
                self.health = 100
                # Random Position
                self.pos[0] = random.uniform(-ARENA_WIDTH * 0.9, ARENA_WIDTH * 0.9)
                self.pos[1] = random.uniform(-ARENA_HEIGHT * 0.9, ARENA_HEIGHT * 0.9)
                self.pos[2] = random.uniform(ARENA_DEPTH * 0.2, ARENA_DEPTH * 0.8)
               
                self.respawn_timer = -1

    def draw(self):
        if not self.active: return
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        if self.type == 'DESTRUCTIBLE':
            color = (0.7, 0.5, 0.3)
        else:
            color = (0.6, 0.6, 0.7)
        glColor3f(*color)
        glutSolidCube(self.size)
        glPopMatrix()

class Bullet:
    def __init__(self, start_pos, vector):
        self.pos = list(start_pos)
        self.vector = vector
        self.speed = bullet_speed
        self.active = True
        self.damage = get_weapon_damage()
        self.radius = 3.5

    def update(self):
        if self.active:
            current_speed = self.speed * (2.0 if weapon_mastery_active else 1.0)
            self.pos[0] += self.vector[0] * current_speed
            self.pos[1] += self.vector[1] * current_speed
            self.pos[2] += self.vector[2] * current_speed
            if self.pos[2] > ARENA_DEPTH + 200 or self.pos[2] < -200: 
                self.active = False

    def draw(self):
        if not self.active: return
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        # We only need to calculate rotation if the vector has a length.
        # If the vector is [0, 0, 0], it has no direction, so we can skip rotation.
        if self.vector[0] != 0 or self.vector[1] != 0 or self.vector[2] != 0:

            # --- Calculate Y-axis rotation (Yaw) ---
            # This orients the laser based on its X and Z direction.
            angle_y = -math.degrees(math.atan2(self.vector[2], self.vector[0])) + 90
            glRotatef(angle_y, 0, 1, 0)
            
            # --- Calculate X-axis rotation (Pitch) ---
            # This tilts the laser up or down.
            v_horiz = math.sqrt(self.vector[0]**2 + self.vector[2]**2)
            
            # We can calculate angle_x directly. math.atan2 handles the case where
            # v_horiz is 0, which fixes the bug for vertical vectors.
            angle_x = -math.degrees(math.atan2(self.vector[1], v_horiz))
            glRotatef(angle_x, 1, 0, 0)
        
        # --- Draw the laser cylinder ---
        glColor3f(*ENERGY_YELLOW)
        laser_length = 80.0 + (skill_weapon_power * 20)
        laser_width = 1.5 + (skill_weapon_power * 0.5)
        gluCylinder(gluNewQuadric(), laser_width, laser_width/2, laser_length, 8, 1)
        glPopMatrix()

class EnemyBullet:
    def __init__(self, start_pos, type):
        self.pos = list(start_pos)
        self.type = type
        self.active = True
        self.vector = [0, 0, -1] 
        base_speed = 1.0
        if self.type == 'FAST':
            base_speed = 1.7; self.damage = 5; self.radius = 7.0
            self.color = (2.0, 0.6, 0.0); self.vector = [0, 0, -1] 
        if self.type == 'WALL':
            base_speed = 1.7; self.damage = 10; self.radius = 7.0
            self.color = (2.0, 0.6, 0.0); self.vector = [0, 0, -1] 
        elif self.type == 'HOMING':
            base_speed = 1.4; self.damage = 10; self.radius = 9.0; self.color = NEON_PINK
        elif self.type == 'BIG':
            base_speed = 1; self.damage = 15; self.radius = 15.0; self.color = NEON_CYAN
        self.speed = base_speed * enemy_bullet_speed_multiplier
        if self.type != "WALL":
            dir_x, dir_y, dir_z = player_pos[0] - self.pos[0], player_pos[1] - self.pos[1], player_pos[2] - self.pos[2]
            dist = math.sqrt(dir_x**2 + dir_y**2 + dir_z**2)
            if dist > 0: self.vector = [dir_x / dist, dir_y / dist, dir_z / dist]

    def update(self):
        if not self.active: 
            return
        self.pos[0] += self.vector[0] * self.speed * time_scale; 
        self.pos[1] += self.vector[1] * self.speed * time_scale; 
        self.pos[2] += self.vector[2] * self.speed * time_scale
        if self.pos[2] < -100: 
            self.active = False
            
    def draw(self):
        if not self.active: 
            return
        glPushMatrix(); glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glColor3f(*self.color); gluSphere(gluNewQuadric(), self.radius, 10, 8); 
        glPopMatrix()

class Asteroid:
    def __init__(self, start_pos, target_pos=None):
        self.pos = list(start_pos)
        self.active = True
        self.speed = 1.2 * enemy_bullet_speed_multiplier
        self.damage = 20
        self.radius = 80.0
        
        aim_pos = target_pos if target_pos is not None else player_pos
        
        dir_x, dir_y, dir_z = aim_pos[0] - self.pos[0], aim_pos[1] - self.pos[1], aim_pos[2] - self.pos[2]
        dist = math.sqrt(dir_x**2 + dir_y**2 + dir_z**2)
        self.vector = [dir_x / dist, dir_y / dist, dir_z / dist] if dist > 0 else [0,0,-1]
    
    def update(self):
        if not self.active: 
            return
        self.pos[0] += self.vector[0] * self.speed * time_scale; 
        self.pos[1] += self.vector[1] * self.speed * time_scale; 
        self.pos[2] += self.vector[2] * self.speed * time_scale
        if self.pos[2] < -100: 
            self.active = False

    def draw(self):
        if not self.active: 
            return
        glPushMatrix(); glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        glColor3f(*ASTEROID_GREY); gluSphere(gluNewQuadric(), self.radius, 5, 5); 
        glPopMatrix()

class Enemy:
    def __init__(self):
        roll = random.random()
        if roll < 0.5: self.type = 'GRUNT'
        elif roll < 0.8: self.type = 'WARPER'
        else: self.type = 'GUARDIAN'
        self.flash_timer = 0 
        self.pos = [random.uniform(-ARENA_WIDTH*0.8, ARENA_WIDTH*0.8), random.uniform(-ARENA_HEIGHT*0.8, ARENA_HEIGHT*0.8), ARENA_DEPTH]
        self.target_z = ARENA_DEPTH - random.uniform(400, 800)
        self.active = True
        
        if self.type == 'GRUNT':
            self.health = 60; self.radius = 50.0; self.color = (0.8, 0.2, 0.2); self.fire_rate = 700; self.move_speed = 0.2
            self.score_value = 100; self.xp_value = 5
        elif self.type == 'GUARDIAN':
            self.health = 100; self.shield_health = 30; self.radius = 70.0; self.color = (0.5, 0.2, 0.8); self.fire_rate = 480; self.move_speed = 0.1
            self.score_value = 250; self.xp_value = 15
        elif self.type == 'WARPER':
            self.health = 30; self.radius = 40.0; self.color = (1.0, 1.0, 0.0); self.fire_rate = 600; self.warp_cooldown = 1800
            self.score_value = 150; self.xp_value = 10

        self.fire_cooldown = random.randint(self.fire_rate, self.fire_rate + 120) * time_scale
        self.move_direction = 1 if random.random() > 0.5 else -1

    def update(self):
        if self.pos[2] > self.target_z:
            self.pos[2] -= 15; return 
        if self.flash_timer > 0: 
            self.flash_timer -= 1
        if self.type == 'GRUNT' or self.type == 'GUARDIAN':
            self.pos[0] += self.move_speed * self.move_direction * time_scale
            if abs(self.pos[0]) > ARENA_WIDTH * 0.9: self.move_direction *= -1
        
        if self.type == 'WARPER':
            self.warp_cooldown -= 1
            if self.warp_cooldown <= 0:
                self.pos = [random.uniform(-ARENA_WIDTH*0.8, ARENA_WIDTH*0.8), random.uniform(-ARENA_HEIGHT*0.8, ARENA_HEIGHT*0.8), ARENA_DEPTH]
                self.warp_cooldown = random.randint(2400, 2600)

        self.fire_cooldown -= 1
        if self.fire_cooldown <= 0:
            if self.type == 'GUARDIAN': bullet_type = 'BIG'
            elif self.type == 'GRUNT': bullet_type = 'FAST'
            elif self.type == 'WARPER': bullet_type = 'HOMING'
            enemy_bullets.append(EnemyBullet(self.pos, bullet_type))
            self.fire_cooldown = random.randint(self.fire_rate, self.fire_rate + 120)

    def take_damage(self, amount):
        global current_score
        self.flash_timer = 15
        if self.type == 'GUARDIAN' and self.shield_health > 0: 
            self.shield_health -= amount
        else: 
            self.health -= amount
        if self.health <= 0: 
            self.active = False; 
            current_score += self.score_value; 
            gain_experience(self.xp_value)
     
    
    def draw(self):
        if not self.active: 
            return
        glPushMatrix(); 
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        # --- Hit Flash Logic ---
        color_to_use = self.color
        if self.flash_timer > 0:
            color_to_use = (0.5, 1.0, 0.5) # Bright green flash

        # --- Draw Model using the chosen color ---
        if self.type == 'GRUNT':
            glColor3f(*color_to_use)
            glPushMatrix(); glScalef(1.0, 0.4, 1.0); gluSphere(gluNewQuadric(), self.radius, 16, 8); glPopMatrix()
            glPushMatrix(); glTranslatef(0, self.radius * 0.2, 0); glColor3f(0.6, 0.6, 0.8); gluSphere(gluNewQuadric(), self.radius * 0.4, 12, 6); glPopMatrix()
        elif self.type == 'GUARDIAN':
            glColor3f(*color_to_use)
            glPushMatrix(); glScalef(1.2, 1.0, 1.0); glutSolidCube(self.radius * 0.8); glPopMatrix()
            glColor3f(0.3, 0.3, 0.3) # Cannons are always dark
            glPushMatrix(); glTranslatef(self.radius * 0.6, 0, 0); gluCylinder(gluNewQuadric(), self.radius*0.2, self.radius*0.2, self.radius * 0.5, 8, 1); glPopMatrix()
            glPushMatrix(); glTranslatef(-self.radius * 0.6, 0, 0); gluCylinder(gluNewQuadric(), self.radius*0.2, self.radius*0.2, self.radius * 0.5, 8, 1); glPopMatrix()
        elif self.type == 'WARPER':
            glColor3f(*color_to_use); glRotatef(game_time, 0.5, 1, 0.3); glutSolidCube(self.radius); glColor3f(0.8, 0.8, 0.2)
            glPushMatrix(); glTranslatef(0, 0, self.radius*0.5); glScalef(0.1, 0.1, 1.5); glutSolidCube(self.radius); glPopMatrix()
            glPushMatrix(); glTranslatef(0, 0, -self.radius*0.5); glScalef(0.1, 0.1, 1.5); glutSolidCube(self.radius); glPopMatrix()
            glPushMatrix(); glTranslatef(self.radius*0.5, 0, 0); glScalef(1.5, 0.1, 0.1); glutSolidCube(self.radius); glPopMatrix()
            glPushMatrix(); glTranslatef(-self.radius*0.5, 0, 0); glScalef(1.5, 0.1, 0.1); glutSolidCube(self.radius); glPopMatrix()

        if self.type == 'GUARDIAN' and self.shield_health > 0:
            pulse = 0.7 + 0.2 * math.sin(game_time * 0.1)
            glColor3f(NEON_CYAN[0]*pulse, NEON_CYAN[1]*pulse, NEON_CYAN[2]*pulse)
            gluSphere(gluNewQuadric(), self.radius, 16, 12)
        glPopMatrix()

class Boss:
    """
    Represents the boss enemy in the game.
    The boss uses multiple AI states:
    - ENTERING: moves into the arena.
    - IDLE: waits, then picks an attack pattern.
    - TELEGRAPH_*: shows warning effects before attacking.
    - SWEEPING: fires a sweeping bullet pattern.
    - ASTEROID: launches asteroid attacks.
    - WALL_ATTACK: spawns horizontal wall bullets with a moving gap.
    - VULNERABLE: temporarily weak to extra damage.
    """

    def __init__(self):
        # --- Core Stats ---
        self.max_health = 800 + (current_wave * 150)
        self.health = self.max_health
        self.radius = 150.0
        self.color = (0.4, 0.4, 0.5)  # Metallic Grey
        self.ring_color = self.color

        # --- Positioning ---
        self.pos = [0, 0, ARENA_DEPTH + 300]
        self.target_pos = [0, 0, ARENA_DEPTH - 800]

        # --- State Flags ---
        self.active = True
        self.phase = 1
        self.ai_state = "ENTERING"
        self.ai_timer = 0
        self.sweep_angle = -90.0
        self.charge_particles = []
        self.flash_timer = 0

        # --- Wall Attack Variables (NEW) ---
        self.gap_pos_x = 0
        self.gap_width = 75
        self.gap_direction = 1  # 1 = move right, -1 = move left
        self.wall_spawn_timer = 0

    def take_damage(self, amount):
        """
        Apply damage to the boss.
        Damage is multiplied if the boss is vulnerable.
        Handles phase transitions and death.
        """
        global current_score, skill_points, game_state, wave_transition_timer
        self.flash_timer = 10
        damage_multiplier = 2.0 if self.ai_state == "VULNERABLE" else 3.0
        self.health -= amount * damage_multiplier

        # Phase shift to Phase 2
        if self.phase == 1 and self.health <= self.max_health / 2:
            self.phase = 2
            self.ai_state = "IDLE"
            self.ai_timer = 120

        # Boss death
        if self.health <= 0:
            self.active = False
            current_score += 5000
            gain_experience(200)
            skill_points += 3
            enemies.clear()
            enemy_bullets.clear()
            asteroids.clear()
            spawn_obstacles(20)
            game_state = "WAVE_TRANSITION"
            wave_transition_timer = WAVE_TRANSITION_DURATION
            trigger_camera_shake(200.0, 60)

    def update(self):
        """Main AI state machine controlling the boss's behavior."""
        if not self.active:
            return

        # Hit flash timer
        if self.flash_timer > 0:
            self.flash_timer -= 1

        # Charge particles (telegraph visuals)
        for p in self.charge_particles[:]:
            p['size'] += p['rate']
            p['timer'] -= 1
            if p['timer'] <= 0:
                self.charge_particles.remove(p)

        # --- AI State Machine ---
        if self.ai_state == "ENTERING":
            self.pos[2] -= 5 * time_scale
            if self.pos[2] <= self.target_pos[2]:
                self.ai_state = "IDLE"
                self.ai_timer = 120

        elif self.ai_state == "IDLE":
            self.ai_timer -= 1 * time_scale
            if self.ai_timer <= 0:
                roll = random.random()
                if roll < 0.4:
                    self.ai_state = "TELEGRAPH_WALL"
                    self.ai_timer = 150
                elif roll < 0.7:
                    self.ai_state = "TELEGRAPH_ASTEROID"
                    self.ai_timer = 200
                else:
                    self.ai_state = "TELEGRAPH_SWEEP"
                    self.ai_timer = 120

        # --- Telegraph States ---
        elif self.ai_state == "TELEGRAPH_ASTEROID":
            self.ai_timer -= 1
            if self.ai_timer % 5 == 0:
                self.charge_particles.append({
                    'pos': [random.uniform(-50, 50), random.uniform(-50, 50), 0],
                    'size': 3,
                    'rate': 1.5,
                    'timer': 15,
                    'color': ASTEROID_GREY
                })
            if self.ai_timer <= 0:
                self.ai_state = "ASTEROID"
                self.ai_timer = 300

        elif self.ai_state == "TELEGRAPH_SWEEP":
            self.ai_timer -= 1
            if self.ai_timer <= 0:
                self.ai_state = "SWEEPING"
                self.ai_timer = 1800

        elif self.ai_state == "TELEGRAPH_WALL":
            self.ai_timer -= 1 * time_scale
            if self.ai_timer <= 0:
                # Set up the moving gap wall attack
                self.ai_state = "WALL_ATTACK"
                self.gap_pos_x = random.uniform(-ARENA_WIDTH / 2, ARENA_WIDTH / 2)
                self.gap_width = 75
                self.gap_direction = random.choice([-1, 1])
                self.ai_timer = 240  # total attack duration
                self.wall_spawn_timer = 40  # spawns rows for 40 frames

        # --- Attack States ---
        elif self.ai_state == "SWEEPING":
            self.ai_timer -= 1
            self.pos[0] = math.sin(game_time * 0.02 * time_scale) * 200
            if self.ai_timer % 3 == 0:
                angle_rad = math.radians(self.sweep_angle)
                start_pos = [
                    self.pos[0] + math.cos(angle_rad) * self.radius,
                    self.pos[1] + math.sin(angle_rad) * self.radius,
                    self.pos[2]
                ]
                bullet = EnemyBullet(start_pos, 'BIG')
                bullet.speed *= 2.5
                bullet.vector[1] += random.uniform(-0.1, 0.1)
                enemy_bullets.append(bullet)
                self.sweep_angle += 0.5 if self.phase == 1 else 0.75
            if self.ai_timer <= 0:
                self.pos[0] = 0
                self.ai_state = "VULNERABLE"
                self.ai_timer = 600

        elif self.ai_state == "ASTEROID":
            self.ai_timer -= 1
            if self.ai_timer <= 0:
                asteroids.append(Asteroid(self.pos))
                for _ in range(4):
                    offset = [random.uniform(-200, 200), random.uniform(-150, 150), 0]
                    target_pos = [
                        player_pos[0] + offset[0],
                        player_pos[1] + offset[1],
                        player_pos[2]
                    ]
                    asteroids.append(Asteroid(self.pos, target_pos=target_pos))
                self.ai_state = "VULNERABLE"
                self.ai_timer = 300

        elif self.ai_state == "WALL_ATTACK":
            self.ai_timer -= 1 * time_scale

            # Move the safe gap horizontally during attack
            gap_speed = 8 * time_scale
            self.gap_pos_x += self.gap_direction * gap_speed
            if self.gap_pos_x > ARENA_WIDTH / 2 - self.gap_width:
                self.gap_pos_x = ARENA_WIDTH / 2 - self.gap_width
                self.gap_direction = -1
            elif self.gap_pos_x < -ARENA_WIDTH / 2 + self.gap_width:
                self.gap_pos_x = -ARENA_WIDTH / 2 + self.gap_width
                self.gap_direction = 1

            # Spawn wall rows with a moving gap
            if self.wall_spawn_timer > 0:
                self.wall_spawn_timer -= 1 * time_scale
                progress = self.wall_spawn_timer / 40.0
                y_offset = -200 + (1.0 - progress) * 400

                # Instead of dozens of small bullets, we place ~6 large bullets
                num_columns = 10  # drastically fewer
                spacing = ARENA_WIDTH / num_columns

                for i in range(num_columns):
                    x = -ARENA_WIDTH / 2 + i * spacing + spacing / 2
                    
                    # Skip the safe gap
                    if abs(x - self.gap_pos_x) < self.gap_width:
                        continue
                    
                    start_pos = [x, player_pos[1] + y_offset, self.pos[2]]
                    bullet = EnemyBullet(start_pos, 'WALL')
                    bullet.speed *= 1.5
                    
                    # Make wall bullets visually larger & cover more space
                    bullet.radius = 40
                    
                    enemy_bullets.append(bullet)

            if self.ai_timer <= 0:
                self.ai_state = "VULNERABLE"
                self.ai_timer = 240

        elif self.ai_state == "VULNERABLE":
            self.pos[0] *= 0.95
            self.pos[1] *= 0.95
            self.ai_timer -= 1
            if self.ai_timer <= 0:
                self.ai_state = "IDLE"
                self.ai_timer = 120

    def draw(self):
        """Draw the boss model and its telegraph effects."""
        if not self.active:
            return
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        # --- Core color based on state ---
        core_color = WARNING_RED
        self.ring_color = self.color
        if self.phase == 2:
            core_color = ENERGY_YELLOW
        if self.ai_state == "VULNERABLE":
            core_color = NEON_GREEN
        elif self.ai_state == "TELEGRAPH_ASTEROID":
            self.ring_color = ASTEROID_GREY
        elif self.ai_state == "TELEGRAPH_SWEEP":
            self.ring_color = (1, 1, 1)
        elif self.ai_state == "TELEGRAPH_WALL":
            self.ring_color = NEON_CYAN

        # --- Flash effect when hit ---
        if self.flash_timer > 0:
            core_color = (0.5, 1.0, 0.5)
            self.ring_color = (0.5, 1.0, 0.5)

        # --- Draw body ---
        pulse = 0.5 + 0.5 * math.sin(game_time * 0.2)
        glColor3f(core_color[0] * pulse, core_color[1] * pulse, core_color[2] * pulse)
        gluSphere(gluNewQuadric(), self.radius * 0.6, 16, 12)

        # --- Draw rotating rings ---
        glColor3f(*self.ring_color)
        glPushMatrix()
        glRotatef(game_time, 1, 1, 1)
        glScalef(1, 1, 0.2)
        glutSolidCube(self.radius * 2)
        glPopMatrix()

        glPushMatrix()
        glRotatef(game_time, -1, 1, -1)
        glScalef(0.2, 1, 1)
        glutSolidCube(self.radius * 2)
        glPopMatrix()

        # --- Draw charge particles ---
        for p in self.charge_particles:
            glPushMatrix()
            glTranslatef(p['pos'][0], p['pos'][1], p['pos'][2])
            glColor3f(*p['color'])
            gluSphere(gluNewQuadric(), p['size'], 6, 6)
            glPopMatrix()

        glPopMatrix()

# =============================
# Game Logic
# =============================


# In Game Logic section

def trigger_camera_shake(intensity, duration):
    global camera_shake_intensity, camera_shake_duration
    # Make the new shake stack with any existing shake for a bigger effect
    camera_shake_intensity += intensity
    camera_shake_duration += duration
def apply_skill_effects():
    global player_max_health, player_health, heat_cool_rate, stamina_regen_rate, stamina_sprint_drain

    # Health Boost: Increase max health and add the gained health to the current health.
    new_max_health = 100 + (skill_levels['health_boost'] * 30)
    if new_max_health > player_max_health:
        player_health += new_max_health - player_max_health
    player_max_health = new_max_health
    player_health = min(player_health, player_max_health) # Ensure health doesn't exceed the new max.

    # Heat Management: Improve the cooling rate of your weapon.
    heat_cool_rate = 0.08 + (skill_levels['heat_management'] * 0.05)

    # Stamina Efficiency: Increase stamina regeneration and reduce sprint drain.
    stamina_regen_rate = 0.03 + (skill_levels['stamina_efficiency'] * 0.1)
    base_sprint_drain = 0.06
    stamina_sprint_drain = max(0.02, base_sprint_drain - (skill_levels['stamina_efficiency'] * 0.05))

def can_upgrade_skill(skill_name):
    """Check if the skill can be upgraded (not maxed and enough points)."""
    level = skill_levels[skill_name]
    if level >= len(SKILL_COSTS[skill_name]):  # Already max
        return False
    cost = SKILL_COSTS[skill_name][level]
    return skill_points >= cost


def upgrade_skill(skill_name):
    """Upgrade a skill if possible, reducing skill points."""
    global skill_points, player_health, player_max_health
    if not can_upgrade_skill(skill_name):
        return False

    level = skill_levels[skill_name]
    cost = SKILL_COSTS[skill_name][level]
    skill_levels[skill_name] += 1
    skill_points -= cost

    # Immediately apply the stat changes from the new skill level.
    apply_skill_effects()

    # If the upgraded skill was health_boost, set health to full.
    if skill_name == 'health_boost':
        player_health = player_max_health
        
    return True

def activate_temp_skill(skill_name):
    """Activate a temporary skill (2 mins) if enough points and not already active."""
    global skill_points
    skill = temp_skills[skill_name]
    if skill_points >= skill["cost"] and not skill["active"]:
        skill_points -= skill["cost"]
        skill["active"] = True
        skill["duration"] = 120 * 60  # 2 mins in frames (if 60 FPS)
        return True
    return False


def update_temp_skills():
    """Reduce duration of temporary skills each frame."""
    for skill in temp_skills.values():
        if skill["active"]:
            skill["duration"] -= 1
            if skill["duration"] <= 0:
                skill["active"] = False


def get_evade_cost():
    return max(15, stamina_evade_cost - (skill_stamina_efficiency * 5))
def can_evade():
    return stamina_level >= get_evade_cost() and evade_cooldown <= 0
def consume_evade_stamina():
    global stamina_level
    stamina_level -= get_evade_cost()
def get_weapon_damage():
    base_damage = 15 + (skill_weapon_power * 7)
    if weapon_mastery_active: base_damage *= WEAPON_MASTERY_DAMAGE_MULT
    if special_ability_active and current_special == "DAMAGE_BOOST": base_damage *= 2.5
    return int(base_damage)
def get_evade_cooldown():
    return max(30, EVADE_COOLDOWN_MAX - (skill_faster_evasion * 12))
def get_evade_distance():
    return EVADE_DISTANCE_BASE + (skill_faster_evasion * 20)
def charge_special_ability(amount):
    global special_ability_meter
    if skill_weapon_power >= 3: amount = int(amount * 1.3)
    special_ability_meter = min(special_ability_max, special_ability_meter + amount)
def can_use_special_ability():
    return special_ability_meter >= special_ability_max and not special_ability_active
def do_teleport():
    global player_pos
    player_pos[0], player_pos[1] = 0.0, 0.0
def activate_special_ability():
    global special_ability_active, special_ability_timer, special_ability_meter
    if not can_use_special_ability(): return
    if current_special == "TELEPORT": do_teleport(); special_ability_meter = 0; return
    special_ability_active = True
    durations = {"TIME_SLOW": 3600, "SHIELD_BUBBLE": 3600, "DAMAGE_BOOST": 3600 }
    special_ability_timer = durations.get(current_special, 3600); special_ability_meter = 0
def update_special_ability():
    global special_ability_active, special_ability_timer
    if special_ability_active and special_ability_timer > 0:
        special_ability_timer -= 1
        if special_ability_timer <= 0: special_ability_active = False
def cycle_special_ability():
    global current_special, SPECIAL_ABILITIES
    idx = (SPECIAL_ABILITIES.index(current_special) + 1) % len(SPECIAL_ABILITIES); current_special = SPECIAL_ABILITIES[idx]
def start_next_wave():
    global current_wave, enemies_per_wave, enemy_bullet_speed_multiplier, boss
    current_wave += 1
    if current_wave > 0 and current_wave % 1 == 0:
        boss = Boss()
    else:
        enemies_per_wave = min(10, 2 + (current_wave - 1) // 2)
        enemy_bullet_speed_multiplier = min(3.0, 1.0 + (current_wave - 1) * 0.1)
        for _ in range(enemies_per_wave):
            spawn_enemy()
def spawn_enemy():
    if len(enemies) < max_enemies: enemies.append(Enemy())
def spawn_obstacles(count):
    global obstacles
    obstacles = []
    for _ in range(count):
        size = random.uniform(40, 150)
        pos = [
            random.uniform(-ARENA_WIDTH + size, ARENA_WIDTH - size),
            random.uniform(-ARENA_HEIGHT + size, ARENA_HEIGHT - size),
            random.uniform(ARENA_DEPTH * 0.2, ARENA_DEPTH * 0.8)
        ]
        type = 'DESTRUCTIBLE' if random.random() < 0.5 else 'INDESTRUCTIBLE'
        obstacles.append(Obstacle(pos, size, type))

def update_enemies_and_bullets():
    if boss and boss.active: boss.update()
    for enemy in enemies[:]:
        if not enemy.active: enemies.remove(enemy)
        else: enemy.update()
    for bullet in enemy_bullets[:]:
        if not bullet.active: enemy_bullets.remove(bullet)
        else: bullet.update()
    for asteroid in asteroids[:]:
        if not asteroid.active: asteroids.remove(asteroid)
        else: asteroid.update()
    # --- Update and clean up obstacles ---
    for obstacle in obstacles[:]:
        obstacle.update()
def check_collisions():
    global player_health,player_flash_timer
    for bullet in bullets[:]:
        if not bullet.active: continue
        # OBSTACLE COLLISION
        for obstacle in obstacles:
            if not obstacle.active: continue
            # Simple sphere vs cube (AABB) check
            if (abs(bullet.pos[0] - obstacle.pos[0]) < obstacle.size/2 + bullet.radius and
                abs(bullet.pos[1] - obstacle.pos[1]) < obstacle.size/2 + bullet.radius and
                abs(bullet.pos[2] - obstacle.pos[2]) < obstacle.size/2 + bullet.radius):
                
                if obstacle.type == 'DESTRUCTIBLE':
                    obstacle.take_damage(bullet.damage)
                bullet.active = False
                break
        if not bullet.active: continue
        # ENEMY COLLISION 
        for enemy in enemies:
            if not enemy.active: continue
            dist_sq = (bullet.pos[0] - enemy.pos[0])**2 + (bullet.pos[1] - enemy.pos[1])**2 + (bullet.pos[2] - enemy.pos[2])**2
            if dist_sq < (bullet.radius + enemy.radius)**2:
                enemy.take_damage(bullet.damage)
                bullet.active = False
                break
     
        # BOSS COLLISION
        if not bullet.active: continue 
        if boss and boss.active:
            dist_sq = (bullet.pos[0] - boss.pos[0])**2 + (bullet.pos[1] - boss.pos[1])**2 + (bullet.pos[2] - boss.pos[2])**2
            if dist_sq < (bullet.radius + boss.radius)**2:
                boss.take_damage(bullet.damage); bullet.active = False


    # --- Enemy Projectiles vs. Obstacles ---
    for proj in enemy_bullets:
        if not proj.active or proj.type=="WALL": continue
        for obstacle in obstacles:
            if (abs(proj.pos[0] - obstacle.pos[0]) < obstacle.size/2 + proj.radius and
                abs(proj.pos[1] - obstacle.pos[1]) < obstacle.size/2 + proj.radius and
                abs(proj.pos[2] - obstacle.pos[2]) < obstacle.size/2 + proj.radius):
                proj.active = False
                break

    
    # --- Player Damage  ---

    invincible = (special_ability_active and current_special in [ "SHIELD_BUBBLE"]) or INVINCIBLE_MODE
    if not invincible:
            # Enemy bullets vs player
            for bullet in enemy_bullets[:]:
                if not bullet.active: continue
                dist_sq = (bullet.pos[0] - player_pos[0])**2 + (bullet.pos[1] - player_pos[1])**2 + (bullet.pos[2] - player_pos[2])**2
                if dist_sq < (bullet.radius + player_radius)**2: 
                    player_health -= bullet.damage; bullet.active = False
                    trigger_camera_shake(50.0, 40) 
                    player_flash_timer = 15 
            # Asteroids vs player
            for asteroid in asteroids[:]:
                if not asteroid.active: continue
                dist_sq = (asteroid.pos[0] - player_pos[0])**2 + (asteroid.pos[1] - player_pos[1])**2 + (asteroid.pos[2] - player_pos[2])**2
                if dist_sq < (asteroid.radius + player_radius)**2: 
                    player_health -= asteroid.damage; asteroid.active = False
                    trigger_camera_shake(25.0, 50) 
                    player_flash_timer = 15 

def update_bullets():
    for bullet in bullets[:]:
        if not bullet.active: bullets.remove(bullet); continue
        bullet.update()


def load_high_scores():
    """
    Loads high scores from a file. If the file doesn't exist,
    it creates one with default placeholder scores.
    """
    global high_scores
    high_scores = []

    # --- New Section: Create the file if it doesn't exist ---
    if not os.path.exists(HIGHSCORE_FILE):
        print("High score file not found. Creating a new one.")
        try:
            # Create a default list of scores to populate the new file
            default_scores = [
                (1000, "Zarif", "2025-01-01", 5),
            ]
            
            # Open the new file in 'write' mode ('w')
            with open(HIGHSCORE_FILE, 'w') as f:
                # Write each default score to the file
                for score, name, date, level in default_scores:
                    f.write(f"{score}|{name}|{date}|{level}\n")
            
            # Set the current high_scores list to our defaults
            high_scores = default_scores
            return # Exit the function since we've created and loaded the scores

        except Exception as e:
            print(f"Error creating high score file: {e}")
            return # Stop if we can't create the file
    # -----------------------------------------------------------

    # --- Original Loading Logic (runs if the file already exists) ---
    try:
        with open(HIGHSCORE_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 4:
                    score = int(parts[0])
                    name = parts[1]
                    date = parts[2]
                    level = int(parts[3])
                    high_scores.append((score, name, date, level))
        
        # Sort and trim the list after loading
        high_scores.sort(key=lambda x: x[0], reverse=True)
        high_scores = high_scores[:max_highscores]

    except Exception as e:
        print(f"Error loading high scores: {e}")

def save_high_score(score, name):
    """
    Adds a new score to the list and saves the updated list to a file.
    """
    global high_scores

    # Get today's date in a "YYYY-MM-DD" format
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Create the new entry and add it to our list
    new_entry = (score, name, current_date, player_level)
    high_scores.append(new_entry)

    # Define a function to get the score, which we'll use for sorting
    def get_score(score_entry):
        return score_entry[0]
        
    # Sort the list again to place the new score correctly
    high_scores.sort(key=get_score, reverse=True)

    # Keep only the top scores
    high_scores = high_scores[:max_highscores]

    try:
        # Open the file to write the new high score list
        with open(HIGHSCORE_FILE, 'w') as f:
            # Write each high score entry to a new line in the file
            for entry in high_scores:
                s, n, d, l = entry # Unpack the tuple for clarity
                f.write(f"{s}|{n}|{d}|{l}\n")

    except Exception as e:
        # If there's an error saving, print a message
        print(f"Error saving high scores: {e}")

def is_high_score(score):
    """
    Checks if a new score is high enough to make the high score list.
    """
    # 1. If the high score board isn't full, any new score is a high score.
    if len(high_scores) < max_highscores:
        return True

    # 2. If the board is full, check against the lowest score on the list.
    # Since the list is sorted, the last item is the lowest score.
    lowest_high_score = high_scores[-1][0] 
    
    # Return True if the new score is better than the lowest high score.
    return score > lowest_high_score
def update_stamina():
    global stamina_level, fatigued, is_sprinting
    if is_sprinting and stamina_level > 0: stamina_level -= stamina_sprint_drain
    elif not is_sprinting and stamina_level < stamina_max: stamina_level += stamina_regen_rate
    stamina_level = max(0, min(stamina_max, stamina_level))
    if stamina_level <= 0: is_sprinting = False
    fatigued = stamina_level < fatigue_threshold
def get_current_speed():
    base = player_speed
    if mobility_boost_active: return base * MOBILITY_BOOST_MULTIPLIER
    if fatigued: return base * fatigue_speed_penalty
    if is_sprinting: return base * sprint_speed_multiplier
    return base
def gain_experience(points):
    global experience_points, player_level, experience_to_next_level, skill_points
    if skill_health_boost >= 3: points = int(points * 1.5)
    experience_points += points
    while experience_points >= experience_to_next_level:
        experience_points -= experience_to_next_level; player_level += 1; skill_points += 1
        experience_to_next_level = int(experience_to_next_level * 1.2)

def fire_weapon():
    """
    Fires a bullet from the ship.

    This function uses a two-step process:
    1. Raycast from the camera through the crosshair to identify the true target.
    2. Fire an actual bullet from the ship's nose directly at that target's center.
    This ensures the player's shots are accurate to what they see.
    """
    global weapon_cooldown, heat_level, overheated, bullets
    
    # Don't fire if the weapon is on cooldown or has overheated.
    if weapon_cooldown > 0 or overheated:
        return

    # === Step 1: Determine what the player is aiming at from the camera's view. ===
    
    # Define the "line of sight" ray, starting from the camera.
    aiming_ray_origin = camera_pos
    
    # Calculate the direction from the camera to the 3D crosshair.
    vector_to_crosshair = [
        crosshair_pos[0] - aiming_ray_origin[0],
        crosshair_pos[1] - aiming_ray_origin[1],
        crosshair_pos[2] - aiming_ray_origin[2]
    ]
    distance = math.sqrt(sum(coord**2 for coord in vector_to_crosshair))
    
    # Normalize the direction vector (make its length 1) for calculations.
    aiming_ray_direction = [coord / distance for coord in vector_to_crosshair] if distance > 0 else [0, 0, 1]

    # === Step 2: Find the closest game object that this aiming ray intersects. ===

    closest_hit_object = None
    min_distance_to_object = float('inf')
    
    # Combine all potential targets into one list for easier checking.
    all_possible_targets = ([boss] if boss and boss.active else []) + enemies
    all_possible_targets += [obs for obs in obstacles if obs.active and obs.type == 'DESTRUCTIBLE']

    for target in all_possible_targets:
        # This is a simplified ray-sphere intersection check.
        # It determines if our aiming ray passes through the target's hitbox.
        vector_to_target = [
            target.pos[0] - aiming_ray_origin[0],
            target.pos[1] - aiming_ray_origin[1],
            target.pos[2] - aiming_ray_origin[2]
        ]
        
        # Project the target's vector onto the ray's direction.
        dot_product = sum(v * d for v, d in zip(vector_to_target, aiming_ray_direction))
        
        # If the dot product is negative, the target is behind the camera.
        if dot_product < 0:
            continue
            
        # Find the closest point on the ray to the target's center.
        closest_point_on_ray = [origin + dot_product * direction for origin, direction in zip(aiming_ray_origin, aiming_ray_direction)]
        
        # Calculate the squared distance from the target's center to that point on the ray.
        distance_from_target_to_ray_sq = sum((p1 - p2)**2 for p1, p2 in zip(target.pos, closest_point_on_ray))
        
        # Use a generic 'hitbox_radius' for checking collision.
        hitbox_radius = getattr(target, 'radius', getattr(target, 'size', 1) * 0.75)

        # If the distance is less than the hitbox radius, we have a hit!
        if distance_from_target_to_ray_sq < hitbox_radius**2:
            distance_from_camera = math.sqrt(sum(v**2 for v in vector_to_target))
            
            # Check if this hit is the closest one we've found so far.
            if distance_from_camera < min_distance_to_object:
                min_distance_to_object = distance_from_camera
                closest_hit_object = target

    # === Step 3: Fire the bullet from the SHIP towards the identified target. ===

    # The bullet originates from the nose of the player's ship.
    nose_offset = 20.0
    bullet_start_position = list(player_pos)
    bullet_start_position[2] += nose_offset # Adjust for the ship's nose.

    # Now, determine the bullet's final travel direction.
    final_bullet_vector = [0, 0, 1] # Default to firing straight ahead.

    if closest_hit_object:
        # If we hit a target, aim the bullet directly at its center.
        vector_to_final_target = [
            closest_hit_object.pos[0] - bullet_start_position[0],
            closest_hit_object.pos[1] - bullet_start_position[1],
            closest_hit_object.pos[2] - bullet_start_position[2]
        ]
    else:
        # If we aimed at empty space, aim the bullet towards the crosshair's location.
        vector_to_final_target = [
            crosshair_pos[0] - bullet_start_position[0],
            crosshair_pos[1] - bullet_start_position[1],
            crosshair_pos[2] - bullet_start_position[2]
        ]
        
    # Normalize the final vector before creating the bullet.
    distance_to_target = math.sqrt(sum(coord**2 for coord in vector_to_final_target))
    if distance_to_target > 0:
        final_bullet_vector = [coord / distance_to_target for coord in vector_to_final_target]

    # Create the bullet and add it to the game world.
    bullets.append(Bullet(bullet_start_position, final_bullet_vector))

    # --- Cooldown and Heat Logic  ---
    weapon_cooldown = max(5, max_weapon_cooldown - (skill_levels['weapon_power'] * 2))
    heat_level += heat_per_shot * (1 - skill_levels['heat_management'] * 0.15)
    if heat_level >= heat_max:
        overheated = True
    charge_special_ability(5)
# =============================
# Drawing Functions
# =============================
# ... (Drawing functions are preserved)
def draw_bar(x, y, width, height, value, max_value, color, label):
    # Switch to 2D drawing mode
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,1000,0,800)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()

    # Calculate fill width
    fill_width = (value / max_value) * width if max_value > 0 else 0
    
    # Draw the colored fill bar using glVertex3f
    glBegin(GL_QUADS)
    glColor3f(*color)
    glVertex3f(x, y, 0); glVertex3f(x + fill_width, y, 0)
    glVertex3f(x + fill_width, y + height, 0); glVertex3f(x, y + height, 0)
    glEnd()
    
    # Draw the white border using glVertex3f
    glColor3f(1.0, 1.0, 1.0) # Set color to white for border and text
    glBegin(GL_LINE_LOOP)
    glVertex3f(x, y, 0); glVertex3f(x + width, y, 0)
    glVertex3f(x + width, y + height, 0); glVertex3f(x, y + height, 0)
    glEnd()
    
    # Draw the text label
    draw_text(x + 5, y - 20, label)

    # Restore 3D drawing mode
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
def draw_button(x, y, w, h, text):
    glColor3f(0.1, 0.2, 0.4); glBegin(GL_QUADS); glVertex3f(x, y, 0); glVertex3f(x + w, y, 0); glVertex3f(x + w, y + h, 0); glVertex3f(x, y + h, 0); glEnd()
    glColor3f(*NEON_CYAN); glBegin(GL_LINES); glVertex3f(x, y, 0); glVertex3f(x+w, y, 0); glVertex3f(x+w, y, 0); glVertex3f(x+w, y+h, 0); glVertex3f(x+w, y+h, 0); glVertex3f(x, y+h, 0); glVertex3f(x, y+h, 0); glVertex3f(x, y, 0); glEnd()
    glColor3f(1, 1, 1); draw_text(x + 20, y + 15, text)
def draw_start_menu():
    # --- Title and Buttons (Existing) ---
    glColor3f(1,1,1); draw_text(250, 600, "ALIEN INVASION SURVIVAL")
    draw_button(350, 400, 300, 50, "START GAME")
    draw_button(350, 300, 300, 50, "HIGH SCORES")
    draw_button(350, 200, 300, 50, "EXIT")

    # --- UPDATED: Controls Display Section ---
    glColor3f(0.8, 0.8, 0.8) 
    
    # --- Movement & Aiming ---
    draw_text(50, 200, "SHIP MOVEMENT")
    draw_text(115, 175, "W")
    draw_text(90, 150, " A S D")
    
    draw_text(750, 200, "AIM CROSSHAIR")
    draw_text(790, 175, "ARROW KEYS") #<-- Updated Text

    # --- Other Actions ---
    draw_text(50, 100, "FIRE LASER: [SPACEBAR]")
    draw_text(50, 75, "EVADE: [Q] / [E]")
    draw_text(50, 50, "CAMERA:   I") #<-- Updated Text
    draw_text(75, 25, "         J, K, L") #<-- Updated Text
    
    draw_text(750, 100, "OPEN SKILLS: [V]")
    draw_text(750, 75, "USE SPECIAL: [F]")
    draw_text(750, 50, "CYCLE SPECIAL: [T]")
    draw_text(400, 25, "TOGGLE CAMERA VIEW: [M]")
def draw_high_score_screen():
    glColor3f(*NEON_CYAN); draw_text(380, 650, "--- HIGH SCORES ---")
    y_pos = 600
    if not high_scores: draw_text(400, y_pos, "No scores yet!")
    for i, (score, name, date, level) in enumerate(high_scores):
        color = ENERGY_YELLOW if i == 0 else (0.9, 0.9, 0.9)
        glColor3f(*color); score_text = f"{i+1}. {name:<10} {score:>6} L{level}"; draw_text(350, y_pos, score_text)
        y_pos -= 40
    draw_button(350, 100, 300, 50, "BACK TO MENU")
def draw_pause_screen():
    glColor3f(*ENERGY_YELLOW); draw_text(450, 500, "PAUSED")
    draw_button(350, 400, 300, 50, "RESUME"); draw_button(350, 300, 300, 50, "EXIT TO MENU")
def draw_crosshair():
    size = 15.0 
    glPushMatrix(); glTranslatef(crosshair_pos[0], crosshair_pos[1], crosshair_pos[2])
    glColor3f(*NEON_GREEN)
    glBegin(GL_LINES); glVertex3f(0, -size, 0); glVertex3f(0, size, 0); glVertex3f(-size, 0, 0); glVertex3f(size, 0, 0); glEnd()
    glPopMatrix()
def draw_background():
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(-1, 1, -1, 1)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glColor3f(*SPACE_BLUE)
    glBegin(GL_QUADS); glVertex3f(-1, -1, 0); glVertex3f( 1, -1, 0); glVertex3f( 1,  1, 0); glVertex3f(-1,  1, 0); glEnd()
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity(); glRasterPos2f(x, y)
    for ch in text: glutBitmapCharacter(font, ord(ch))
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
def init_stars():
    global star_positions
    for _ in range(400): star_positions.append([random.uniform(-ARENA_WIDTH * 2, ARENA_WIDTH * 2), random.uniform(-ARENA_HEIGHT * 2, ARENA_HEIGHT * 2), random.uniform(0, ARENA_DEPTH)])
def draw_stars():
    glPointSize(1.5); glBegin(GL_POINTS)
    for star in star_positions:
        star[2] -= 4.0
        if star[2] < -10: star[2] = ARENA_DEPTH
        alpha = 0.2 + 0.3 * (star[2] / ARENA_DEPTH)
        glColor3f(alpha * 0.8, alpha * 0.8, alpha); glVertex3f(star[0], star[1], star[2])
    glEnd()
def draw_corridor():
    glColor3f(0.3, 0.6, 1.0); glBegin(GL_LINES)
    for z in range(0, int(ARENA_DEPTH), 200):
        glVertex3f(-ARENA_WIDTH, -ARENA_HEIGHT, z); glVertex3f(ARENA_WIDTH, -ARENA_HEIGHT, z); glVertex3f(-ARENA_WIDTH, ARENA_HEIGHT, z); glVertex3f(ARENA_WIDTH, ARENA_HEIGHT, z)
    glVertex3f(-ARENA_WIDTH, -ARENA_HEIGHT, 0); glVertex3f(-ARENA_WIDTH, -ARENA_HEIGHT, ARENA_DEPTH); glVertex3f(ARENA_WIDTH, -ARENA_HEIGHT, 0); glVertex3f(ARENA_WIDTH, -ARENA_HEIGHT, ARENA_DEPTH)
    glVertex3f(-ARENA_WIDTH, ARENA_HEIGHT, 0); glVertex3f(-ARENA_WIDTH, ARENA_HEIGHT, ARENA_DEPTH); glVertex3f(ARENA_WIDTH, ARENA_HEIGHT, 0); glVertex3f(ARENA_WIDTH, ARENA_HEIGHT, ARENA_DEPTH)
    glEnd()

def draw_3d_player():
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(-90,0,1,0)

    # --- Aiming Rotation Logic ---
    # Calculate direction vector from player to crosshair
    dir_x = crosshair_pos[0] - player_pos[0]
    dir_y = crosshair_pos[1] - player_pos[1]
    dir_z = crosshair_pos[2] - player_pos[2]

    # Calculate Yaw (left-right rotation around Y axis)
    yaw = math.degrees(math.atan2(dir_x, dir_z))
    glRotatef(yaw, 0, 1, 0)

    # Calculate Pitch (up-down rotation around X axis)
    horizontal_dist = math.sqrt(dir_x**2 + dir_z**2)
    pitch = math.degrees(math.atan2(-dir_y, horizontal_dist))
    glRotatef(pitch, 0, 0, -1)
    
    # --- Original Model Drawing Code (no changes below) ---
    base_color = [0.2, 0.8, 1.0]
    if special_ability_active or weapon_mastery_active: base_color = [1.0, 0.2, 1.0]
    elif is_sprinting or mobility_boost_active: base_color = [1.0, 1.0, 0.3]
    elif fatigued: base_color = [0.8, 0.4, 0.4]
    glColor3f(*base_color); hull_scale = 1.0 + (skill_health_boost * 0.05)
    glPushMatrix(); glScalef(3.5 * hull_scale, 0.7 * hull_scale, 1.0 * hull_scale); gluSphere(gluNewQuadric(), 8.0, 12, 8); glPopMatrix()
    glColor3f(0.3, 0.3, 0.3); glPushMatrix(); glTranslatef(20.0, 0.0, 0.0); glScalef(0.5, 0.5, 0.5); glRotatef(90, 0, 1, 0); gluCylinder(gluNewQuadric(), 5, 2, 50, 12, 1); glPopMatrix()
    glColor3f(0.1, 0.3, 0.8); glPushMatrix(); glTranslatef(10.0, 3.0, 0.0); glScalef(1.0, 0.8, 0.8); gluSphere(gluNewQuadric(), 6.0, 10, 8); glPopMatrix()
    wing_color = [0.15, 0.6, 0.9]
    if skill_faster_evasion >= 2: wing_color[1] = min(1.0, wing_color[1] + 0.3)
    glColor3f(*wing_color); glPushMatrix(); glTranslatef(0, 0, -15); glScalef(1.0, 0.2, 2); glutSolidCube(10); glPopMatrix()
    glPushMatrix(); glTranslatef(0, 0, 15); glScalef(1.0, 0.2, 2); glutSolidCube(10); glPopMatrix()
    glColor3f(0.15, 0.6, 0.9); glPushMatrix(); glTranslatef(-20, 5, 0); glScalef(0.8, 1.5, 0.2); glutSolidCube(10); glPopMatrix()
    glColor3f(0.3, 0.3, 0.3)
    glPushMatrix(); glTranslatef(-20, 0, -8); glRotatef(-90, 0, 1, 0); gluCylinder(gluNewQuadric(), 3.0, 2.0, 8.0, 8, 4); glPopMatrix()
    glPushMatrix(); glTranslatef(-20, 0, 8); glRotatef(-90, 0, 1, 0); gluCylinder(gluNewQuadric(), 3.0, 2.0, 8.0, 8, 4); glPopMatrix()
    glow_color = NEON_PINK if is_sprinting or mobility_boost_active else (0.3, 0.3, 0.3)
    glColor3f(*glow_color); glPushMatrix(); glTranslatef(-20, 0, -8); gluSphere(gluNewQuadric(), 3, 8, 6); glPopMatrix()
    glPushMatrix(); glTranslatef(-20, 0, 8); gluSphere(gluNewQuadric(), 3, 8, 6); glPopMatrix()
    if special_ability_active and current_special == "SHIELD_BUBBLE": glColor3f(0.0, 0.8, 1.0); gluSphere(gluNewQuadric(), 25.0, 16, 12)
    glPopMatrix()
def draw_boss_health_bar():
    if not boss or not boss.active: return
    health_ratio = boss.health / boss.max_health if boss.max_health > 0 else 0
    health_percentage = int(health_ratio * 100)
    health_color = NEON_GREEN
    if health_ratio < 0.6: health_color = ENERGY_YELLOW
    if health_ratio < 0.3: health_color = WARNING_RED
    glColor3f(*health_color)
    draw_text(350, 700, f"HIVE OVERLORD: {health_percentage}%")
def draw_enhanced_hud():
    # --- Health, Stamina, and Heat Bars  ---
    health_color = NEON_GREEN if (player_health / player_max_health) > 0.6 else ENERGY_YELLOW if (player_health / player_max_health) > 0.3 else WARNING_RED
    draw_bar(15, 750, 200, 25, player_health, player_max_health, health_color, f"HULL: {int(player_health)}")
    stamina_color = NEON_CYAN if not fatigued else WARNING_RED
    draw_bar(15, 700, 180, 20, stamina_level, stamina_max, stamina_color, f"STAMINA: {int(stamina_level)}")
    heat_color = NEON_GREEN if (heat_level / heat_max) < 0.5 else ENERGY_YELLOW if (heat_level / heat_max) < 0.8 else WARNING_RED
    draw_bar(15, 650, 160, 20, heat_level, heat_max, heat_color, f"HEAT: {int(heat_level)}")
    if overheated:
        pulse = 0.5 + 0.5 * math.sin(game_time * 0.2); glColor3f(1.0, pulse * 0.2, 0.0); draw_text(180, 675, "OVERHEATED!")

    # --- Score  ---
    glColor3f(*ENERGY_YELLOW); draw_text(400, 750, f"SCORE: {current_score}")

    # --- Special Ability Bar (Bottom-Right) ---
    special_color = NEON_PINK
    bar_label = f"SPECIAL: {int(special_ability_meter)}"
    if special_ability_meter >= special_ability_max:
        bar_label = "SPECIAL READY!"
    draw_bar(720, 60, 200, 20, special_ability_meter, special_ability_max, special_color, bar_label)
    glColor3f(0.8,0.8,0.8); draw_text(710, 10, f"'{current_special.replace('_', ' ')}' selected (T)")

    # --- Active Ability Text ) ---
    if special_ability_active:
        pulse = 0.7 + 0.3 * math.sin(game_time * 0.2); glColor3f(pulse, 0.2, pulse); secs_left = int(special_ability_timer / 60) + 1
        draw_text(320, 100, f"{current_special.replace('_', ' ')} ACTIVE: {secs_left}s")

    # --- Bottom-Left UI Text ---
    glColor3f(0.7, 0.7, 0.7); draw_text(350, 30, "LVL " + str(player_level))
    exp_ratio = experience_points / experience_to_next_level if experience_to_next_level > 0 else 0
    draw_text(350, 10, f"EXP: [{'#' * int(exp_ratio * 20):<20}]")
    glColor3f(1,1,1); draw_text(10, 10, f"CAM: {camera_mode}") #<-- MOVED to bottom-left

    # --- Top-Right Buttons  ---
    draw_button(800, 750, 100, 40, "PAUSE"); draw_button(910, 750, 80, 40, "EXIT")
def draw_game_over_screen():
    global high_scores
    if name_input_mode:
        glColor3f(*ENERGY_YELLOW); draw_text(350, 500, "NEW HIGH SCORE!")
        draw_text(320, 460, "Enter Your Name (10 chars max):")
        display_name = player_name + "_" if len(player_name) < 10 else player_name
        glColor3f(*NEON_GREEN); draw_text(400, 420, display_name)
        glColor3f(0.8, 0.8, 0.8); draw_text(350, 380, "Press ENTER to save.")
    else:
        glColor3f(*WARNING_RED); draw_text(400, 650, "GAME OVER")
        glColor3f(1,1,1); draw_text(380, 620, f"FINAL SCORE: {current_score}")
        glColor3f(*NEON_CYAN); draw_text(380, 550, "--- HIGH SCORES ---")
        y_pos = 500
        if not high_scores: draw_text(400, y_pos, "No scores yet!")
        for i, (score, name, date, level) in enumerate(high_scores):
            color = ENERGY_YELLOW if i == 0 else (0.9, 0.9, 0.9)
            glColor3f(*color); score_text = f"{i+1}. {name:<10} {score:>6} L{level}"; draw_text(350, y_pos, score_text)
            y_pos -= 40
        glColor3f(1,1,1); draw_text(410, 250, "Press R to Restart")
def draw_skill_menu():
    """Draw the skill menu with temporary and permanent skills."""
    glColor3f(0.1, 0.1, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(200, 150, 0)
    glVertex3f(800, 150, 0)
    glVertex3f(800, 650, 0)
    glVertex3f(200, 650, 0)
    glEnd()

    glColor3f(*NEON_CYAN)
    draw_text(380, 600, "--- SKILL UPGRADES ---")
    glColor3f(*ENERGY_YELLOW)
    draw_text(220, 560, f"Skill Points: {skill_points}")

    y_pos = 500

    # --- Temporary Skills ---
    for name, data in temp_skills.items():
        if data["active"]:
            color = NEON_PINK
            status = "[ACTIVE]"
        elif skill_points >= data["cost"]:
            color = NEON_GREEN
            status = f"(Cost: {data['cost']})"
        else:
            color = (0.7, 0.7, 0.7)
            status = "(Locked)"

        glColor3f(*color)
        label = "Mobility Boost (2 mins)" if name == "mobility_boost" else "Weapon Mastery (2 mins)"
        draw_text(220, y_pos, f"{label} {status}")
        y_pos -= 40

    # --- Permanent Skills ---
    for name, costs in SKILL_COSTS.items():
        level = skill_levels[name]
        if level >= len(costs):
            color = NEON_PINK
            status = f"[MAXED] ({level}/{len(costs)})"
        elif can_upgrade_skill(name):
            color = NEON_GREEN
            cost = costs[level]
            status = f"[{level}/{len(costs)}] (Cost: {cost})"
        else:
            color = (0.7, 0.7, 0.7)
            cost = costs[level]
            status = f"[{level}/{len(costs)}] (Need {cost})"

        glColor3f(*color)
        draw_text(220, y_pos, f"{name.replace('_', ' ').title()} {status}")
        y_pos -= 40

    glColor3f(1, 1, 1)
    draw_text(350, 200, "Press 'V' to close menu")

# =============================
# Input & Main Loop
# =============================

def specialKeyListener(key, x, y):
    # AIMING with the Arrow Keys
    global crosshair_move_y_timer, crosshair_move_y_dir, crosshair_move_x_timer, crosshair_move_x_dir

    if key == GLUT_KEY_UP:
        crosshair_move_y_timer = INPUT_TIMEOUT; crosshair_move_y_dir = 1
    elif key == GLUT_KEY_DOWN:
        crosshair_move_y_timer = INPUT_TIMEOUT; crosshair_move_y_dir = -1
    elif key == GLUT_KEY_LEFT:
        crosshair_move_x_timer = INPUT_TIMEOUT; crosshair_move_x_dir = +1
    elif key == GLUT_KEY_RIGHT:
        crosshair_move_x_timer = INPUT_TIMEOUT; crosshair_move_x_dir = -1
def keyboardListener(key, x, y):
    # CAMERA controls with IJKL and other controls
    global player_name, name_input_mode, is_sprinting, fatigued, game_state, camera_mode, player_move_y_timer, player_move_y_dir, player_move_x_timer, player_move_x_dir, fire_timer, skill_points, mobility_boost_active, mobility_boost_timer, weapon_mastery_active, weapon_mastery_timer, is_evading, evade_timer, evade_direction, camera_angle, camera_height
    
    if game_state == "GAME_OVER" and name_input_mode:
        if key == b'\r':
            if player_name: save_high_score(current_score, player_name); name_input_mode = False; load_high_scores()
        elif key == b'\x08': player_name = player_name[:-1]
        else:
            try:
                char = key.decode('ascii')
                if char.isalnum() and len(player_name) < 10: player_name += char.upper()
            except UnicodeDecodeError: pass
        return

    if game_state == "SKILL_MENU":
        if key == b'1' and skill_points >= 1 and not mobility_boost_active:
            skill_points -= 1; mobility_boost_active = True; mobility_boost_timer = MOBILITY_BOOST_DURATION
        elif key == b'2' and skill_points >= 1 and not weapon_mastery_active:
            skill_points -= 1; weapon_mastery_active = True; weapon_mastery_timer = WEAPON_MASTERY_DURATION
        elif key == b'3': upgrade_skill('faster_evasion')
        elif key == b'4': upgrade_skill('weapon_power')
        elif key == b'5': upgrade_skill('heat_management')
        elif key == b'6': upgrade_skill('stamina_efficiency')
        elif key == b'7': upgrade_skill('health_boost')
        elif key == b'v': game_state = "PLAYING"
        return

    # Player and Weapon Controls
    if key == b'w': player_move_y_timer = INPUT_TIMEOUT; player_move_y_dir = 1
    elif key == b's': player_move_y_timer = INPUT_TIMEOUT; player_move_y_dir = -1
    elif key == b'a': player_move_x_timer = INPUT_TIMEOUT; player_move_x_dir = 1
    elif key == b'd': player_move_x_timer = INPUT_TIMEOUT; player_move_x_dir = -1
    elif key == b' ': fire_timer = INPUT_TIMEOUT
    
    # Camera Controls on IJKL 
    elif key == b'i': camera_height += 5.0
    elif key == b'k': camera_height -= 5.0
    elif key == b'j': camera_angle += 5.0
    elif key == b'l': camera_angle -= 5.0

    # Other Action Keys
    elif key == b'c': is_sprinting = not fatigued and not is_sprinting
    elif key == b'v': game_state = "SKILL_MENU"
    elif key == b'm':
        if camera_mode == "FOLLOW": camera_mode = "CENTERED"
        elif camera_mode == "CENTERED": camera_mode = "FIRST_PERSON"
        else: camera_mode = "FOLLOW"
    elif key == b'q' and not is_evading and can_evade(): is_evading = True; evade_timer = EVADE_DURATION; evade_direction = 1; consume_evade_stamina(); trigger_camera_shake(30,20)
    elif key == b'e' and not is_evading and can_evade(): is_evading = True; evade_timer = EVADE_DURATION; evade_direction = -1; consume_evade_stamina(); trigger_camera_shake(30,20)
    elif key == b'f': activate_special_ability()
    elif key == b't': cycle_special_ability()
    elif key == b'r' and game_state == "GAME_OVER" and not name_input_mode: game_state = "START_MENU"

    # Clamp camera height after any adjustment
    camera_height = max(20.0, min(200.0, camera_height))
def mouseListener(button, state, x, y): 
    global game_state, pre_game_timer, boss
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        y = 800 - y 
        if game_state == "START_MENU":
            if 350 < x < 650 and 400 < y < 450: # Start Game
                reset_game(); game_state = "PRE_GAME"; pre_game_timer = PRE_GAME_DURATION
            elif 350 < x < 650 and 300 < y < 350: # High Scores
                game_state = "HIGH_SCORES"
            elif 350 < x < 650 and 200 < y < 250: # Exit
                glutLeaveMainLoop()
        elif game_state == "HIGH_SCORES":
            if 350 < x < 650 and 100 < y < 150: game_state = "START_MENU"
        elif game_state == "PLAYING":
            if 800 < x < 900 and 750 < y < 790: game_state = "PAUSED"
            elif 910 < x < 990 and 750 < y < 790: game_state = "START_MENU"; boss = None; enemies.clear()
        elif game_state == "PAUSED":
            if 350 < x < 650 and 400 < y < 450: # Resume button
                game_state = "RESUMING"
                pre_game_timer = 180 # 3 seconds at 60fps
            elif 350 < x < 650 and 300 < y < 350: game_state = "START_MENU"; boss = None; enemies.clear()
def reset_game():
    global current_score, game_time, player_health, player_pos, bullets, enemies, enemy_bullets, asteroids, boss, heat_level, overheated, weapon_cooldown, is_evading, evade_timer, evade_cooldown, stamina_level, is_sprinting, special_ability_meter, name_input_mode, player_name, spawn_timer, crosshair_pos, current_wave
    current_score, game_time, heat_level, spawn_timer, current_wave = 0, 0, 0, 0, 0
    overheated, is_evading, is_sprinting, name_input_mode = False, False, False, False
    player_name = ""; evade_timer, evade_cooldown, weapon_cooldown = 0, 0, 0
    player_pos = [0.0, 0.0, 0.0]; crosshair_pos = [0.0, 0.0, ARENA_DEPTH - 800]
    apply_skill_effects(); player_health, stamina_level, special_ability_meter = player_max_health, stamina_max, 0
    spawn_obstacles(20)
    bullets, enemies, enemy_bullets, asteroids = [], [], [], []; boss = None
def handle_player_death():
    global game_state, name_input_mode, player_name
    if player_health <= 0 and game_state == "PLAYING" and not INVINCIBLE_MODE:
        game_state = "GAME_OVER"
        if is_high_score(current_score): name_input_mode = True; player_name = ""
        else: load_high_scores()
def idle():
    global game_time, weapon_cooldown, heat_level, overheated, evade_timer, is_evading, evade_cooldown, player_pos, spawn_timer, player_move_y_timer, player_move_x_timer, crosshair_move_y_timer, crosshair_move_x_timer, fire_timer, mobility_boost_active, mobility_boost_timer, weapon_mastery_active, weapon_mastery_timer, game_state, pre_game_timer, wave_transition_timer, boss,camera_shake_duration,camera_shake_intensity,player_flash_timer
     # --- Camera Shake Decay Logic ---
    if camera_shake_duration > 0:
        camera_shake_duration -= 1
        camera_shake_intensity *= 0.9 # Smoothly reduce intensity
    else:
        camera_shake_intensity = 0.0

    # ------------------------------------

        # --- Player Flash Decay Logic ---
    if player_flash_timer > 0:
        player_flash_timer -= 1
   

    if game_state not in ["PLAYING", "PRE_GAME", "WAVE_TRANSITION","RESUMING"]:
        glutPostRedisplay(); return
    game_time += 1
    if game_state == "PRE_GAME":
        pre_game_timer -=1
        if pre_game_timer <= 0: game_state = "WAVE_TRANSITION"; wave_transition_timer = WAVE_TRANSITION_DURATION
    elif game_state == "RESUMING":
        pre_game_timer -= 1
        if pre_game_timer <= 0:
            game_state = "PLAYING"
    if game_state == "WAVE_TRANSITION":
        wave_transition_timer -= 1
        if wave_transition_timer <= 0:
            game_state = "PLAYING"; start_next_wave()
    if player_move_y_timer > 0: player_pos[1] += player_move_y_dir * get_current_speed(); player_move_y_timer -= 1
    if player_move_x_timer > 0: player_pos[0] += player_move_x_dir * get_current_speed(); player_move_x_timer -= 1
    if crosshair_move_y_timer > 0: crosshair_pos[1] += crosshair_move_y_dir * crosshair_speed; crosshair_move_y_timer -= 1
    if crosshair_move_x_timer > 0: crosshair_pos[0] += crosshair_move_x_dir * crosshair_speed; crosshair_move_x_timer -= 1
    # Continuous Bullets for a laser effect using fire_timer
    if fire_timer > 0 and game_state == "PLAYING": fire_weapon(); fire_timer -=1
    player_pos[0] = max(-ARENA_WIDTH, min(ARENA_WIDTH, player_pos[0])); player_pos[1] = max(-ARENA_HEIGHT, min(ARENA_HEIGHT, player_pos[1]))
    crosshair_pos[0] = max(-ARENA_WIDTH, min(ARENA_WIDTH, crosshair_pos[0])); crosshair_pos[1] = max(-ARENA_HEIGHT, min(ARENA_HEIGHT, crosshair_pos[1]))
    if is_evading:
        player_pos[0] += (get_evade_distance() / EVADE_DURATION) * evade_direction; evade_timer -= 1
        if evade_timer <= 0: is_evading = False; evade_cooldown = get_evade_cooldown()
    if evade_cooldown > 0: evade_cooldown -= 1
    if weapon_cooldown > 0: weapon_cooldown -= 1
    if heat_level > 0: heat_level = max(0, heat_level - heat_cool_rate)
    if overheated and heat_level <= (heat_max * 0.1): overheated = False
    if mobility_boost_timer > 0: mobility_boost_timer -= 1
    else: mobility_boost_active = False
    if weapon_mastery_timer > 0: weapon_mastery_timer -= 1
    else: weapon_mastery_active = False
    if game_state == "PLAYING" and len(enemies) == 0 and (not boss or not boss.active):
        game_state = "WAVE_TRANSITION"; wave_transition_timer = WAVE_TRANSITION_DURATION
        # --- Time Scale Logic ---
    global time_scale
    if special_ability_active and current_special == "TIME_SLOW":
        time_scale = 0.4 # Slow down to 40% speed
    else:
        time_scale = 1.0 # Return to normal speed
    # -----------------------------
    update_stamina(); update_special_ability(); update_bullets(); update_enemies_and_bullets(); check_collisions(); handle_player_death(); 
    glutPostRedisplay()

def setupCamera():
    glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(fovY, 1.25, 0.1, ARENA_DEPTH * 1.5)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()

    cam_x, cam_y, cam_z = 0, 0, 0
    look_at_x, look_at_y, look_at_z = 0, 0, 1

    if camera_mode == "FIRST_PERSON":
        # Position the camera inside the ship's "cockpit"
        cam_x, cam_y, cam_z = player_pos[0]+5, player_pos[1] +10, player_pos[2] + 20
        # Aim the camera directly at the 3D crosshair
        look_at_x, look_at_y, look_at_z = crosshair_pos[0], crosshair_pos[1], crosshair_pos[2]
    else: # FOLLOW or CENTERED modes
        current_cam_angle = 0.0 if camera_mode == "CENTERED" else camera_angle
        angle_rad = math.radians(current_cam_angle)
        offset_x = math.sin(angle_rad) * camera_distance; offset_z = -math.cos(angle_rad) * camera_distance
        cam_x, cam_y, cam_z = player_pos[0] + offset_x, player_pos[1] + camera_height, player_pos[2] + offset_z
        look_at_x, look_at_y, look_at_z = player_pos[0], player_pos[1], player_pos[2] + 50

    # Apply Camera Shake Offsets 
    if camera_shake_duration > 0:
        shake_offset_x = random.uniform(-camera_shake_intensity, camera_shake_intensity)
        shake_offset_y = random.uniform(-camera_shake_intensity, camera_shake_intensity)
        cam_x += shake_offset_x
        cam_y += shake_offset_y
     # --- Store the final camera position ---
    global camera_pos
    camera_pos = [cam_x, cam_y, cam_z]
    # -----------------------------------------
    gluLookAt(cam_x, cam_y, cam_z, look_at_x, look_at_y, look_at_z, 0.0, 1.0, 0.0)
def showScreen():
    global player_flash_timer
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT); draw_background(); glClear(GL_DEPTH_BUFFER_BIT) 
    if game_state not in ["START_MENU", "HIGH_SCORES"]:
        glLoadIdentity(); glViewport(0, 0, 1000, 800); setupCamera()
        draw_stars(); draw_corridor()
        for bullet in bullets: bullet.draw()
        for bullet in enemy_bullets: bullet.draw()
        for asteroid in asteroids: asteroid.draw()
        for obstacle in obstacles: obstacle.draw() #<-- ADD THIS LINE
        if boss and boss.active: boss.draw()
        for enemy in enemies: enemy.draw()
        # if camera_mode != "FIRST_PERSON": # Only draw the player if not in first-person
        draw_3d_player()
        glClear(GL_DEPTH_BUFFER_BIT); draw_crosshair()
       # --- Draw Player Damage Flash Border  ---
        if player_flash_timer > 0:
            glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity(); gluOrtho2D(0,1000,0,800)
            glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()

            glColor3f(1.0, 0.0, 0.0) # Solid Red
            border_thickness = 10.0
            # Top bar
            glBegin(GL_QUADS); glVertex3f(0, 800-border_thickness, 0); glVertex3f(1000, 800-border_thickness, 0); glVertex3f(1000, 800, 0); glVertex3f(0, 800, 0); glEnd()
            # Bottom bar
            glBegin(GL_QUADS); glVertex3f(0, 0, 0); glVertex3f(1000, 0, 0); glVertex3f(1000, border_thickness, 0); glVertex3f(0, border_thickness, 0); glEnd()
            # Left bar
            glBegin(GL_QUADS); glVertex3f(0, 0, 0); glVertex3f(border_thickness, 0, 0); glVertex3f(border_thickness, 800, 0); glVertex3f(0, 800, 0); glEnd()
            # Right bar
            glBegin(GL_QUADS); glVertex3f(1000-border_thickness, 0, 0); glVertex3f(1000, 0, 0); glVertex3f(1000, 800, 0); glVertex3f(1000-border_thickness, 800, 0); glEnd()

            glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
        # -----------------------------------------------------------------

    
    glClear(GL_DEPTH_BUFFER_BIT)
    if game_state == "START_MENU": draw_start_menu()
    elif game_state == "HIGH_SCORES": draw_high_score_screen()
    elif game_state == "PAUSED": draw_pause_screen()
    elif game_state == "GAME_OVER": draw_game_over_screen()
    elif game_state == "SKILL_MENU": draw_skill_menu()
    else: 
        draw_enhanced_hud()
        if boss and boss.active: draw_boss_health_bar()
        if game_state == "PRE_GAME":
            glColor3f(1,1,1); draw_text(400, 400, f"GET READY... {int(pre_game_timer/60) + 1}")
        if game_state == "WAVE_TRANSITION":
            glColor3f(1,1,1); draw_text(450, 400, f"WAVE {current_wave+1}")
        elif game_state == "RESUMING":
            glColor3f(1,1,1); draw_text(420, 400, f"RESUMING IN {int(pre_game_timer/60) + 1}...")

    glutSwapBuffers()
def main():
    glutInit(); glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800); glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Alien Invasion Survival - Final Build")
    glEnable(GL_DEPTH_TEST)
    init_stars(); load_high_scores(); apply_skill_effects()
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    print("Game Initialized.")
    glutMainLoop()

if __name__ == "__main__":
    main()