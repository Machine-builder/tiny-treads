import time
from scripts import engine

class ClientModel():
    def __init__(self):
        ...

server_ip = engine.network.Utility.get_local_ip()
server_port_tcp = 9183
server_port_udp = 9184

packet_handler = engine.network.get_default_hybrid_packet_handler()

system = engine.network.HSystem(
    server_ip,
    server_port_tcp,
    server_port_udp,
    ClientModel,
    packet_handler
)

while True:
    r = system.pump()
    
    for c in r.new_clients:
        print('new client', c.addr_tcp)
    
    for c in r.disconnected_clients:
        print('disconnected client', c.addr_tcp)
        
    for c, e in r.events_tcp:
        print('tcp', e.type, e.args)
        if e.type == 4 and not e.args[0]: # rtt_ping request
            system.send_event_tcp(engine.network.Event(4, True), e.from_connection)
        
    for c, e in r.events_udp:
        print('tcp', e.type, e.args)
        
    time.sleep(0.01)