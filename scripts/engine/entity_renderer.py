from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .entity import Entity

class EntityRenderer():
    def __init__(self):
        ...
        
        # render an entity based off attributes
        # this is a placeholder class and will contain stub methods
        # other classes will build off it
    
    def update(self, dt: float): ...
    
    def draw(self, entity: "Entity", surface: pygame.Surface):
        pygame.draw.rect(surface, (255, 0, 0), entity.rect, 1)