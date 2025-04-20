import random
import time
from typing import Dict, List, Set, Tuple

import pygame

from .entity import Entity, EntityRenderer
from . import network
from .. import packets

class World():
    entities: Dict[str, Entity]
    local_entities: Set[str]
    
    def __init__(self, is_server: bool = False):
        self.is_server = is_server
        self.entities = {}
        self.local_entities = set()
    
    def handle_network_event(self, event: network.Event):
        if event.type == packets.PacketDefinitions.EntityCreate:
            id, type_id = event.args
            print(f'Create entity {id}')
            entity = Entity(self, pygame.Vector2(50, 50), pygame.Vector2(32, 32), EntityRenderer())
            entity.id = id
            self.create_entity(entity, False)
        
        elif event.type == packets.PacketDefinitions.EntityDestroy:
            id, = event.args
            self.destroy_entity(id)
    
        elif event.type == packets.PacketDefinitions.EntityUpdatePhys:
            id, position, velocity, rotation, rotational_velocity = event.args
            if not self.is_server and id in self.local_entities:
                return # Do not update if this is client-controlled
            entity = self.entities.get(id)
            if entity is None: return
            entity.position = position
            entity.velocity = velocity
            entity.rotation = rotation
            entity.rotational_velocity = rotational_velocity
            # These attributes should be saved to the snapshot buffer instead of immediately applied
    
    def assign_new_entity_id(self) -> int:
        id = -1
        while id == -1 or id in self.entities:
            id = random.randint(0, 65535)
        return id
    
    def create_entity(self, entity: Entity, is_local: bool = False):
        self.entities[entity.id] = entity
        if is_local:
            self.local_entities.add(entity.id)
        
    def destroy_entity(self, entity_id: int):
        if not entity_id in self.entities: return
        del self.entities[entity_id]
        self.local_entities.discard(entity_id)
    
    def set_entity_local(self, entity_id: int, value: bool):
        if value: self.local_entities.add(entity_id)
        else: self.local_entities.discard(entity_id)
    
    def pump_network_events(self) -> Tuple[List[network.Event], List[network.Event]]:
        events_tcp = []
        events_udp = []
        
        for entity_id in self.local_entities:
            entity = self.entities.get(entity_id)
            if entity is None: continue
            events_udp.append(network.Event(
                packets.PacketDefinitions.EntityUpdatePhys,
                entity_id,
                entity.position,
                entity.velocity,
                entity.rotation,
                entity.rotational_velocity
            ))
        
        return events_tcp, events_udp
    
    def update(self, dt: float):
        # some entities should be interpolated not use proper physics
        # have a way to specify this
        if self.is_server:
            for entity in self.entities.values():
                entity.update(dt)
        else:
            for entity in self.entities.values():
                if entity.id in self.local_entities:
                    entity.update(dt)
                else:
                    entity.update_visuals(dt) # These visuals should be interpolated from snapshot buffer
    
    def draw(self, surface: pygame.Surface):
        for entity in self.entities.values():
            entity.draw(surface)