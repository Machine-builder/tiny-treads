import time
from typing import Dict, List, Set, Tuple

import pygame

from .entity import Entity
from . import network

class World():
    entities: Dict[str, Entity]
    
    _network_authority_entities: Set[str]
    
    def __init__(self):
        self.entities = {}
        self._network_authority_entities = set()
        self.last_network_pump = time.time()
    
    def add_entity(self, entity: Entity, network_authortiy: bool = False):
        if entity.uid in self.entities: return
        self.entities[entity.uid] = entity
        if network_authortiy:
            self.set_entity_network_authority(entity, True)
    
    def remove_entity(self, entity_uid: str):
        if not entity_uid in self.entities: return
        del self.entities[entity_uid]
        if entity_uid in self._network_authority_entities:
            self._network_authority_entities.remove(entity_uid)
    
    def set_entity_network_authority(self, entity: Entity, value: bool):
        entity_is_network_authority = entity.uid in self._network_authority_entities
        if value and not entity_is_network_authority:
            self._network_authority_entities.add(entity.uid)
        elif not value and entity_is_network_authority:
            self._network_authority_entities.remove(entity.uid)
    
    def handle_network_event(self, event: network.Event):
        try:
            if event.event == 'ENTITY:CREATE':
                e = Entity.from_creation_event(event)
                self.add_entity(e)
            elif event.event == 'ENTITY:ATTRIBUTES':
                e = self.entities[event.uid]
                if not e.uid in self._network_authority_entities:
                    e.update_attributes(**event.attributes)
        except:
            pass
    
    def pump_network_events(self, as_client: bool = False) -> Tuple[List[network.Event], List[network.Event]]:
        # Ensure we only send network events once per tick to not spam the server
        now = time.time()
        if now < self.last_network_pump+0.05:
            return [], []
        
        self.last_network_pump = now
        events_tcp = []
        events_udp = []
        entities = [self.entities[uid] for uid in self._network_authority_entities] if as_client else self.entities.values()
        for entity in entities:
            attrs = entity.get_attributes_dict()
            del attrs['velocity']
            events_udp.append(network.Event(
                'ENTITY:ATTRIBUTES',
                uid=entity.uid,
                attributes=attrs
            ))
        
        return events_tcp, events_udp
    
    def update(self, dt: float):
        for entity in self.entities.values():
            entity.update(dt)
    
    def draw(self, surface: pygame.Surface):
        for entity in self.entities.values():
            entity.draw(surface)