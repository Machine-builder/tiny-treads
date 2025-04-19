import pygame
from pygame.locals import *

from scripts import engine

pygame.init()

pygame.display.set_caption('Spritesheet Viewer')

screen = pygame.Surface((64, 64))
display = pygame.display.set_mode((512, 512))

spritesheet = engine.spritesheet.Spritesheet('./blender/sheets/tank_shoot.png', (32, 32))

clock = pygame.time.Clock()
ct = 0.0
running = True
while running:
    dt = clock.tick(61)/1000
    ct += dt
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    screen.fill((25, 25, 25))
    
    screen.blit(spritesheet.get_frame(1, int(ct*12)), (16, 16))
    
    display.blit(pygame.transform.scale(screen, (512, 512)))
    pygame.display.flip()

pygame.quit()