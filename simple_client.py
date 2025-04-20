import time

import pygame
from scripts import engine, packets

server_ip = engine.network.Utility.get_local_ip()
server_port_tcp = 9183
server_port_udp = 9184

packet_handler = packets.get_packet_handler()

client = engine.network.HClient(
    server_ip,
    server_port_tcp,
    server_port_udp,
    packet_handler
)

client.connect()

ping_start = -1

connection_status = 0
while connection_status != -1:
    r = client.pump()
    
    connection_status = r.connection_status
    
    for e in r.events_tcp:
        print('tcp', e.type, e.args)
        
        if e.type == 3: # tcp_final
            print('Hybrid cnnection established')
            ping_start = time.time()
            client.send_event_tcp(engine.network.Event(4, False))
        
        if e.type == 4 and e.args[0]: # rtt_ping return
            now = time.time()
            rtt = now - ping_start
            print(f'Connection RTT: {int(rtt*1000)}ms')
            
            client.send_event_tcp(engine.network.Event(301, 9281, "tank"))
            client.send_event_tcp(engine.network.Event(304, 9281, pygame.Vector2(100.5, 200.25), pygame.Vector2(99.4, 25.2), 45.0, 0.0))
    
    for e in r.events_udp:
        print('tcp', e.type, e.args)
        
    time.sleep(0.01)

print('Connection to the server has been lost')