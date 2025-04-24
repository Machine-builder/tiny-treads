import typing
import pygame

if typing.TYPE_CHECKING:
    from . import World

class EntityRegistry:
    def __init__(self):
        self.definitions = {}
    
    def register_entity(self, type_id: str, class_):
        self.definitions[type_id] = class_
    
    def get_instance(self, id: int, type_id: str, world: "World", position: pygame.Vector2):
        assert type_id in self.definitions, f"Cannot call get_instance() - {type_id} does not exist in entity registry"
        return self.definitions[type_id](id, world, position)