import pygame
from scripts import network

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
        
        self.tank_img = pygame.image.load('./assets/tank.png')

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000  # Delta time in seconds

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    self.client.send_event_tcp(network.Event('SPACE'))
            
            r = self.client.pump()
            
            for event_tcp in r.events_tcp:
                print('tcp:', event_tcp)
            
            for event_udp in r.events_udp:
                print('udp:', event_udp)

            self.screen.fill((65, 65, 65))
            
            self.screen.blit(self.tank_img, (10, 10))
            
            self.display.blit(pygame.transform.scale(self.screen, self.display.size))
            pygame.display.flip()
        
        self.quit()

    def quit(self):
        pygame.quit()