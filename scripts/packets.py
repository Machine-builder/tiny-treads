import struct
from typing import List, Tuple
import pygame
from . import engine

class PacketDefinitions:
    NetInitTCP = 1
    NetInitUDP = 2
    NetInitFinal = 3
    RTTPing = 4
    
    EntityCreate = 301
    EntityDestroy = 302
    EntityUpdateAttr = 303
    EntityUpdatePhys = 304
    EntityUpdatePhysMulti = 305
    
    ClientSetLocalEntity = 401

def get_packet_handler():
    packet_handler = engine.network.get_default_hybrid_packet_handler()
    
    @packet_handler.register(PacketDefinitions.EntityCreate)
    def entity_create():
        # id, typeid
        def preprocess(id: int, typeid: str):
            return id, typeid.encode()
        def postprocess(id: int, typeid: bytes):
            return id, typeid.rstrip(b'\x00').decode()
        return '<H16s', preprocess, postprocess
    
    @packet_handler.register(PacketDefinitions.EntityDestroy)
    def entity_destroy():
        # id
        return '<H', None, None
    
    @packet_handler.register(PacketDefinitions.EntityUpdateAttr)
    def entity_update_attr():
        # id, hp, hpmax
        return '<HII', None, None

    @packet_handler.register(PacketDefinitions.EntityUpdatePhys)
    def entity_update_phys():
        # id, vec2(x, y), vec2(vx, vy), angle, vangle
        def preprocess(id: int, position: pygame.Vector2, velocity: pygame.Vector2, angle: float, angular_velocity: float):
            return id, position.x, position.y, velocity.x, velocity.y, angle, angular_velocity
        def postprocess(id: int, x: float, y: float, vx: float, vy: float, a: float, va: float):
            return id, pygame.Vector2(x, y), pygame.Vector2(vx, vy), a, va
        return '<H2d4f', preprocess, postprocess

    @packet_handler.register(PacketDefinitions.EntityUpdatePhysMulti)
    def entity_update_phys_multi():
        # id, vec2(x, y), vec2(vx, vy), angle, vangle
        def packer(reference_time: float, entity_updates: List[Tuple[int, pygame.Vector2, pygame.Vector2, float, float]]):
            result = b''
            result += struct.pack('<dH', reference_time, len(entity_updates))
            for update in entity_updates:
                result += struct.pack('<H2d4f', update[0], update[1], update[2], update[3], update[4], update[5], update[6])
            return result
        
        def unpacked(data: bytes):
            updates = []
            reference_time, count, = struct.unpack_from('<dH', data)
            offset = 8+2
            for _ in range(count):
                updates.append(struct.unpack_from('<H2d4f', data, offset))
                offset += 2 + 2*8 + 4*4 # one unsigned short, 2 doubles, 4 floats
            return (reference_time, updates)
        
        return packer, unpacked
    
    @packet_handler.register(PacketDefinitions.ClientSetLocalEntity)
    def client_set_local_entity():
        # id, local?
        return '<H?', None, None
    
    return packet_handler

def test():
    p = get_packet_handler()
    
    bytes_ = p.pack(engine.network.Event(
        PacketDefinitions.EntityUpdatePhysMulti,
        [
            (0, pygame.Vector2(2, 3), pygame.Vector2(0.1, 0.5), 45, 0),
            (1, pygame.Vector2(8, 2), pygame.Vector2(0.0, -5), -90, 0)
        ]
    ))
    
    event = p.unpack(bytes_)
    
    print(event.args)