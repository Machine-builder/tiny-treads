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
        return '<Hddffff', preprocess, postprocess
    
    @packet_handler.register(PacketDefinitions.ClientSetLocalEntity)
    def client_set_local_entity():
        # id, local?
        return '<H?', None, None
    
    return packet_handler