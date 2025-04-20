import pygame


def get_input_vector(keys_held: pygame.key.ScancodeWrapper, up: int, down: int, left: int, right: int):
    input_vector = pygame.Vector2(
        keys_held[right] - keys_held[left],
        keys_held[down] - keys_held[up],
    )
    if input_vector.length_squared() > 0:
        input_vector.normalize_ip()
    
    return input_vector