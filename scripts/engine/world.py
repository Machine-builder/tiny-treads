from collections import deque
import random
import time
from typing import Dict, List, Set, Tuple, Union

import pygame

from . import Snapshot

from . import network
from .. import packets
from . import EntityRegistry
from .entity import Entity, EntityRenderer
from .particle import Particle

class World():
    entities: Dict[str, Entity]
    local_entities: Set[str]
    
    def __init__(self, entity_registry: EntityRegistry, is_server: bool = False):
        self.is_server = is_server
        self.entity_registry: EntityRegistry = entity_registry
        self.entities = {}
        self.local_entities = set()
        self.snapshot_buffer: deque[Snapshot] = deque()
        self.render_delay = 0.2 if not self.is_server else 0
        
        self.reference_time = time.time()
        
        self.particles: List[Particle] = []
        
        self._s1_time = 0
        self._s2_time = 0
    
    def handle_network_event(self, event: network.Event):
        if event.type == packets.PacketDefinitions.EntityCreate:
            id, type_id = event.args
            print(f'Create entity {id} {type_id}')
            entity: Entity = self.entity_registry.get_instance(id, type_id, self, pygame.Vector2(50, 50))
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
    
        elif event.type == packets.PacketDefinitions.EntityUpdatePhysMulti:
            reference_time, updates = event.args
            snapshot = Snapshot(reference_time, time.time(), updates)
            if self.is_server:
                self.apply_snapshot(snapshot)
            else:
                self.snapshot_buffer.append(snapshot)
                if len(self.snapshot_buffer) > 60: # TODO: Base on render time instead of arbitrary
                    self.snapshot_buffer.popleft()
    
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
        
        phys_updates = []
        
        if self.is_server:
            update_entities = self.entities.values()
        else:
            update_entities = [e for e in [self.entities.get(entity_id) for entity_id in self.local_entities] if e]
        
        for entity in update_entities:
            entity_id = entity.id
            entity = self.entities.get(entity_id)
            if entity is None: continue
            phys_updates.append((
                entity_id,
                entity.position.x,
                entity.position.y,
                entity.velocity.x,
                entity.velocity.y,
                entity.rotation,
                entity.rotational_velocity
            ),)

        if len(phys_updates) > 0:
            events_udp.append(network.Event(
                packets.PacketDefinitions.EntityUpdatePhysMulti,
                time.time() - self.reference_time, phys_updates
            ))
        
        return events_tcp, events_udp
    
    def apply_snapshot(self, snapshot: Snapshot):
        # Used by server to instantly process snapshot
        for update in snapshot.entity_states:
            entity_id = update[0]
            
            entity = self.entities.get(entity_id)
            
            if entity is None or (entity_id in self.local_entities and not self.is_server):
                continue
            
            entity.update_from_snapshot(update)
            entity.update_visuals(0.0)
    
    def update(self, dt: float):
        # some entities should be interpolated not use proper physics
        # have a way to specify this
        
        if not self.is_server:
            current_time = time.time()
            render_time = current_time - self.render_delay
            snapshot = self.interpolate_snapshot(render_time)
        
            if snapshot:
                for update in snapshot.entity_states:
                    entity_id = update[0]
                    
                    entity = self.entities.get(entity_id)
                    
                    if entity is None or (entity_id in self.local_entities and not self.is_server):
                        continue
                    
                    entity.update_from_snapshot(update)
            
            for entity in self.entities.values():
                entity.update_visuals(dt)
        
        # Update local entities directly
        for entity_id in self.local_entities:
            entity = self.entities[entity_id]
            entity.update(dt)
        
        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]
    
    def interpolate_snapshot(self, render_time: float) -> Union[None, Snapshot]:
        if len(self.snapshot_buffer) < 2: return None
        
        for i in range(len(self.snapshot_buffer) - 1):
            s1 = self.snapshot_buffer[i]
            s2 = self.snapshot_buffer[i+1]
            if s1.time <= render_time <= s2.time:
                # snapshots surround render_time
                t = (render_time - s1.time) / (s2.time - s1.time)
                
                self._s1_time = s1.time
                self._s2_time = s2.time
                
                updates_by_id = {}
                for update in s1.entity_states:
                    updates_by_id[update[0]] = update
                
                interpolated_updates = []
                
                for update in s2.entity_states:
                    entity_id = update[0]
                    if entity_id not in updates_by_id: continue
                    
                    old = updates_by_id[entity_id]
                    new = update
                    
                    pos_x = old[1]*(1-t) + new[1]*t
                    pos_y = old[2]*(1-t) + new[2]*t
                    vel_x = old[3]*(1-t) + new[3]*t
                    vel_y = old[4]*(1-t) + new[4]*t
                    rotation = old[5]*(1-t) + new[5]*t
                    rotational_velocity = old[6]*(1-t) + new[6]*t
                    
                    interpolated_updates.append((
                        entity_id,
                        pos_x, pos_y,
                        vel_x, vel_y,
                        rotation, rotational_velocity
                    ))
                
                return Snapshot(0, render_time, interpolated_updates)
    
    def draw(self, surface: pygame.Surface):
        for entity in self.entities.values():
            entity.draw(surface)
        [p.draw(surface) for p in self.particles]