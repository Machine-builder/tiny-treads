from typing import Union
import pygame

from .entity_renderer import EntityRenderer

class Entity():
    position: pygame.Vector2
    velocity: pygame.Vector2
    drag: float
    size: pygame.Vector2
    rect: pygame.Rect
    renderer: EntityRenderer
    
    def __init__(
            self,
            position: pygame.Vector2,
            size: pygame.Vector2,
            renderer: Union[EntityRenderer, None]):
        
        self.position = position
        self.velocity = pygame.Vector2(0, 0)
        self.drag = 0.1
        self.size = size
        self.rect = pygame.Rect(0, 0, self.size.x, self.size.y)
        self._update_rect_position()
        
        self.renderer = renderer
    
    def _update_rect_position(self):
        self.rect.centerx = self.position.x
        self.rect.bottom = self.position.y
    
    def update(self, dt: float):
        self.position += self.velocity*dt 
        self.velocity -= self.velocity*self.drag*dt
    
    def draw(self, surface: pygame.Surface):
        if self.renderer is None:
            return

        # TODO: render entity image to surface