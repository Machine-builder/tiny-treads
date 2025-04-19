import itertools
from typing import List, Tuple
import pygame


class Spritesheet():
    def __init__(self, image: pygame.Surface, tile_size: Tuple[int, int]):
        self.tile_size = tile_size
        self.image = image
        self.tile_count = (
            self.image.size[0] // tile_size[0],
            self.image.size[1] // tile_size[1]
        )
        self.frames = self._get_frames()
    
    def _get_tile(self, tile_xy: Tuple[int, int]) -> pygame.Surface:
        s = pygame.Surface(self.tile_size)
        s.fill((0, 0, 0))
        s.set_colorkey((0, 0, 0))
        s.blit(self.image, (-tile_xy[0]*self.tile_size[0], -tile_xy[1]*self.tile_size[1]))
        return s
    
    def _get_frames(self) -> List[pygame.Surface]:
        frames = []
        for y, x in itertools.product(range(self.tile_count[1]), range(self.tile_count[0])):
            frames.append(self._get_tile((x, y)))
        return frames

    def get_frame(self, rotation: int, frame_index: int) -> pygame.Surface:
        i = (frame_index%self.tile_count[0] + rotation*self.tile_count[0]) % len(self.frames)
        return self.frames[i]