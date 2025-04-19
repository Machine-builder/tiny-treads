import time

import pygame
from scripts import engine

class ClientModel():
    def __init__(self):
        self.entity_uid: str = None

server_ip = engine.network.Utility.get_local_ip()
server_port_tcp = 9183
server_port_udp = 9184
system = engine.network.HSystem(server_ip, server_port_tcp, server_port_udp, ClientModel)

print(f'Server running on {server_ip}:{server_port_tcp}')

world = engine.world.World()
e = engine.Entity(pygame.Vector2(50, 50), pygame.Vector2(32, 32), None)
world.add_entity(e, True)

while True:
    now = time.time()
    dt = 0.05
    
    r = system.pump()
    
    for client in r.new_clients:
        print('Connected:', client.addr_tcp)
        
        client_entity = engine.Entity(pygame.Vector2(100, 50), pygame.Vector2(32, 32), None)
        world.add_entity(client_entity, False)
        
        client_model: ClientModel = client.model
        client_model.entity_uid = client_entity.uid
        
        # Send entities to this new client
        for entity in world.entities.values():
            system.send_event_tcp(engine.network.Event('ENTITY:CREATE', uid=entity.uid, attributes=entity.get_attributes_dict()), client.conn)
        
        system.send_event_tcp(engine.network.Event('ENTITY:SET_CLIENT_ENTITY', uid=client_entity.uid), client.conn)
    
    for client in r.disconnected_clients:
        print('Disconnected:', client.addr_tcp)
        client_model: ClientModel = client.model
        entity_uid = client_entity.uid
        world.remove_entity(entity_uid)
        
    for client, event in r.events_tcp:
        # print('tcp:', event)
        world.handle_network_event(event)
    
    for client, event in r.events_udp:
        # print('udp:', event, event.__dict__)
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
        ... # Server is running slow