from typing import List

import pygame

from .entity import Entity

class World():
    entities: List[Entity]
    
    def __init__(self):
        self.entities = []
    
    def update(self, dt: float):
        pass
    
    def draw(self, surface: pygame.Surface):
        pass