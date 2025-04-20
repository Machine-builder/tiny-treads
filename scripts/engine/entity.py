import random
import string
import typing
from typing import Any, Dict, Union
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
            world: "World",
            position: pygame.Vector2,
            size: pygame.Vector2,
            renderer: Union[EntityRenderer, None]):
    
        self.world = world
        self.id = self.world.assign_new_entity_id()
        
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
    
    def get_attributes_dict(self) -> Dict[str, Any]:
        return {
            'position': self.position,
            'velocity': self.velocity,
            'drag': self.drag,
            'size': self.size
        }
    
    @staticmethod
    def from_creation_event(event: network.Event):
        assert event.event == 'ENTITY:CREATE', f'Attemting to initialize Entity instance from event of type "{event.event}", expected "ENTITY:CREATE"'
        attributes: Dict[str, Any] = event.attributes
        position: pygame.Vector2 = attributes['position']
        velocity: pygame.Vector2 = attributes['velocity']
        drag: float = attributes['drag']
        size: pygame.Vector2 = attributes['size']
        
        e = Entity( position, size, EntityRenderer() )
        e.velocity = velocity
        e.drag = drag
        
        e.id = event.id
        
        return e
    
    def update_attributes(self, **kwargs):
        if 'position' in kwargs:
            self.position = kwargs['position']
        if 'velocity' in kwargs:
            self.velocity = kwargs['velocity']
        if 'drag' in kwargs:
            self.drag = kwargs['drag']
        if 'size' in kwargs:
            self.size = kwargs['size']