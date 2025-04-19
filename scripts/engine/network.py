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
import pickle
import random
import select
import socket
import string
import time
from typing import List, Tuple, Union
from dataclasses import dataclass

class Utility:
    ...
class Constants:
    ...
class TCPBase:
    ...
class UDPBase:
    ...
class Event:
    ...

class Constants:
    HEADER_SIZE = 16
    UDP_PACKET_SIZE = 8096
    RANDOM_ID_CHARS = string.ascii_letters+string.digits

class Utility():
    @staticmethod
    def get_header(data: bytes, headersize: int = 16):
        """generates a header for byte data"""
        return str(len(data)).rjust(headersize, '0').encode()

    @staticmethod
    def get_local_ip() -> str:
        """gets local ipv4 address"""
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


"""
██████  ██████  ██████
  ██    ██      ██  ██
  ██    ██      ██████
  ██    ██      ██    
  ██    ██████  ██    
"""

class TCPBase(object):
    """base class for both the server & client ebsocket classes"""

    def __init__(self, connection: socket.socket) -> None:
        self.connection = connection

    def is_valid_socket(self, socket_) -> socket.socket:
        """if socket_ is a socket.socket instance the function returns it,
        otherwise returns the class instances' connection attribute"""
        if not isinstance(socket_, socket.socket):
            return self.connection
        return socket_

    def send_raw_to(self, data: bytes, connection: socket.socket):
        """sends raw byte data to specific connection"""
        connection.send(data)

    def send_raw(self, data: bytes):
        """sends raw byte data"""
        self.send_raw_to(data, self.connection)

    def recv_raw_from(self, buffersize: int = 34, connection: socket.socket = ...):
        """receives a ray payload of the provided buffer size from a specific connection"""
        return connection.recv(buffersize)

    def recv_raw(self, buffersize: int = 512):
        """receives a raw payload of the provided buffer size"""
        return self.recv_raw_from(buffersize, self.connection)

    def send_with_header(self, data: bytes, send_socket: socket.socket = None):
        """sends data with a header"""
        use_socket = self.is_valid_socket(send_socket)
        byte_data = Utility.get_header(data, Constants.HEADER_SIZE)+data
        use_socket.send(byte_data)

    def recv_with_header(self, recv_socket: socket.socket = None):
        """receives data with a header"""
        use_socket = self.is_valid_socket(recv_socket)
        # TODO can cause issue,
        # catch ConnectionAbortedError
        header_recv = use_socket.recv(Constants.HEADER_SIZE)
        if not header_recv:
            raise ConnException(
                "header received was empty in recv_with_header() call",
                critical=True)
        total_bytes = int(header_recv.decode())
        data_recv = use_socket.recv(total_bytes)
        return data_recv

    def send_event(self, event: Event = None, send_socket: socket.socket = None):
        """sends an event using send_socket"""
        use_socket = self.is_valid_socket(send_socket)
        raw_bytes = event.as_bytes()
        return self.send_with_header(raw_bytes, use_socket)

    def recv_event(self, recv_socket: socket.socket = None):
        """attempts to receive and return an event object, if the object
        received is not an event object, the function returns None"""
        use_socket = self.is_valid_socket(recv_socket)
        raw_bytes = self.recv_with_header(use_socket)
        event = Event.from_bytes(raw_bytes)
        if isinstance(event, Event):
            return event
        return None


class TCPServer(TCPBase):
    """a server class used to handle multiple socket connections"""

    def __init__(self, bind_to: Union[tuple, int]):
        if isinstance(bind_to, int):
            bind_to = (Utility.get_local_ip(), bind_to)
        self.address = bind_to
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.bind(self.address)

    def listen(self, backlog: int = 1):
        """listens for incoming connections with a backlog"""
        self.connection.listen(backlog)

    def accept_connection(self) -> tuple:
        """accepts next incoming connection and returns the connection and address"""
        connection, address = self.connection.accept()
        return connection, address


class TCPClient(TCPBase):
    """a client class used to handle a single connection"""

    def __init__(self) -> None:
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        super().__init__(self.connection)

    def connect_to(self, address: tuple):
        """try connect to an address, the connected attribute is
        a boolean which will be set to True if the connection is a success"""
        try:
            self.connection.connect(address)
            self.connected = True
            self.connection.setblocking(False)
        except:
            self.connected = False

    def pump(self):
        """gets a list of all new events from the server

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
            logging.debug(f"connection reset error in get_new_events() -> {e}")
            return new_events, False

        except IOError as e:
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                # reading error
                logging.debug(f"reading error in get_new_events() -> {e}")
        
        except ConnException as e:
            if e.critical:
                return new_events, False

        except Exception as e:
            # general error
            logging.debug(f"general error in get_new_events() -> {e}")

        return new_events, True


class TCPSystem(object):
    """a whole server-client system network"""

    def __init__(self, server: TCPServer) -> None:
        self.server = server
        self.server.listen(5)
        self.connections_list = [self.server.connection]
        self.clients = {}
        self.timeout = 0.0

    def pump(self) -> Tuple[List[Tuple], List[Event], List[Tuple]]:
        """runs the main system

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
        """removes a client from the server"""
        self.connections_list.remove(client_connection)
        del self.clients[client_connection]

    def send_raw_to(self, connection: socket.socket, data: bytes):
        """sends byte data to a client"""
        connection.send(data)

    def send_event_to(self, connection: socket.socket, event: Event):
        """sends an event to a client"""
        try:
            data = event.as_bytes()
            header = Utility.get_header(data)
            self.send_raw_to(connection, header+data)
        except Exception as e:
            return False

    def send_event_to_clients(self, event: Event):
        """sends an event to all clients"""
        try:
            data = event.as_bytes()
            header = Utility.get_header(data)
            full_bytes = header+data
            for connection in self.clients:
                self.send_raw_to(connection, full_bytes)
        except Exception as e:
            return False


"""
██  ██  ████    ██████
██  ██  ██  ██  ██  ██
██  ██  ██  ██  ██████
██  ██  ██  ██  ██    
██████  ████    ██    
"""

class UDPBase(socket.socket):
    """Basic UDP socket wrapper.
    """
    def __init__(self):
        super().__init__(socket.AF_INET, socket.SOCK_DGRAM)
        self.settimeout(0)
        self.setblocking(False)
    
    def _send_packet(self, packet:bytes, addr:tuple[str,int]):
        self.sendto(packet, addr)
    
    def _recv_packet(self, bufsize:int=...) -> tuple[bytes|None, tuple[str,int]|None]:
        if bufsize == ...:
            bufsize = Constants.UDP_PACKET_SIZE
        try: return self.recvfrom(bufsize)
        except BlockingIOError as e: return None, None
    
    def send_event(self, event:Event, addr:tuple[str,int]):
        """Send an event to the specified UDP address.

        Args:
            event (Event): Event to send.
            addr (tuple[str,int]): UDP address to send to.
        """
        packet:bytes = event.as_bytes()
        self._send_packet(packet, addr)
    
    def recv_event(self) -> tuple[Event|None, tuple[str,int]|None]:
        """Try recieve an event. This function may
        return None.

        Returns:
            tuple[Event|None, tuple[str,int]|None]: (Event, address) pair or None.
        """
        packet, addr = self._recv_packet()
        if packet is None:
            return None, None
        event = Event.from_bytes(packet)
        return event, addr
    
    def pump(self) -> list[tuple[Event, tuple[str,int]]]:
        """Retrieves a list of new events and the address(es)
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
    def __init__(self, addr:tuple[str,int]):
        super().__init__()
        self.addr = addr
        self.bind(self.addr)
    
class UDPClient(UDPBase):
    """UDP client, which is essentially a socket wrapper.
    Allows for sending and recieving events in a streamlined
    manner."""
    def __init__(self, server_addr:tuple[str,int]):
        super().__init__()
        self.server_addr = server_addr
    
    def set_server_addr(self, server_addr:tuple[str,int]):
        self.server_addr = server_addr
    
    def _send_packet(self, packet:bytes):
        super()._send_packet(packet, self.server_addr)
    
    def send_event(self, event:Event):
        """Send an event to the server.

        Args:
            event (Event): Event to send.
        """
        packet:bytes = event.as_bytes()
        self._send_packet(packet)

"""
██  ██  ██  ██  ████    ██████  ██  ████  
██  ██  ██  ██  ██  ██  ██  ██  ██  ██  ██
██████  ██████  ██████  ████    ██  ██  ██
██  ██    ██    ██  ██  ██  ██  ██  ██  ██
██  ██    ██    ████    ██  ██  ██  ████  
"""

class HEvents:
    INIT_A = "hs_init_tcp"
    INIT_B = "hs_init_udp"
    INIT_C = "hs_init"

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
            client_model):
        self.addr_tcp = (ip, port_tcp)
        self.addr_udp = (ip, port_udp)
        self.client_model = client_model
        self.server_tcp = TCPServer(self.addr_tcp)
        self.system_tcp = TCPSystem(self.server_tcp)
        self.server_udp = UDPServer(self.addr_udp)
        self.clients = {}
        self.cid_by_udp = {}
        self.cid_by_conn = {}
    
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
    
    def send_event_udp(self, event:Event, addr:tuple[str, int]=None):
        if addr is None:
            # send to all
            for addr in self.cid_by_udp.keys():
                self.server_udp.send_event(event, addr)
        else:
            self.server_udp.send_event(event, addr)
    
    def get_client_model(self, cid:str) -> Union[any, None]:
        """Gets a client model from a provided cid.

        Args:
            cid (str): The client's id.

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
            cid = Utility.random_identifier()
            client = HSystemClient(
                conn=conn,
                cid=cid,
                addr_tcp=addr,
                client_model=self.client_model)
            self.clients[cid] = client
            self.cid_by_conn[conn] = cid
            self.send_event_tcp(Event(HEvents.INIT_A, cid=cid), conn)
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
            client:HSystemClient = self.clients.get(cid, None)
            if event.event == HEvents.INIT_B:
                self.cid_by_udp[addr] = event.cid
                client = self.clients[event.cid]
                client.addr_udp = addr
                # client is now ready
                self.send_event_tcp(Event(HEvents.INIT_C), client.conn)
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
            server_port_udp:int):
        self.ready = False
        self.init_step = "A"
        self.server_addr_tcp = (server_ip, server_port_tcp)
        self.server_addr_udp = (server_ip, server_port_udp)
        self.client_tcp = TCPClient()
        self.client_udp = UDPClient(self.server_addr_udp)
        self.cid:str = None
    
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
            True, connection_status=0)
        # the "connecting" pump loop
        if not self.ready:
            result.connected = False
            for event in events_tcp:
                if event.event == HEvents.INIT_A:
                    self.cid = event.cid
                    # send a UDP packet
                    # to the server with the client cid
                    # so that the server can create a reference
                    # to the UDP client address
                    self.client_udp.send_event(Event(
                        HEvents.INIT_B, cid=self.cid))
                    self.init_step = "B"
                elif event.event == HEvents.INIT_C:
                    self.init_step = "C"
                    self.ready = True
                    result.connection_status = 1
                    return result
            # failsafe incase the UDP packet got lost
            # allows for re-sending the init part B
            # with a timeout
            if self.init_step == "B":
                self._current_time = time.time()
                if self._current_time > self._retry_time:
                    self._retries -= 1
                    if self._retries == 0:
                        result.connection_status = -1
                        self.init_step = "F"
                        return result
                    print(f"HS:INIT:B Retrying ({self._retries} left)")
                    self._retry_time = self._current_time+1
                    self.client_udp.send_event(Event(
                        HEvents.INIT_B, cid=self.cid))
            elif self.init_step == "F":
                result.connection_status = -1

        else:
            # the proper pump loop
            events_udp = self.client_udp.pump()
            for event, addr in events_udp:
                result.events_udp.append(event)

        return result

class Event(object):
    """an event
    stores the event type and event data"""

    def __init__(self, event_data, **kwargs) -> None:
        self.from_connection = False
        if isinstance(event_data, str):
            self.__dict__ = {'event': event_data}
            self.__dict__.update(kwargs)
        elif isinstance(event_data, Event):
            self.__dict__ = event_data.data
            self.from_connection = event_data.from_connection
        else:
            self.__dict__ = event_data
        self.event = self.__dict__.get('event', None)

    def get_attribute(self, attribute):
        """gets an attribute of the event's data, if the attribute
        does not exist, returns None"""
        return self.__dict__.get(attribute, None)

    def compare_type(self, event_type:str) -> bool:
        """compare the event's type with the provided argument"""
        return self.event == event_type

    def __repr__(self):
        return f'Event<{self.event}>'
    
    def print_attributes(self):
        """prints all event data attributes"""
        attribute_names = [k for k in self.__dict__]
        print(self)
        print('~ attributes ~')
        if len(attribute_names) > 0:
            longest = max([len(i) for i in attribute_names])
            for attribute_name in attribute_names:
                print(f' * {attribute_name.ljust(longest)}  :  {self.__dict__[attribute_name]}')
        else:
            print("event has no attributes")

    def as_bytes(self) -> bytes:
        """compile the event into bytes"""
        json_data = {
            'event': self.event,
            '__dict__': self.__dict__}
        return pickle.dumps(json_data)
    
    @staticmethod
    def from_bytes(byte_data:bytes) -> Event:
        """decompile an event from bytes"""
        try:
            unpickled: dict = pickle.loads(byte_data)
            event = Event(
                unpickled.get('event',None),
                **unpickled.get('__dict__',{}))
            return event
        except:
            return None