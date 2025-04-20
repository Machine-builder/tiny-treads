"""

This network.py file is responsible for handling
UDP + TCP hybrid client-server connections.

Latest update:
29-02-24

Current version:
v0.0.2

"""

import errno
import logging
import random
import select
import socket
import string
import struct
import time
from typing import Callable, Dict, Iterable, List, Tuple, Union
from dataclasses import dataclass

logger = logging.getLogger('network')
logger.setLevel(logging.WARN)

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class Utility:
    ...
class Constants:
    ...
class TCPBase:
    ...
class UDPBase:
    ...

class Constants:
    HEADER_SIZE = 16
    UDP_PACKET_SIZE = 8096
    RANDOM_ID_CHARS = string.ascii_letters+string.digits

class Utility():
    @staticmethod
    def get_header(data: bytes, headersize: int = 16):
        """generate header for byte data"""
        return str(len(data)).rjust(headersize, '0').encode()

    @staticmethod
    def get_local_ip() -> str:
        """get local ipv4 address"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ipv4 = s.getsockname()[0]
        s.close()
        return ipv4

    @staticmethod
    def random_identifier(length:int=8):
        """generate a random id with a given length"""
        return "".join(
            random.choice(Constants.RANDOM_ID_CHARS)\
            for _ in range(length))


class ConnException(Exception):
    def __init__(self, message, critical:bool=False):
        super().__init__(message)
        self.critical = critical


class Event:
    type: int
    args: Iterable
    from_connection: Union[None, socket.socket]
    
    def __init__(self, type: int, *args):
        self.type = type
        self.args = args
        self.from_connection = None
    
    def __repr__(self) -> str:
        return f'Event<{self.type}, {self.args}>'
        

'''

Complex packet handlers can have packer and unpacker
functions given as arguments instead of simple struct format str

packet_handler.add_handler(
    4,
    packer=lambda args: struct.pack('<?', *args),
    unpacker=lambda data: struct.unpack('<?', data)
)

'''

class PacketHandler:
    """Pack and unpack events"""
    
    def __init__(self):
        self.handlers: Dict[int, Union[
            Tuple[str, Callable, Callable], # Simple (format, pre/postprocess)
            Tuple[Callable, Callable]       # Custom (packer, unpacker)
        ]] = {}

    def register(self, id: int):
        def decorator(func):
            result = func()
            # Support both return types
            if isinstance(result[0], str) or result[0] is None:
                self.add_handler(id, *result)
            else:
                self.handlers[id] = result  # (packer, unpacker)
            return func
        return decorator

    def add_handler(
        self,
        id: int,
        format: str = None,
        preprocess: Callable[[Iterable], Iterable] = None,
        postprocess: Callable[[Iterable], Iterable] = None
    ) -> None:
        assert id not in self.handlers, f"Handler for id {id} already exists."
        self.handlers[id] = (format, preprocess, postprocess)

    def pack(self, event: Event) -> bytes:
        if event.type not in self.handlers:
            raise ValueError(f"No handler for event type {event.type}")
        handler = self.handlers[event.type]

        if isinstance(handler[0], str) or handler[0] is None:
            # Simple handler (format string or empty)
            format, preprocess, _ = handler
            args = event.args if preprocess is None else preprocess(*event.args)
            body = struct.pack(format, *args) if format else b''
        else:
            # Custom packer
            packer, _ = handler
            body = packer(*event.args)

        return struct.pack('<H', event.type) + body

    def unpack(self, data: bytes) -> Event:
        type_ = struct.unpack_from('<H', data, 0)[0]
        if type_ not in self.handlers:
            raise ValueError(f"No handler for event type {type_}")
        handler = self.handlers[type_]

        if isinstance(handler[0], str) or handler[0] is None:
            format, _, postprocess = handler
            unpacked_args = struct.unpack(format, data[2:]) if format else ()
            unpacked_args = unpacked_args if postprocess is None else postprocess(*unpacked_args)
        else:
            # Custom unpacker
            _, unpacker = handler
            unpacked_args = unpacker(data[2:]) # pass data after event type

        return Event(type_, *unpacked_args)

def get_default_hybrid_packet_handler() -> PacketHandler:
    packet_handler = PacketHandler()

    packet_handler.add_handler(1, '<H')  # init_tcp   (client_id)
    packet_handler.add_handler(2, '<H')  # init_udp   (client_id)
    packet_handler.add_handler(3)        # init_final ()
    packet_handler.add_handler(4, '<?')  # rtt_ping   (return?)
    
    return packet_handler


# region TCP

class TCPBase(object):
    """base class for both the server & client ebsocket classes"""

    def __init__(self, connection: socket.socket, packet_handler: PacketHandler) -> None:
        self.connection = connection
        self.packet_handler = packet_handler

    def is_valid_socket(self, socket_) -> socket.socket:
        """if socket_ is a socket.socket instance the function returns it,
        otherwise returns the class instances' connection attribute"""
        if not isinstance(socket_, socket.socket):
            return self.connection
        return socket_

    def send_bytes_to(self, data: bytes, connection: socket.socket):
        """send byte data to specific connection"""
        connection.send(data)

    def send_bytes(self, data: bytes):
        """send byte data"""
        self.send_bytes_to(data, self.connection)

    def recv_bytes_from(self, buffersize: int = 34, connection: socket.socket = ...):
        """receive a ray payload of the provided buffer size from a specific connection"""
        return connection.recv(buffersize)

    def recv_bytes(self, buffersize: int = 512):
        """receive a bytes payload of the provided buffer size"""
        return self.recv_bytes_from(buffersize, self.connection)

    def send_with_header(self, data: bytes, send_socket: socket.socket = None):
        """send data with a header"""
        use_socket = self.is_valid_socket(send_socket)
        bytes = Utility.get_header(data, Constants.HEADER_SIZE)+data
        use_socket.send(bytes)

    def recv_with_header(self, recv_socket: socket.socket = None):
        """receive data with a header"""
        use_socket = self.is_valid_socket(recv_socket)
        header_recv = use_socket.recv(Constants.HEADER_SIZE)
        if not header_recv:
            raise ConnException(
                "header received was empty in recv_with_header() call",
                critical=True)
        byte_count = int(header_recv.decode())
        data_recv = use_socket.recv(byte_count)
        return data_recv

    def send_event(self, event: Event = None, send_socket: socket.socket = None):
        """send an event using send_socket"""
        use_socket = self.is_valid_socket(send_socket)
        bytes = self.packet_handler.pack(event)
        return self.send_with_header(bytes, use_socket)

    def recv_event(self, recv_socket: socket.socket = None) -> Event:
        """attempt to receive and return an event object, if the object
        received is not an event object, the function returns None"""
        use_socket = self.is_valid_socket(recv_socket)
        bytes = self.recv_with_header(use_socket)
        event = self.packet_handler.unpack(bytes)
        return event


class TCPServer(TCPBase):
    """a server class used to handle multiple socket connections"""

    def __init__(self, bind_to: Union[tuple, int], packet_handler: PacketHandler):
        if isinstance(bind_to, int): bind_to = (Utility.get_local_ip(), bind_to)
        self.address = bind_to
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.bind(self.address)
        super().__init__(connection, packet_handler)

    def listen(self, backlog: int = 1):
        """listen for incoming connections with a backlog"""
        self.connection.listen(backlog)

    def accept_connection(self) -> tuple:
        """accept next incoming connection and returns the connection and address"""
        connection, address = self.connection.accept()
        return connection, address


class TCPClient(TCPBase):
    """a client class used to handle a single connection"""

    def __init__(self, packet_handler: PacketHandler) -> None:
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        super().__init__(self.connection, packet_handler)

    def connect_to(self, address: tuple):
        """try connect to an address, the connected attribute is
        a boolean which will be set to True if the connection is a success"""
        try:
            self.connection.connect(address)
            self.connected = True
            self.connection.setblocking(False)
        except:
            self.connected = False

    def pump(self) -> Tuple[List[Event], bool]:
        """get a list of all new events from the server

        also returns a boolean representing whether the connection
        is still active"""
        new_events = []

        if not self.connected:
            return new_events, False

        try:
            while True:
                new_event = self.recv_event()
                if new_event is None:
                    return new_events, False
                new_events.append(new_event)

        except ConnectionResetError as e:
            logger.debug(f"connection reset error in get_new_events() {e}")
            return new_events, False

        except IOError as e:
            logger.debug(f"IOError in get_new_events() {e}")
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                # reading error
                logger.debug(f"reading error in get_new_events() {e}")
        
        except ConnException as e:
            logger.debug(f"ConnException in get_new_events() {e}")
            if e.critical:
                return new_events, False

        except Exception as e:
            # general error
            logger.debug(f"Other exception in get_new_events() {e}")

        return new_events, True


class TCPSystem(object):
    """a whole server-client system network"""

    def __init__(self, server: TCPServer) -> None:
        self.server = server
        self.server.listen(5)
        self.connections_list = [self.server.connection]
        self.clients = {}
        self.timeout = 0.0
        self.packet_handler = server.packet_handler

    def pump(self) -> Tuple[List[Tuple], List[Event], List[Tuple]]:
        """run the main system

        run this function within a loop for basic functionality

        returns:
         - new_clients:list
         - new_events:list
         - disconnected_clients:list"""
        
        conn_list = self.connections_list
        read_connections, _, exception_connections = select.select(
            conn_list, [], conn_list, self.timeout)

        new_clients = []
        new_events = []
        disconnected_clients = []

        for notified_connection in read_connections:
            if notified_connection == self.server.connection:
                client_connection, client_address = self.server.accept_connection()
                self.connections_list.append(client_connection)
                self.clients[client_connection] = client_address
                new_clients.append((client_connection, client_address))

            else:
                try:
                    event = self.server.recv_event(notified_connection)
                except ConnectionResetError as e:
                    event = None
                    exception_connections.append(notified_connection)
                except ValueError as e:
                    event = None
                    exception_connections.append(notified_connection)
                except ConnException as e:
                    event = None
                    exception_connections.append(notified_connection)
                if event is not None:
                    event.from_connection = notified_connection
                    new_events.append(event)

        for notified_connection in exception_connections:
            disconnected_clients.append(
                (notified_connection, self.clients[notified_connection]))
            self.remove_client(notified_connection)

        return new_clients, new_events, disconnected_clients

    def remove_client(self, client_connection):
        """remove a client from the server"""
        self.connections_list.remove(client_connection)
        del self.clients[client_connection]

    def send_bytes_to(self, connection: socket.socket, data: bytes):
        """send byte data to a client"""
        connection.send(data)

    def send_event_to(self, connection: socket.socket, event: Event):
        """send an event to a client"""
        try:
            data = self.packet_handler.pack(event)
            header = Utility.get_header(data)
            self.send_bytes_to(connection, header+data)
        except Exception as e:
            raise e
            return False

    def send_event_to_clients(self, event: Event):
        """send an event to all clients"""
        try:
            data = self.packet_handler.pack(event)
            header = Utility.get_header(data)
            full_bytes = header+data
            for connection in self.clients:
                self.send_bytes_to(connection, full_bytes)
        except Exception as e:
            return False


#region UDP

class UDPBase(socket.socket):
    """Basic UDP socket wrapper.
    """
    def __init__(self, packet_handler: PacketHandler):
        super().__init__(socket.AF_INET, socket.SOCK_DGRAM)
        self.settimeout(0)
        self.setblocking(False)
        self.packet_handler = packet_handler
    
    def _send_bytes(self, packet: bytes, addr: tuple[str,int]):
        self.sendto(packet, addr)
    
    def _recv_bytes(self, bufsize: int=...) -> tuple[Union[bytes, None], Union[tuple[str,int], None]]:
        if bufsize == ...:
            bufsize = Constants.UDP_PACKET_SIZE
        try: return self.recvfrom(bufsize)
        except BlockingIOError as e: return None, None
    
    def send_event(self, event: Event, addr: tuple[str,int]):
        """Send an event to the specified UDP address.

        Args:
            event (Event): Event to send.
            addr (tuple[str,int]): UDP address to send to.
        """
        bytes = self.packet_handler.pack(event)
        self._send_bytes(bytes, addr)
    
    def recv_event(self) -> tuple[Event|None, tuple[str,int]|None]:
        """Try recieve an event. This function may
        return None.

        Returns:
            tuple[Event|None, tuple[str,int]|None]: (Event, address) pair or None.
        """
        bytes, addr = self._recv_bytes()
        if bytes is None:
            return None, None
        event = self.packet_handler.unpack(bytes)
        return event, addr
    
    def pump(self) -> list[tuple[Event, tuple[str,int]]]:
        """Retrieve a list of new events and the address(es)
        said events were sent by.

        Returns:
            list[tuple[Event, tuple[str,int]]]: List of (Event, address) pairs.
        """
        events = []
        while True:
            event, addr = self.recv_event()
            if event is None: break
            events.append((event, addr))
        return events

class UDPServer(UDPBase):
    """UDP server, which is essentially a socket wrapper.
    Allows for sending and recieving events in a streamlined
    manner."""
    def __init__(self, addr: tuple[str,int], packet_handler: PacketHandler):
        super().__init__(packet_handler)
        self.addr = addr
        self.bind(self.addr)
    
class UDPClient(UDPBase):
    """UDP client, which is essentially a socket wrapper.
    Allows for sending and recieving events in a streamlined
    manner."""
    def __init__(self, server_addr: tuple[str,int], packet_handler: PacketHandler):
        super().__init__(packet_handler)
        self.server_addr = server_addr
        self.packet_handler = packet_handler
    
    def set_server_addr(self, server_addr: tuple[str,int]):
        self.server_addr = server_addr
    
    def _send_bytes(self, packet: bytes):
        super()._send_bytes(packet, self.server_addr)
    
    def send_event(self, event: Event):
        """Send an event to the server.

        Args:
            event (Event): Event to send.
        """
        bytes = self.packet_handler.pack(event)
        self._send_bytes(bytes)

#region Hybrid

class HEvents:
    INIT_TCP = 1
    INIT_UDP = 2
    INIT_FINAL = 3

class HSystemClient():
    def __init__(
            self,
            conn:socket.socket,
            cid:str,
            addr_tcp:tuple[str, int],
            client_model):
        """The internal server-client client
        representation.

        Args:
            conn (socket.socket): Socket connection.
            cid (str): Randomly assigned id.
            addr_tcp (tuple[str, int]): TCP address.
            client_model (_type_): _description_
        """
        self.conn = conn
        self.cid = cid
        self.addr_tcp = addr_tcp
        self.addr_udp:tuple[str, int] = None
        self.model = client_model()

@dataclass
class HClientPumpResult:
    events_tcp:list[Event]
    events_udp:list[Event]
    connected:bool
    connection_status:int=0

@dataclass
class HSystemPumpResult:
    new_clients:list[HSystemClient]
    disconnected_clients:list[HSystemClient]
    events_tcp:list[Tuple[HSystemClient, Event]]
    events_udp:list[Tuple[HSystemClient, Event]]

class HSystem():
    def __init__(
            self,
            ip:str,
            port_tcp:int,
            port_udp:int,
            client_model,
            packet_handler: PacketHandler):
        self.addr_tcp = (ip, port_tcp)
        self.addr_udp = (ip, port_udp)
        self.client_model = client_model
        self.server_tcp = TCPServer(self.addr_tcp, packet_handler)
        self.system_tcp = TCPSystem(self.server_tcp)
        self.server_udp = UDPServer(self.addr_udp, packet_handler)
        self.clients: Dict[int, HSystemClient] = {}
        self.cid_by_udp: Dict[Tuple[str, int], int] = {}
        self.cid_by_conn: Dict[socket.socket, int] = {}
        self.packet_handler = packet_handler
    
    def send_event_tcp(self, event:Event, conn:socket.socket=None):
        """Send an event to a client via TCP

        Args:
            event (Event): The event to send
            conn (socket.socket, optional): Client connection.
                If not provided the event will be sent to all clients.
        """
        if conn is None:
            self.system_tcp.send_event_to_clients(event)
        else:
            self.system_tcp.send_event_to(conn, event)
    
    def send_event_udp(self, event: Event, addr: tuple[str, int]=None):
        if addr is None:
            # send to all
            for addr in self.cid_by_udp.keys():
                self.server_udp.send_event(event, addr)
        else:
            self.server_udp.send_event(event, addr)
    
    def get_client_model(self, cid: int) -> Union[any, None]:
        """Gets a client model from a provided cid.

        Args:
            cid (int): The client's id.

        Returns:
            any | None: The client model, or None.
        """
        client = self.clients.get(cid)
        if client is None: return None
        return client.model

    def pump(self):
        result = HSystemPumpResult([], [], [], [])
        (n_clients_tcp,
         events_tcp,
         d_clients_tcp) = self.system_tcp.pump()

        for conn, addr in n_clients_tcp:
            # when a client joins the system needs to
            # initialize the hybrid handshake process.
            # this is simply done by sending a TCP event,
            # and preparing the rest of the data for the client
            # to complete the handshake.
            cid = -1
            while cid == -1 or cid in self.clients:
                cid = random.randint(0, 65535)
            client = HSystemClient(
                conn=conn,
                cid=cid,
                addr_tcp=addr,
                client_model=self.client_model)
            self.clients[cid] = client
            self.cid_by_conn[conn] = cid
            self.send_event_tcp(Event(HEvents.INIT_TCP, cid), conn)
            print(f"HS:INIT Client handshake begun... {client.addr_tcp} -> Assigned CID: {cid}")

        for conn, addr in d_clients_tcp:
            # remove this client from the system.
            # in order to do that we need to remove this client's
            # class instance from the dicts, and other pointers in
            # the dicts, like cid_by_conn, cid_by_udp, etc.
            cid = self.cid_by_conn[conn]
            client = self.clients[cid]
            if conn in self.cid_by_conn:
                self.cid_by_conn.pop(conn)
            if client.addr_udp in self.cid_by_udp:
                self.cid_by_udp.pop(client.addr_udp)
            if cid in self.clients:
                self.clients.pop(cid)
            result.disconnected_clients.append(client)

        for event in events_tcp:
            conn = event.from_connection
            cid = self.cid_by_conn.get(conn, None)
            client = self.clients.get(cid, None)
            if client is None: continue
            result.events_tcp.append((client, event),)

        udp_packets = self.server_udp.pump()

        for event, addr in udp_packets:
            cid = self.cid_by_udp.get(addr, None)
            client: HSystemClient = self.clients.get(cid, None)
            if event.type == HEvents.INIT_UDP:
                self.cid_by_udp[addr] = event.args[0]
                client = self.clients[event.args[0]]
                client.addr_udp = addr
                # client is now ready
                self.send_event_tcp(Event(HEvents.INIT_FINAL), client.conn)
                result.new_clients.append(client)
            else:
                if client is None:
                    continue
                result.events_udp.append((client, event))
        
        return result

class HClient():
    def __init__(
            self,
            server_ip:str,
            server_port_tcp:int,
            server_port_udp:int,
            packet_handler: PacketHandler):
        self.ready = False
        self.connection_state = "A"
        self.server_addr_tcp = (server_ip, server_port_tcp)
        self.server_addr_udp = (server_ip, server_port_udp)
        self.client_tcp = TCPClient(packet_handler)
        self.client_udp = UDPClient(self.server_addr_udp, packet_handler)
        self.cid:str = None
        self.packet_handler = packet_handler
    
    def set_server_ip(
            self,
            server_ip:str,
            server_port_tcp:int,
            server_port_udp:int):
        self.server_addr_tcp = (server_ip, server_port_tcp)
        self.server_addr_udp = (server_ip, server_port_udp)
        self.client_udp.set_server_addr(self.server_addr_udp)
    
    def send_event_tcp(self, event:Event):
        self.client_tcp.send_event(event)
    
    def send_event_udp(self, event:Event):
        self.client_udp.send_event(event)
    
    def connect(self):
        self._retry_time = time.time()+2.5
        self._retries = 5
        self.client_tcp.connect_to(self.server_addr_tcp)
    
    def pump(self) -> HClientPumpResult:
        events_tcp, connected = self.client_tcp.pump()
        result = HClientPumpResult(
            events_tcp,
            [],
            connected,
            connection_status=0)
        # the "connecting" pump loop
        if not self.ready:
            result.connected = False
            for event in events_tcp:
                if event.type == HEvents.INIT_TCP:
                    self.cid = event.args[0]
                    # send a UDP packet
                    # to the server with the client cid
                    # so that the server can create a reference
                    # to the UDP client address
                    self.client_udp.send_event(Event(HEvents.INIT_UDP, self.cid))
                    self.connection_state = "B"
                elif event.type == HEvents.INIT_FINAL:
                    self.connection_state = "C"
                    self.ready = True
                    result.connection_status = 1
                    return result
            # failsafe incase the UDP packet got lost
            # allows for re-sending the init part B
            # with a timeout
            if self.connection_state == "B":
                self._current_time = time.time()
                if self._current_time > self._retry_time:
                    self._retries -= 1
                    if self._retries == 0:
                        result.connection_status = -1
                        self.connection_state = "F"
                        return result
                    print(f"HS:INIT:B Retrying ({self._retries} left)")
                    self._retry_time = self._current_time+1
                    self.client_udp.send_event(Event(HEvents.INIT_UDP, self.cid))
            elif self.connection_state == "F":
                result.connection_status = -1

        else:
            # the proper pump loop
            events_udp = self.client_udp.pump()
            for event, addr in events_udp:
                result.events_udp.append(event)
            
            if not connected:
                result.connection_status = -1

        return result