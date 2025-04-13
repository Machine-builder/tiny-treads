from scripts import network

class ClientModel():
    def __init__(self, *args, **kwargs):
        print('Client model init')
        print('args:', args)
        print('kwargs:', kwargs)

server_ip = network.Utility.get_local_ip()
server_port_tcp = 9183
server_port_udp = 9184
system = network.HSystem(server_ip, server_port_tcp, server_port_udp, ClientModel)

print(f'Server running on {server_ip}:{server_port_tcp}')

while True:
    r = system.pump()
    
    for client in r.new_clients:
        print('Connected:', client.addr_tcp)
    
    for client in r.disconnected_clients:
        print('Disconnected:', client.addr_tcp)
        
    for client, event in r.events_tcp:
        print('tcp:', event)
        system.send_event_tcp(network.Event('SPACERET'), client.conn)
    
    for event in r.events_udp:
        print('udp:', event)