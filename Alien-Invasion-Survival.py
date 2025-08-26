from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import time
import math
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18, GLUT_BITMAP_HELVETICA_10, GLUT_BITMAP_HELVETICA_12, GLUT_BITMAP_9_BY_15

# Camera-related variables
camera_pos = [0, 400, 400]
camera_shake_offset = [0, 0, 0]
camera_shake_timer = 0

fovY = 60  # Reduced for better view
GRID_LENGTH = 400  # Smaller arena for better gameplay
rand_var = 423

# Colors for space theme
SPACE_BLUE = (0.1, 0.1, 0.3)
NEON_CYAN = (0, 1, 1)
NEON_GREEN = (0, 1, 0.2)
NEON_PINK = (1, 0, 0.8)
ALIEN_GREEN = (0.2, 1, 0.2)
WARNING_RED = (1, 0.2, 0.2)
ENERGY_YELLOW = (1, 1, 0)

# Player variables
player_pos = [0, 0, 20]
player_angle = 0
player_health = 100
player_max_health = 100
player_speed = 4
current_score = 0
game_time = 0

# Weapon system variables
bullets = []  # List to store active bullets
weapon_cooldown = 0
max_weapon_cooldown = 15  # Frames between shots
bullet_speed = 8
muzzle_flash_timer = 0

# Simple animation variables for UI effects
ui_pulse = 0
star_positions = []

class Bullet:
    def __init__(self, x, y, z, angle):
        self.x = x
        self.y = y
        self.z = z
        self.angle = angle
        self.speed = bullet_speed
        self.life = 150  # Bullet lifetime in frames
        self.active = True
    
    def update(self):
        if not self.active:
            return
        
        # Move bullet forward
        self.x += math.cos(math.radians(self.angle)) * self.speed
        self.y += math.sin(math.radians(self.angle)) * self.speed
        
        # Decrease lifetime
        self.life -= 1
        if self.life <= 0:
            self.active = False
        
        # Check boundaries
        if abs(self.x) > GRID_LENGTH * 1.5 or abs(self.y) > GRID_LENGTH * 1.5:
            self.active = False
    
    def draw(self):
        if not self.active:
            return
        
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        # Draw glowing bullet - using basic sphere
        glow = 0.8 + 0.2 * math.sin(game_time * 0.5)
        glColor3f(0, glow, 1)  # Cyan energy bullet
        
        # Main bullet core
        gluSphere(gluNewQuadric(), 1.5, 8, 6)
        
        # Energy trail effect - simplified
        glColor3f(0.3, 0.6, 1)
        for i in range(3):
            trail_offset = i * 3
            trail_x = self.x - math.cos(math.radians(self.angle)) * trail_offset
            trail_y = self.y - math.sin(math.radians(self.angle)) * trail_offset
            
            glPushMatrix()
            glTranslatef(trail_x - self.x, trail_y - self.y, 0)
            alpha = 0.6 - i * 0.2
            glColor3f(0, alpha, alpha * 1.5)
            gluSphere(gluNewQuadric(), 1.0 - i * 0.2, 6, 4)
            glPopMatrix()
        
        glPopMatrix()

# Initialize stars for background effect
def init_stars():
    global star_positions
    star_positions = []
    for i in range(100):
        x = random.uniform(-GRID_LENGTH*2, GRID_LENGTH*2)
        y = random.uniform(-GRID_LENGTH*2, GRID_LENGTH*2)
        z = random.uniform(50, 200)
        size = random.uniform(1, 3)
        star_positions.append([x, y, z, size])

def draw_stars():
    """Draw animated stars in the background"""
    glPointSize(2)
    glBegin(GL_POINTS)
    for star in star_positions:
        # Pulsing effect
        alpha = 0.5 + 0.3 * math.sin(game_time * 0.1 + star[0] * 0.01)
        glColor3f(alpha, alpha, alpha * 1.2)
        glVertex3f(star[0], star[1], star[2])
    glEnd()

def draw_space_grid():
    """Draw a futuristic grid floor with glowing lines"""
    glLineWidth(1)
    grid_size = 50
    
    # Main grid in cyan
    glColor3f(0.3, 0.6, 1.0)  # Softer blue-cyan
    glBegin(GL_LINES)
    
    # Vertical lines
    for i in range(-GRID_LENGTH, GRID_LENGTH + 1, grid_size):
        glVertex3f(i, -GRID_LENGTH, 0)
        glVertex3f(i, GRID_LENGTH, 0)
    
    # Horizontal lines
    for i in range(-GRID_LENGTH, GRID_LENGTH + 1, grid_size):
        glVertex3f(-GRID_LENGTH, i, 0)
        glVertex3f(GRID_LENGTH, i, 0)
    glEnd()
    
    # Add glowing center cross
    glLineWidth(3)
    pulse = 0.7 + 0.3 * math.sin(game_time * 0.05)
    glColor3f(0, pulse, pulse)
    glBegin(GL_LINES)
    # Center cross
    glVertex3f(-100, 0, 1)
    glVertex3f(100, 0, 1)
    glVertex3f(0, -100, 1)
    glVertex3f(0, 100, 1)
    glEnd()
    
    glLineWidth(1)

def draw_arena_boundaries():
    """Draw glowing arena boundaries"""
    glLineWidth(4)
    pulse = 0.5 + 0.5 * math.sin(game_time * 0.08)
    glColor3f(pulse, 0, pulse)  # Pulsing purple
    
    glBegin(GL_LINE_LOOP)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 10)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 10)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 10)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 10)
    glEnd()
    
    # Corner markers
    corner_size = 30
    glBegin(GL_LINES)
    # Top-left corner
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 10)
    glVertex3f(-GRID_LENGTH + corner_size, GRID_LENGTH, 10)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 10)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH - corner_size, 10)
    
    # Top-right corner
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 10)
    glVertex3f(GRID_LENGTH - corner_size, GRID_LENGTH, 10)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 10)
    glVertex3f(GRID_LENGTH, GRID_LENGTH - corner_size, 10)
    
    # Bottom-right corner
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 10)
    glVertex3f(GRID_LENGTH - corner_size, -GRID_LENGTH, 10)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 10)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH + corner_size, 10)
    
    # Bottom-left corner
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 10)
    glVertex3f(-GRID_LENGTH + corner_size, -GRID_LENGTH, 10)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 10)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH + corner_size, 10)
    glEnd()
    
    glLineWidth(1)

def fire_weapon():
    """Create a new bullet at player position"""
    global weapon_cooldown, muzzle_flash_timer
    
    if weapon_cooldown <= 0:
        # Calculate bullet spawn position (front of ship)
        spawn_distance = 15
        bullet_x = player_pos[0] + math.cos(math.radians(player_angle)) * spawn_distance
        bullet_y = player_pos[1] + math.sin(math.radians(player_angle)) * spawn_distance
        bullet_z = player_pos[2]
        
        # Create new bullet
        new_bullet = Bullet(bullet_x, bullet_y, bullet_z, player_angle)
        bullets.append(new_bullet)
        
        # Set cooldown and muzzle flash
        weapon_cooldown = max_weapon_cooldown
        muzzle_flash_timer = 5
        
        return True
    return False

def draw_bullets():
    """Draw all active bullets and update them"""
    global bullets
    
    # Update and draw bullets
    for bullet in bullets[:]:  # Use slice to avoid modification during iteration
        bullet.update()
        if bullet.active:
            bullet.draw()
        else:
            bullets.remove(bullet)

def draw_weapon_effects():
    """Draw weapon muzzle flash and other effects"""
    global muzzle_flash_timer
    
    if muzzle_flash_timer > 0:
        # Draw muzzle flash at weapon positions
        flash_intensity = muzzle_flash_timer / 5.0
        
        glPushMatrix()
        glTranslatef(player_pos[0], player_pos[1], player_pos[2])
        glRotatef(player_angle, 0, 0, 1)
        
        # Left weapon muzzle flash
        glColor3f(1, flash_intensity, 0)  # Orange flash
        glPushMatrix()
        glTranslatef(-6, 12, -1)
        gluSphere(gluNewQuadric(), 2 * flash_intensity, 8, 6)
        glPopMatrix()
        
        # Right weapon muzzle flash
        glPushMatrix()
        glTranslatef(6, 12, -1)
        gluSphere(gluNewQuadric(), 2 * flash_intensity, 8, 6)
        glPopMatrix()
        
        glPopMatrix()
        
        muzzle_flash_timer -= 1

def draw_3d_player():
    """Draw a fully 3D futuristic spaceship"""
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(player_angle, 0, 0, 1)
    
    # === MAIN HULL - 3D Fuselage ===
    glColor3f(0.2, 0.8, 1.0)  # Bright cyan hull
    glPushMatrix()
    glScalef(1.5, 3.0, 0.8)
    gluSphere(gluNewQuadric(), 8, 12, 8)
    glPopMatrix()
    
    # === COCKPIT - Forward section ===
    glColor3f(0.1, 0.3, 0.8)  # Darker blue cockpit
    glPushMatrix()
    glTranslatef(0, 12, 3)
    glScalef(0.8, 1.2, 0.6)
    gluSphere(gluNewQuadric(), 6, 10, 8)
    glPopMatrix()
    
    # === WINGS - Left and Right ===
    # Left wing
    glColor3f(0.15, 0.6, 0.9)
    glPushMatrix()
    glTranslatef(-12, -2, 0)
    glRotatef(90, 0, 1, 0)
    glScalef(0.3, 1.8, 2.0)
    glutSolidCube(8)
    glPopMatrix()
    
    # Right wing
    glPushMatrix()
    glTranslatef(12, -2, 0)
    glRotatef(90, 0, 1, 0)
    glScalef(0.3, 1.8, 2.0)
    glutSolidCube(8)
    glPopMatrix()
    
    # === ENGINE PODS - 3D Cylinders ===
    # Left engine
    glColor3f(0.3, 0.3, 0.3)  # Dark metallic
    glPushMatrix()
    glTranslatef(-8, -12, 0)
    glRotatef(90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 3, 2, 8, 8, 4)
    glPopMatrix()
    
    # Right engine
    glPushMatrix()
    glTranslatef(8, -12, 0)
    glRotatef(90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 3, 2, 8, 8, 4)
    glPopMatrix()
    
    # === ENGINE GLOW EFFECTS ===
    glow = 0.6 + 0.4 * math.sin(game_time * 0.2)
    
    # Left engine glow
    glColor3f(0, glow, 1)
    glPushMatrix()
    glTranslatef(-8, -18, 0)
    gluSphere(gluNewQuadric(), 4, 8, 6)
    glPopMatrix()
    
    # Right engine glow
    glPushMatrix()
    glTranslatef(8, -18, 0)
    gluSphere(gluNewQuadric(), 4, 8, 6)
    glPopMatrix()
    
    # Central engine boost
    glColor3f(glow, glow * 0.8, 1)
    glPushMatrix()
    glTranslatef(0, -16, 1)
    gluSphere(gluNewQuadric(), 2.5, 8, 6)
    glPopMatrix()
    
    # === WEAPON MOUNTS ===
    # Left weapon
    glColor3f(0.8, 0.8, 0.8)  # Metallic silver
    glPushMatrix()
    glTranslatef(-6, 8, -1)
    glRotatef(90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 1, 0.5, 4, 6, 4)
    glPopMatrix()
    
    # Right weapon
    glPushMatrix()
    glTranslatef(6, 8, -1)
    glRotatef(90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 1, 0.5, 4, 6, 4)
    glPopMatrix()
    
    # === NAVIGATION LIGHTS ===
    # Wingtip strobes
    strobe = math.sin(game_time * 0.4) > 0.5
    if strobe:
        glColor3f(1, 0, 0)  # Red strobe
    else:
        glColor3f(0.3, 0, 0)  # Dim red
    
    # Left wingtip light
    glPushMatrix()
    glTranslatef(-15, -2, 1)
    gluSphere(gluNewQuadric(), 1.2, 6, 6)
    glPopMatrix()
    
    # Right wingtip light (green)
    if strobe:
        glColor3f(0, 1, 0)  # Green strobe
    else:
        glColor3f(0, 0.3, 0)  # Dim green
    
    glPushMatrix()
    glTranslatef(15, -2, 1)
    gluSphere(gluNewQuadric(), 1.2, 6, 6)
    glPopMatrix()
    
    # === COCKPIT DETAILS ===
    # Cockpit window
    glColor3f(0.2, 0.4, 0.8)
    glPushMatrix()
    glTranslatef(0, 15, 4)
    glScalef(0.6, 0.8, 0.3)
    gluSphere(gluNewQuadric(), 4, 8, 6)
    glPopMatrix()
    
    # === HULL DETAILS ===
    # Top fin
    glColor3f(0.1, 0.5, 0.8)
    glPushMatrix()
    glTranslatef(0, 0, 8)
    glRotatef(90, 1, 0, 0)
    glScalef(0.2, 1.5, 1.0)
    glutSolidCube(6)
    glPopMatrix()
    
    # === SHADOW/DEPTH EFFECT ===
    # Subtle shadow under the ship
    glColor3f(0.05, 0.05, 0.15)  # Very dark shadow
    glPushMatrix()
    glTranslatef(0, 0, -2)
    glScalef(1.8, 3.5, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(-5, -8, 0)
    glVertex3f(5, -8, 0)
    glVertex3f(5, 8, 0)
    glVertex3f(-5, 8, 0)
    glEnd()
    glPopMatrix()
    
    glPopMatrix()

def draw_space_hud():
    """Draw space-themed HUD with futuristic styling"""
    global ui_pulse
    ui_pulse += 0.1
    
    # === LEFT PANEL - SHIP STATUS ===
    glColor3f(*NEON_CYAN)
    draw_text(15, 750, "=== SHIP STATUS ===", GLUT_BITMAP_HELVETICA_18)
    
    # Health with color coding
    health_ratio = player_health / player_max_health
    if health_ratio > 0.6:
        glColor3f(*NEON_GREEN)
        status_text = "OPTIMAL"
    elif health_ratio > 0.3:
        glColor3f(*ENERGY_YELLOW)
        status_text = "DAMAGED"
    else:
        glColor3f(*WARNING_RED)
        status_text = "CRITICAL"
    
    draw_text(15, 720, f"HULL INTEGRITY: {int(health_ratio * 100)}%", GLUT_BITMAP_HELVETICA_12)
    draw_text(15, 700, f"STATUS: {status_text}", GLUT_BITMAP_HELVETICA_12)
    
    # Weapon status
    if weapon_cooldown > 0:
        glColor3f(*WARNING_RED)
        weapon_status = "CHARGING"
    else:
        glColor3f(*NEON_GREEN)
        weapon_status = "READY"
    
    draw_text(15, 680, f"WEAPONS: {weapon_status}", GLUT_BITMAP_HELVETICA_12)
    draw_text(15, 660, f"ENERGY: 100%", GLUT_BITMAP_HELVETICA_12)
    
    # === CENTER TOP - MISSION INFO ===
    glColor3f(*NEON_PINK)
    draw_text(400, 750, "ALIEN INVASION SURVIVAL", GLUT_BITMAP_HELVETICA_18)
    glColor3f(*ENERGY_YELLOW)
    draw_text(420, 720, f"WAVE: 1  |  SCORE: {current_score}", GLUT_BITMAP_HELVETICA_12)
    
    # Pulsing mission status
    pulse_alpha = 0.7 + 0.3 * math.sin(ui_pulse)
    glColor3f(pulse_alpha, 1, pulse_alpha)
    draw_text(450, 700, "MISSION: SURVIVE", GLUT_BITMAP_HELVETICA_12)
    
    # === RIGHT PANEL - TACTICAL ===
    glColor3f(*NEON_CYAN)
    draw_text(720, 750, "=== TACTICAL ===", GLUT_BITMAP_HELVETICA_18)
    glColor3f(*ALIEN_GREEN)
    draw_text(720, 720, "ENEMIES: 0 DETECTED", GLUT_BITMAP_HELVETICA_12)
    draw_text(720, 700, "THREAT LEVEL: LOW", GLUT_BITMAP_HELVETICA_12)
    draw_text(720, 680, f"PROJECTILES: {len(bullets)}", GLUT_BITMAP_HELVETICA_12)
    
    # === BOTTOM LEFT - CONTROLS ===
    glColor3f(0.7, 0.7, 1)
    draw_text(15, 150, "=== CONTROLS ===", GLUT_BITMAP_HELVETICA_12)
    draw_text(15, 130, "WASD: Navigate Ship", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 110, "SPACE: Fire Weapons", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 90, "Q/E: Evasive Maneuvers", GLUT_BITMAP_HELVETICA_10)
    draw_text(15, 70, "ARROWS: Camera Control", GLUT_BITMAP_HELVETICA_10)
    
    # === BOTTOM RIGHT - SCAN RESULTS ===
    glColor3f(*NEON_GREEN)
    draw_text(650, 150, "=== SECTOR SCAN ===", GLUT_BITMAP_HELVETICA_12)
    draw_text(650, 130, "Area: Secure", GLUT_BITMAP_HELVETICA_10)
    draw_text(650, 110, f"Coordinates: ({int(player_pos[0])}, {int(player_pos[1])})", GLUT_BITMAP_HELVETICA_10)
    draw_text(650, 90, f"Mission Time: {int(game_time/60)}:{int(game_time%60):02d}", GLUT_BITMAP_HELVETICA_10)
    
    # === CENTER CROSSHAIRS ===
    glColor3f(1, 0.3, 0.3)
    draw_text(485, 410, "+", GLUT_BITMAP_HELVETICA_18)
    glColor3f(0.7, 0.7, 0.7)
    draw_text(470, 390, "TARGET", GLUT_BITMAP_9_BY_15)

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_12):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def keyboardListener(key, x, y):
    """Handles keyboard inputs for player movement"""
    global player_pos, player_angle
    
    # Movement with boundary checking
    if key == b'w':  # Forward
        new_x = player_pos[0] + math.cos(math.radians(player_angle)) * player_speed
        new_y = player_pos[1] + math.sin(math.radians(player_angle)) * player_speed
        if abs(new_x) < GRID_LENGTH - 30 and abs(new_y) < GRID_LENGTH - 30:
            player_pos[0] = new_x
            player_pos[1] = new_y
    
    if key == b's':  # Backward
        new_x = player_pos[0] - math.cos(math.radians(player_angle)) * player_speed
        new_y = player_pos[1] - math.sin(math.radians(player_angle)) * player_speed
        if abs(new_x) < GRID_LENGTH - 30 and abs(new_y) < GRID_LENGTH - 30:
            player_pos[0] = new_x
            player_pos[1] = new_y
    
    if key == b'a':  # Rotate left
        player_angle += 3
    
    if key == b'd':  # Rotate right
        player_angle -= 3
    
    if key == b' ':  # Spacebar - Fire weapon
        fire_weapon()
    
    # Future: Add evasion, special abilities
    if key == b'q':  # Left evasion (placeholder)
        pass
    
    if key == b'e':  # Right evasion (placeholder)
        pass

def specialKeyListener(key, x, y):
    """Handles special key inputs for camera control"""
    global camera_pos
    
    x_pos, y_pos, z_pos = camera_pos
    
    if key == GLUT_KEY_UP:
        z_pos += 15
    if key == GLUT_KEY_DOWN:
        z_pos = max(100, z_pos - 15)  # Don't go too low
    if key == GLUT_KEY_LEFT:
        x_pos -= 15
    if key == GLUT_KEY_RIGHT:
        x_pos += 15
    
    camera_pos = [x_pos, y_pos, z_pos]

def mouseListener(button, state, x, y):
    """Handles mouse inputs for firing"""
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        fire_weapon()

def setupCamera():
    """Configure camera with cinematic angle"""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 2000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    x, y, z = camera_pos
    # Follow player with offset
    target_x = player_pos[0]
    target_y = player_pos[1]
    
    gluLookAt(x, y, z, target_x, target_y, 0, 0, 0, 1)

def idle():
    """Continuous updates"""
    global game_time, weapon_cooldown
    game_time += 1
    
    # Update weapon cooldown
    if weapon_cooldown > 0:
        weapon_cooldown -= 1
    
    # Score will only increase from specific actions:
    # - Killing aliens
    # - Surviving waves
    # - Collecting power-ups
    # - Time-based survival bonus (maybe every 10 seconds)
    glutPostRedisplay()

def showScreen():
    """Main display function with space theme"""
    # Clear with space background
    glClearColor(*SPACE_BLUE, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, 1000, 800)
    
    setupCamera()
    
    # Draw space environment
    draw_stars()
    draw_space_grid()
    draw_arena_boundaries()
    
    # Draw game objects
    draw_3d_player()
    draw_bullets()  # Draw bullets
    draw_weapon_effects()  # Draw muzzle flash and other effects
    
    # Draw UI
    draw_space_hud()
    
    glutSwapBuffers()

def main():
    init_stars()
    
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)  
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Alien Invasion Survival - Space Combat")
    
    glEnable(GL_DEPTH_TEST)  # Allowed exception

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    
    glutMainLoop()


if __name__ == "__main__":
    main()