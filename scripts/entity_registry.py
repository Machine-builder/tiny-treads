from .engine import EntityRegistry
from .tank import TankEntity

def get_entity_registry() -> EntityRegistry:
    er = EntityRegistry()
    er.register_entity('tank', TankEntity)
    return er