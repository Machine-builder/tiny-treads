from typing import Union
import pygame
from pygame.locals import *
from . import network
from .entity import Entity
from scripts import engine

class GameState:
    MainMenu = 0

class ClientGame:
    screen_size_: pygame.Vector2
    screen: pygame.Surface
    display: pygame.Surface
    clock: pygame.time.Clock
    state: GameState
    
    def __init__(self):
        pygame.init()

        self.screen_size_ = pygame.Vector2(450, 300)
        
        self.screen = pygame.Surface(self.screen_size_)
        self.display = pygame.display.set_mode(self.screen_size_*2)
        
        pygame.display.set_caption('Tiny Treads')
        
        self.clock = pygame.Clock()
        self.running = True
        self.state = GameState.MainMenu
        
        server_ip_addr = '192.168.15.10'
        server_port_tcp = 9183
        server_port_udp = 9184
        self.client = network.HClient(server_ip_addr, server_port_tcp, server_port_udp)
        self.client.connect()
        
        self.world = engine.World()
        self.client_entity: Union[Entity, None] = None

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000  # Delta time in seconds

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    self.client.send_event_tcp(network.Event('SPACE'))
            
            r = self.client.pump()
            
            for event in r.events_tcp:
                # print('tcp:', event)
                self.world.handle_network_event(event)
                
                if event.event == 'ENTITY:SET_CLIENT_ENTITY':
                    e = self.world.entities.get(event.uid)
                    assert e is not None, f'No entity with uid "{event.uid}" found when processing "ENTITY:SET_CLIENT_ENTITY" event'
                    self.world.set_entity_network_authority(e, True)
                    self.client_entity = e
            
            for event in r.events_udp:
                # print('udp:', event)
                self.world.handle_network_event(event)

            keys_held = pygame.key.get_pressed()
            
            if self.client_entity is not None:
                input_vector = pygame.Vector2(
                    -1*keys_held[K_a] + keys_held[K_d],
                    -1*keys_held[K_w] + keys_held[K_s]
                )
                if input_vector.length() > 0:
                    input_vector.normalize_ip()
                self.client_entity.velocity.x = input_vector.x*50
                self.client_entity.velocity.y = input_vector.y*50

            self.world.update(dt)
            
            world_events = self.world.pump_network_events(as_client=True)
            for event in world_events[0]:
                self.client.send_event_tcp(event)
            for event in world_events[1]:
                self.client.send_event_udp(event)

            self.screen.fill((65, 65, 65))
            self.world.draw(self.screen)
            self.display.blit(pygame.transform.scale(self.screen, self.display.size))
            pygame.display.flip()
        
        self.quit()

    def quit(self):
        pygame.quit()