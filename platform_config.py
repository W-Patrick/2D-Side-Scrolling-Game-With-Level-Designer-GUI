import pygame
import json
from GLOBALS import BLACK

class PlatformTypeException(Exception):
    pass


# class to represent a platform
class Platform(pygame.sprite.Sprite):
    with open("platforms.json") as filename:
        data = json.load(filename)

    def __init__(self, groups, rect, ptype=None, width=None, height=None, color=None):
        pygame.sprite.Sprite.__init__(self, groups.platforms, groups.scrolling_units)

        if ptype is not None:
            try:
                attributes = self.data["types"][ptype]
                if width is None:
                    width = attributes["width"]

                if height is None:
                    height = attributes["height"]

                if color is None:
                    color = tuple(attributes["color"][i] for i in range(0, 3))
            except:
                raise PlatformTypeException("Couldn't load platform type - {}".format(ptype))

        self.width = width
        self.height = height
        self.color = color
        self.rect = pygame.Rect(rect + (self.width, self.height))
        self.posn = [rect[0], rect[1]]
        self.ptype = ptype

    # draws the platform
    def draw_platform(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)

        # Draws an outline around the platform, its more pleasant to look at
        pygame.draw.rect(surface, BLACK, self.rect, 1)

    # updates the platform's rect
    def update_rect(self):
        self.rect = pygame.Rect((self.posn[0], self.posn[1]) + (self.width, self.height))
