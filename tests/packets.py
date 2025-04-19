import struct

packets = [
    struct.pack('!Iff', 1, 100.5, 200.25), # Type 1, float x, float y
    struct.pack('!IIB', 2, 144, 200) # Type 2, entity id, health
]

for packet in packets:
    # Read the packet type
    packet_type = struct.unpack_from('!I', packet, 0)[0]

    # Dispatch to format logic
    if packet_type == 1:
        _, x, y = struct.unpack('!Iff', packet)
        print('Packet type 1:', x, y)

    if packet_type == 2:
        _, entity_id, health = struct.unpack('!IIB', packet)
        print('Packet type 2:', entity_id, health)