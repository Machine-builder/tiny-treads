import math
import time

import pygame
from scripts import engine, packets

class ClientModel():
    def __init__(self):
        self.entity_id: str = None

packet_handler = packets.get_packet_handler()
server_ip = engine.network.Utility.get_local_ip()
server_port_tcp = 9183
server_port_udp = 9184
system = engine.network.HSystem(server_ip, server_port_tcp, server_port_udp, ClientModel, packet_handler)

print(f'Server running on {server_ip}:{server_port_tcp}')

world = engine.world.World(is_server=True)
server_entity = engine.Entity(world, pygame.Vector2(50, 50), pygame.Vector2(32, 32), None)
world.create_entity(server_entity, True)

elapsed = 0
ct = 0.0
while True:
    now = time.time()
    dt = 0.05
    ct += dt
    
    server_entity.position.x = 100+math.sin(ct*10)*20
    
    r = system.pump()
    
    for client in r.new_clients:
        print('Connected:', client.addr_tcp)
        
        client_entity = engine.Entity(world, pygame.Vector2(100, 50), pygame.Vector2(32, 32), None)
        
        client_model: ClientModel = client.model
        client_model.entity_id = client_entity.id
        
        # Send entities to this new client
        for entity in world.entities.values():
            e = engine.network.Event(packets.PacketDefinitions.EntityCreate, entity.id, 'typeid')
            system.send_event_tcp(e, client.conn)
            
        world.create_entity(client_entity, True)
        
        # Alert all clients of this new entity
        for other_client in system.clients.values():
            e = engine.network.Event(packets.PacketDefinitions.EntityCreate, client_entity.id, 'typeid')
            system.send_event_tcp(e, other_client.conn)
        
        system.send_event_tcp(engine.network.Event(packets.PacketDefinitions.ClientSetLocalEntity, client_entity.id, True), client.conn)
    
    for client in r.disconnected_clients:
        print('Disconnected:', client.addr_tcp)
        client_model: ClientModel = client.model
        entity_id = client_model.entity_id
        world.destroy_entity(entity_id)
        system.send_event_tcp(engine.network.Event(packets.PacketDefinitions.EntityDestroy, entity_id))
        
    for client, event in r.events_tcp:
        # print('tcp:', event)
        world.handle_network_event(event)
        
        if event.type == packets.PacketDefinitions.RTTPing and not event.args[0]:
            system.send_event_tcp(engine.network.Event(packets.PacketDefinitions.RTTPing, True), event.from_connection)
    
    for client, event in r.events_udp:
        # print('udp:', event)
        world.handle_network_event(event)
    
    world.update(dt)
    world_events = world.pump_network_events()
    for event in world_events[0]:
        system.send_event_tcp(event)
    for event in world_events[1]:
        system.send_event_udp(event)
    
    elapsed = time.time() - now
    added_delay = 0.05 - elapsed
    if added_delay > 0:
        time.sleep(added_delay)
    else:
        ... # Server is running slow, log this?