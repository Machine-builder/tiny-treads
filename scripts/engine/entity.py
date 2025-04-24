import random
import string
import typing
from typing import Any, Dict, Tuple, Union
import pygame

from . import network
from .entity_renderer import EntityRenderer

if typing.TYPE_CHECKING:
    from .world import World

id_chars = string.ascii_letters+string.digits
def create_entity_id():
    return ''.join([random.choice(id_chars) for _ in range(16)])

class Entity():
    position: pygame.Vector2
    velocity: pygame.Vector2
    drag: float
    size: pygame.Vector2
    rect: pygame.Rect
    renderer: EntityRenderer
    
    def __init__(
            self,
            id: int,
            world: "World",
            type_id: str,
            position: pygame.Vector2,
            size: pygame.Vector2,
            renderer: Union[EntityRenderer, None]):
    
        self.world: "World" = world
        self.id: int = self.world.assign_new_entity_id() if id == -1 else id
        self.type_id: str = type_id
        
        self.position = position
        self.velocity = pygame.Vector2(0, 0)
        self.rotation = 0
        self.rotational_velocity = 0
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
        self.update_visuals(dt)
    
    def update_visuals(self, dt: float):
        self._update_rect_position()
        if self.renderer is not None: self.renderer.update(dt)
    
    def draw(self, surface: pygame.Surface):
        if self.renderer is None:
            return

        self.renderer.draw(self, surface)
    
    def update_from_snapshot(self, update: Tuple):
        (id_,
         position_x, position_y,
         velocity_x, velocity_y,
         rotation, rotational_velocity) = update
        self.position.x = position_x
        self.position.y = position_y
        self.velocity.x = velocity_x
        self.velocity.y = velocity_y
        self.rotation = rotation
        self.rotational_velocity = rotational_velocity