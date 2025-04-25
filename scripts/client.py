import math
import time
from typing import Union
import pygame
from pygame.locals import *

from scripts.entity_registry import get_entity_registry
from . import engine, packets
from .tank import TankEntity

class ClientGame:
    def __init__(self):
        pygame.init()

        self.screen_size_ = pygame.Vector2(200, 140)
        
        self.screen = pygame.Surface(self.screen_size_)
        self.display = pygame.display.set_mode(self.screen_size_*3)
        
        self.font = pygame.font.SysFont('Consolas', 16)
        
        pygame.display.set_caption('Tiny Treads')
        
        self.clock = pygame.Clock()
        self.running = True
        
        self._packet_handler = packets.get_packet_handler()
        
        server_ip_addr = '192.168.15.12'
        server_port_tcp = 9183
        server_port_udp = 9184
        self.client = engine.network.HClient(server_ip_addr, server_port_tcp, server_port_udp, self._packet_handler)
        self.client.connect()
        
        self.client_entity: Union[TankEntity, None] = None
        
        self.world = engine.World(get_entity_registry())
        
        self.timer_rtt = engine.Timer(5, True)
        self.timer_world_update = engine.Timer(0.1)
        
        self.rtt_started_at = -1
        self.last_recorded_rtt = 0
        self.avg_rtt = -1
    
    def start_rtt(self):
        self.client.send_event_tcp(engine.network.Event(packets.PacketDefinitions.RTTPing, False))
        self.rtt_started_at = time.time()
    
    def receive_rtt(self):
        rtt = time.time() - self.rtt_started_at
        self.last_recorded_rtt = rtt
        self.rtt_started_at = -1
        if self.avg_rtt == -1:
            self.avg_rtt = rtt
        else:
            self.avg_rtt += (rtt - self.avg_rtt)*0.5
    
    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000  # Delta time in seconds

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            if self.timer_rtt.tick(dt):
                self.start_rtt()
            
            r = self.client.pump()
            
            for event in r.events_tcp:
                self.world.handle_network_event(event)
                
                if event.type == packets.PacketDefinitions.RTTPing and event.args[0]:
                    self.receive_rtt()
                
                if event.type == packets.PacketDefinitions.ClientSetLocalEntity:
                    entity_id, value = event.args
                    self.world.set_entity_local(entity_id, value)
                    self.client_entity = self.world.entities[entity_id]
            
            for event in r.events_udp:
                self.world.handle_network_event(event)

            keys_held = pygame.key.get_pressed()
            input_vector = engine.input_utils.get_input_vector(keys_held, K_s, K_w, K_a, K_d)
            
            if self.client_entity is not None:
                self.client_entity.process_inputs(dt, input_vector, keys_held)

            self.world.update(dt)
            
            if self.timer_world_update.tick(dt):
                send_events_tcp, send_events_udp = self.world.pump_network_events()
                for event in send_events_tcp: self.client.send_event_tcp(event)
                for event in send_events_udp: self.client.send_event_udp(event)

            self.screen.fill((150, 117, 72))
            self.world.draw(self.screen)
            self.display.blit(pygame.transform.scale(self.screen, self.display.size))
            
            debug_lines = [
                f'RTT latest ... avg {int(self.last_recorded_rtt*1000)}ms ... {int(self.avg_rtt*1000)}ms',
                (f'Latest Snapshot {self.world.snapshot_buffer[-1].time}' if len(self.world.snapshot_buffer) > 0 else 'No snapshots received')
            ]
            for i, line in enumerate(debug_lines):
                self.display.blit(self.font.render(line, True, (255, 255, 255)), (10, 10+i*16))
            
            pygame.display.flip()
        
        self.quit()

    def quit(self):
        pygame.quit()