import math
import random
import time
import pygame
from . import engine

class TankEntity(engine.Entity):
    def __init__(self, id: int, world: engine.World, position: pygame.Vector2, with_renderer: bool = True):
        super().__init__(
            id,
            world,
            'tank',
            pygame.Vector2(random.uniform(50, 150), random.uniform(50, 150)),
            pygame.Vector2(20, 20),
            None)
        if with_renderer:
            self.renderer = TankRenderer(self.id)
        
        self.rotation = random.uniform(0, 360)
        
        self.timer_smoke_particle = engine.Timer(0.1)
    
    def get_direction(self) -> pygame.Vector2:
        return pygame.Vector2(math.sin(-self.rotation), math.cos(-self.rotation))
    
    def process_inputs(self, dt: float, input_vector: pygame.Vector2, keys_held: pygame.key.ScancodeWrapper):
        movement_speed = 800 if not keys_held[pygame.K_LSHIFT] else 1400
        self.rotation += input_vector.x*5*dt
        self.velocity = pygame.Vector2(
            math.sin(-self.rotation)*input_vector.y*movement_speed*dt,
            math.cos(-self.rotation)*input_vector.y*movement_speed*dt
        )
    
    def update_visuals(self, dt: float):
        super().update_visuals(dt)
        
        tick_duration = 0.1 if self.velocity.length() > 0 else 0.25
        self.timer_smoke_particle.timeout_max = tick_duration
        if self.timer_smoke_particle.tick(dt):
            c = random.randint(60, 110)
            self.world.particles.append(engine.Particle(
                self.position+pygame.Vector2(0, -15),
                pygame.Vector2(random.uniform(-18, 18), -16+random.uniform(-18, 18)),
                drag=2,
                lifetime=random.uniform(0.5, 1),
                linear_acceleration=pygame.Vector2(0, -10),
                color=(c, c, c)))

class TankRenderer(engine.entity.EntityRenderer):
    def __init__(self, entity_id: int):
        super().__init__()

        image_drive_base = pygame.image.load('./assets/sheets/tank_drive.png')
        image_drive_color = pygame.image.load('./assets/sheets/tank_drive_color.png')
        image_shoot_base = pygame.image.load('./assets/sheets/tank_shoot.png')
        image_shoot_color = pygame.image.load('./assets/sheets/tank_shoot_color.png')
        
        random.seed(entity_id)
        hue_shift = random.uniform(-180, 180)
        saturation = random.uniform(-0.2, 0.2)
        value = random.uniform(-0.2, 0.2)
        image_drive_base.blit(pygame.transform.hsl(image_drive_color, hue_shift, saturation, value))
        image_shoot_base.blit(pygame.transform.hsl(image_shoot_color, hue_shift, saturation, value))
        
        self.spritesheet_driving = engine.spritesheet.Spritesheet(image_drive_base, (48, 48))
        self.spritesheet_shooting = engine.spritesheet.Spritesheet(image_shoot_base, (48, 48))
        
        self.rect = pygame.Rect(0, 0, 48, 48)
    
    def draw(self, entity: engine.Entity, surface: pygame.Surface):
        self.rect.center = entity.rect.center
        
        rad_11_25 = math.radians(11.25)
        rad_22_5 = math.radians(22.5)
        rad_45 = math.radians(45)
        rotation_index = math.floor((entity.rotation+rad_11_25)/rad_22_5)%16
        
        frame = self.spritesheet_driving.get_frame(
            rotation_index,
            int(time.time()*12) if entity.velocity.length_squared()>0 else 0
        )
        
        shadow_rect = pygame.Rect(0, 0, 26, 16)
        shadow_rect.center = (entity.rect.centerx, entity.rect.centery+6)
        pygame.draw.ellipse(surface, (128, 97, 56), shadow_rect)
        
        surface.blit(frame, self.rect)