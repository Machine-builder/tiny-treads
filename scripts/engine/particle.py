import math
from typing import Tuple
import pygame


class Particle():
    position: pygame.Vector2
    velocity: pygame.Vector2
    drag: float
    linear_acceleration: pygame.Vector2
    lifetime: float
    lifetime_max: float
    
    def __init__(self,
                 position: pygame.Vector2,
                 velocity: pygame.Vector2,
                 lifetime: float = 1,
                 drag: float = 1,
                 linear_acceleration: pygame.Vector2 = None,
                 color: Tuple[int, int, int] = (255, 255, 255)):
        self.position = position
        self.velocity = velocity
        self.drag = drag
        self.linear_acceleration = linear_acceleration or pygame.Vector2(0, 5)
        self.lifetime = lifetime
        self.lifetime_max = lifetime
        self.color = color
    
    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        self.position += self.velocity*dt
        self.velocity -= self.velocity*self.drag*dt
        self.velocity += self.linear_acceleration*dt
        return self.lifetime > 0
    
    def draw(self, surface: pygame.Surface):
        pygame.draw.circle(surface, self.color, self.position, math.ceil(3*self.lifetime/self.lifetime_max))