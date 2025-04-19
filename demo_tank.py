import math
import random
from typing import Dict, List
import pygame
from pygame.locals import *

from scripts import engine

pygame.init()

pygame.display.set_caption('Spritesheet Viewer')

screen = pygame.Surface((256, 256))
display = pygame.display.set_mode((512, 512))

image_heart = pygame.image.load('./assets/heart.png')
image_heart_half = pygame.image.load('./assets/heart_half.png')
image_heart_empty = pygame.image.load('./assets/heart_empty.png')

class World:
    def __init__(self):
        self.particles: List[engine.Particle] = []
    
    def update(self, dt: float):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface: pygame.Surface):
        [p.draw(surface) for p in self.particles]

class Tank:
    def __init__(self, world: World):
        self.world = world
        
        self.position = pygame.Vector2(64, 64)
        self.velocity = pygame.Vector2(0, 0)
        self.rotation = 0
        
        self.rect = pygame.Rect(0, 0, 48, 48)
        self.rect.center = self.position
        self.hitbox = pygame.Rect(0, 0, 32, 32)
        self.hitbox.center = self.position

        image_drive_base = pygame.image.load('./blender/sheets/tank_drive.png')
        image_drive_color = pygame.image.load('./blender/sheets/tank_drive_color.png')
        image_shoot_base = pygame.image.load('./blender/sheets/tank_shoot.png')
        image_shoot_color = pygame.image.load('./blender/sheets/tank_shoot_color.png')
        image_drive_base.blit(pygame.transform.hsl(image_drive_color, -90, 0.25, 0))
        image_shoot_base.blit(pygame.transform.hsl(image_shoot_color, -90, 0.25, 0))
        self.spritesheet_driving = engine.spritesheet.Spritesheet(image_drive_base, (48, 48))
        self.spritesheet_shooting = engine.spritesheet.Spritesheet(image_shoot_base, (48, 48))
        
        self.shooting_started_at = -10.0
        self.time = 0.0
    
    def apply_controls(self, dt: float, keys_held: pygame.key.ScancodeWrapper):
        self.rotation += (keys_held[K_d]-keys_held[K_a])*5*dt
        # self.rotation %= 6.283 # ~360 degrees
        forward_inputs = keys_held[K_w]-keys_held[K_s]
        if self.time - self.shooting_started_at < 0.25: forward_inputs = 0
        forward_x = math.sin(-self.rotation)*forward_inputs*850*dt
        forward_y = math.cos(-self.rotation)*forward_inputs*850*dt
        self.velocity.x = forward_x
        self.velocity.y = forward_y
    
    def get_direction(self) -> pygame.Vector2:
        return pygame.Vector2(math.sin(-self.rotation), math.cos(-self.rotation))
    
    def get_barrel_position(self) -> pygame.Vector2:
        direction = self.get_direction()
        direction.y *= 0.7
        return self.position + direction*14 + pygame.Vector2(0, -2)
    
    def process_event(self, event: pygame.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                barrel_position = self.get_barrel_position()
                direction = self.get_direction()
                for _ in range(5):
                    c = random.randint(60, 110)
                    self.world.particles.append(engine.Particle(
                        barrel_position.copy(),
                        direction*random.uniform(30, 55) + pygame.Vector2(0 + random.uniform(-12, 12), -10 + random.uniform(-12, 12)),
                        drag=2,
                        lifetime=random.uniform(0.5, 1),
                        linear_acceleration=pygame.Vector2(0, -5),
                        color=(c, c, c)))
                self.world.particles.append(engine.Particle(
                    barrel_position.copy(),
                    direction*150 + pygame.Vector2(0 + random.uniform(-5, 5), random.uniform(-5, 5)),
                    drag=0.25,
                    lifetime=3,
                    color=(30, 30, 30)))
                self.shooting_started_at = self.time
    
    def update(self, dt: float):
        self.time += dt
        self.position += self.velocity*dt
        self.velocity -= self.velocity*5*dt
        self.rect.center = self.position
        self.hitbox.center = self.position
    
    def draw(self, surface: pygame.Surface):
        rad_11_25 = math.radians(11.25)
        rad_22_5 = math.radians(22.5)
        rad_45 = math.radians(45)
        rotation_index = math.floor((self.rotation+rad_11_25)/rad_22_5)%16
        
        if self.shooting_started_at > self.time-8/16:
            frame = self.spritesheet_shooting.get_frame(rotation_index, min(int((self.time-self.shooting_started_at)*16), 7))
        else:
            frame = self.spritesheet_driving.get_frame(rotation_index, int(self.time*12) if self.velocity.length_squared()>0 else 0)
        
        pygame.draw.line(surface,
                         (128, 97, 56),
                         self.position + pygame.Vector2(0, 3),
                         self.position + pygame.Vector2(math.sin(-self.rotation), math.cos(-self.rotation))*14 + pygame.Vector2(0, 3),
                         5)
        
        pygame.draw.ellipse(surface, (128, 97, 56), pygame.Rect(self.hitbox.left+5, self.hitbox.top+13, self.hitbox.width-10, self.hitbox.height-16))
        
        # pygame.draw.line(surface,
        #                  (0, 0, 0),
        #                  self.position + pygame.Vector2(0, 3),
        #                  self.position + pygame.Vector2(math.sin(-self.rotation), math.cos(-self.rotation))*20 + pygame.Vector2(0, 3),
        #                  1)
        
        surface.blit(frame, self.rect)
        
        surface.blit(image_heart, self.position+pygame.Vector2(-3-8, -18 + math.sin(self.time*20)*2))
        surface.blit(image_heart_half, self.position+pygame.Vector2(-3, -18 + math.sin(self.time*20+1)*2))
        surface.blit(image_heart_empty, self.position+pygame.Vector2(-3+8, -18 + math.sin(self.time*20+2)*2))

world = World()
tank = Tank(world)

clock = pygame.time.Clock()
ct = 0.0
running = True
while running:
    dt = clock.tick(61)/1000
    ct += dt
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        tank.process_event(event)
    
    keys_held = pygame.key.get_pressed()
    
    tank.apply_controls(dt, keys_held)
    tank.update(dt)
    world.update(dt)
    
    screen.fill((150, 117, 72))
    
    tank.draw(screen)
    world.draw(screen)
    
    display.blit(pygame.transform.scale(screen, (512, 512)))
    pygame.display.flip()

pygame.quit()