import pygame
import random
import math
from platform_config import Platform
import GLOBALS
from GLOBALS import BLACK
import json
import sys


# class containing all of the groups in the game
# the class also contains the world posn and the screen
# object that is initialized later
class GameGroups:
    def __init__(self):
        self.players = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.gravity_units = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()
        self.scrolling_units = pygame.sprite.Group()
        self.world_posn = [0, 0]
        self.screen = None

# initializing groups
groups = GameGroups()

# setting the size dimensions for the screen
size = GLOBALS.size

# set the size of the world, initializing to None
world_size = None


# rule class that dictates general rules for the game, much of the
# code is dependent on the values of these variables
class Rules:

    # Represents the closest distance that an enemy can spawn to the player (x coordinate)
    spawn_distance = 150

    # This is the amount of HP the player starts off with
    player_hp = 500000

    # This is the amount of HP the enemies start off with
    enemy_hp = 10

    # This is the maximum amount of enemies that can spawn at one time
    spawn_count = 0

    # This represents how many seconds must pass until a new enemy is spawned
    spawn_rate = 1

    # Represents how many ticks there should be in a second
    clock_tick = 100

    # How many seconds of immortality does the player get after getting hit
    immortality = 2

    # Loads platforms into the game if True
    platforms_exist = True

    # True if the game should be placed in debug mode
    debug_mode = False

    # The height of the floor
    floor_height = GLOBALS.floor_height


# class that represents screen scrolling mechanics
class Screen:

    def __init__(self):
        self.should_scroll = None

    # moves all the pieces but the player by the amount that the player
    # moved either to the right or left
    def scroll_pieces(self, player_displacement):

        player = groups.players.sprites()[0]

        # moves the player normally since the player is at the very edge of the map
        if (groups.world_posn[0] == 0 and (player_displacement < 0)) \
                or (groups.world_posn[0] == size[0] - world_size[0] and (player_displacement > 0)):
            player.posn[0] += player_displacement

        # since the player is not at the edge of the map, center the player
        elif not (player.posn[0] == ((size[0] / 2) - (player.WIDTH / 2))):
            self.center_player(player_displacement)

        # since the player is already centered, simply scroll the screen
        else:
            self.apply_displacement_to_all_pieces(player_displacement)

            # scroll the 'world' as well
            groups.world_posn[0] -= player_displacement

        # make sure the world is kept in place when you reach the end of it
        self.bound_the_world(player_displacement)

    def bound_the_world(self, player_displacement):
        # keeps the world at the x coordinate zero if player is at the left side of the map
        if player_displacement < 0 < groups.world_posn[0]:
            self.apply_displacement_to_all_pieces(groups.world_posn[0])
            groups.world_posn[0] = 0

        # keeps the world at the x coordinate size[0] - world_size[0] since the player is on the right side of map
        elif player_displacement > 0 and groups.world_posn[0] + world_size[0] < size[0]:
            self.apply_displacement_to_all_pieces((groups.world_posn[0] + world_size[0]) - size[0])
            groups.world_posn[0] = size[0] - world_size[0]

    # scrolls all pieces that are supposed to be scrolled
    def apply_displacement_to_all_pieces(self, displacement):
        for unit in groups.scrolling_units.sprites():
            unit.posn[0] -= displacement
            unit.update_rect()

    # puts the player in the center and scrolls all pieces accordingly
    def center_player(self, player_displacement):

        player = groups.players.sprites()[0]

        player.posn[0] += player_displacement

        # account for the player moving away from the edges from the map by centering the
        # player according to where the player was and what direction the player was heading
        if player.posn[0] > ((size[0] / 2) - (player.WIDTH / 2)) and player_displacement > 0:
            player.posn[0] = ((size[0] / 2) - (player.WIDTH / 2))

        elif player.posn[0] < ((size[0] / 2) - (player.WIDTH / 2)) and player_displacement < 0:
            player.posn[0] = ((size[0] / 2) - (player.WIDTH / 2))

        # if the previous to conditions were False, then there is no need to center the player
        else:
            pass

# making sure to update the groups's screen attribute to an initialized screen
groups.screen = Screen()


# physics engine for free fall, gravity and etc
class Physics:

    knock_back_constant_x = 10
    knock_back_constant_y = 7

    def __init__(self):

        self.tick = 0

    # takes in a platform object and the units previous position
    # and returns the highest platform that the player is above
    def get_highest_platform(self, landing, posn):
        highest_platform = None
        for land in landing:
            if highest_platform is None:
                highest_platform = land
            elif posn < land.rect.top < highest_platform.rect.top:
                highest_platform = land
            else:
                pass
        return highest_platform

    # takes in a platform object and the units previous position
    # and returns the lowest platform that the player is below
    def get_lowest_platform(self, landing, posn):
        lowest_platform = None
        for land in landing:
            if lowest_platform is None:
                lowest_platform = land
            elif posn > land.rect.top > lowest_platform.rect.top:
                lowest_platform = land
            else:
                pass
        return lowest_platform

    # takes in the sprite, it's last position and a platform
    # and returns True if the unit is either completely below
    # or completely above the platform
    def completely_above_or_below(self, unit, posn, platform):
        return posn <= platform.rect.top - unit.HEIGHT or posn >= platform.rect.top + platform.rect.height

    # checks to see if any units are being blocked by a platform
    # and adjusts their attributes accordingly
    def check_for_blockage(self, unit):
        platforms = pygame.sprite.spritecollide(unit, groups.platforms, dokill=False)
        if len(platforms) > 0:
            for platform in platforms:
                self.adjust_for_blockage(unit, platform)

    # adjusts the units attributes accordingly, set if_happened=True
    # for the function to return whether a blockage occurred
    def adjust_for_blockage(self, unit, platform, if_happened=False):
        # if the player is inside of the platform
        if platform.rect.left - unit.WIDTH < unit.posn[0] < platform.rect.left + platform.rect.width:
            # check to see if the player is knocked back to know what direction to use
            # don't use knock_dir if it is "up" since there was no x change caused by
            # knock back in that specific case
            if self.is_knocked_back(unit) and not unit.knock_dir == "up":
                direction = unit.knock_dir
            else:
                direction = unit.direction

            # record the previous x in order to scroll the pieces properly if player ends up in a platform
            previous_x = unit.posn[0]

            # keep the player on the side of the platform and scroll everything accordingly
            if direction == "right":
                calculation = platform.rect.left - unit.WIDTH
                if type(unit) == Player:
                    groups.screen.scroll_pieces(int(calculation - previous_x))
                else:
                    unit.posn[0] = platform.rect.left - unit.WIDTH
                unit.motion = False
                unit.update_rect()
            elif direction == "left":
                calculation = platform.rect.left + platform.rect.width
                if type(unit) == Player:
                    groups.screen.scroll_pieces(int(calculation - previous_x))
                else:
                    unit.posn[0] = platform.rect.left + platform.rect.width
                unit.motion = False
                unit.update_rect()
            else:
                pass

            unit.knock_back_blocked = True

            if if_happened:
                return True
            else:
                return False

    # checks for general platform collisions and adjusts the units accordingly
    # based on the passed in unit and position
    def check_platform_collision(self, unit, last_posn):
        landing = pygame.sprite.spritecollide(unit, groups.platforms, dokill=False)
        if len(landing) > 0:
            for platform in landing:

                # if the player is not completely above or below the platform, adjust it for blockage
                if not self.completely_above_or_below(unit, last_posn, platform):
                    self.adjust_for_blockage(unit, platform)
                # since the unit is not completely underneath or above, the unit must be either landing
                # onto a platform or hitting into the platform from underneath
                else:
                    # if the unit has a "down" y_dir, then the unit must be landing on a platform
                    # so change all of unit's attributes accordingly
                    if unit.y_dir == "down":
                        highest_platform = self.get_highest_platform(landing, last_posn)
                        unit.y_base = highest_platform.rect.top - unit.HEIGHT
                        unit.posn[1] = unit.y_base
                        unit.gravity_time = 0
                        unit.knock_back_time = 0
                        unit.knock_back_blocked = False
                        unit.free_fall = False
                        unit.jumping = False

                    # unit must otherwise have an "up" y_dir and the unit must be hitting into a platform
                    # from underneath, so change all of the unit's attributes accordingly
                    else:
                        lowest_platform = self.get_lowest_platform(landing, last_posn)
                        unit.y_base = lowest_platform.rect.top + lowest_platform.rect.height
                        unit.posn[1] = unit.y_base
                        unit.gravity_time = 1
                        unit.knock_back_time = 0
                        unit.knock_back_blocked = False
                        unit.free_fall = True
                        unit.jumping = False
                        unit.y_dir = "down"
            unit.update_rect()

    # applies gravity where it is applicable
    def apply_gravity(self, unit):
        if unit.gravity_time != 0 and not unit.free_fall:
            # if the unit has reach the highest point of the jump, change the y_dir to "down"
            if self.calc_disp(unit.gravity_time, unit.max_jump) == unit.max_jump * 2:
                unit.y_dir = "down"

            unit.posn[1] = unit.y_base - self.calc_disp(unit.gravity_time, unit.max_jump)
            unit.gravity_time += 1
            unit.update_rect()

        elif unit.gravity_time != 0 and unit.free_fall:

            unit.posn[1] = unit.y_base - self.free_fall(unit.gravity_time)
            unit.gravity_time += 1
            unit.update_rect()

    # checks if the passed in unit should be experiencing free fall
    def check_for_free_fall(self, unit):
        # If the unit is already in free fall or is knocked back there is no need to check so return
        if unit.free_fall:
            return

        # since jumping is it's own mechanism, don't apply free fall, otherwise apply free fall
        if not unit.jumping:
            standing = []
            for land in groups.platforms.sprites():
                standing.append((unit.posn[1] + unit.HEIGHT == land.rect.top
                                 and land.rect.left - unit.WIDTH < unit.posn[0] < land.rect.left + land.rect.width))
            if True not in standing:
                unit.free_fall = True
                unit.gravity_time = 1

    # applies knock back to the passed in unit if it is applicable
    def apply_knock_back(self, unit):
        if unit.knock_back_time > 0:
            # if the knock back reaches the highest y point, change the unit's y_dir to down
            if self.calc_knock_y(unit.knock_back_time) == self.knock_back_constant_y * self.knock_back_constant_y:
                unit.y_dir = "down"

            # if the knock back is not blocked by a platform, move the screen accordingly
            if not unit.knock_back_blocked:
                previous_x = unit.posn[0]
                if unit.knock_dir == "left":
                    # if the player is knocked back you must scroll the screen, otherwise simply
                    # change the x coordinate of the unit
                    if type(unit) == Player:
                        calculation = unit.x_base - self.calc_knock_x(unit.knock_back_time)
                        groups.screen.scroll_pieces(int(calculation - previous_x))
                    else:
                        unit.posn[0] = unit.x_base - self.calc_knock_x(unit.knock_back_time)
                elif unit.knock_dir == "right":
                    # if the player is knocked back you must scroll the screen, otherwise simply
                    # change the x coordinate of the unit
                    if type(unit) == Player:
                        calculation = unit.x_base + self.calc_knock_x(unit.knock_back_time)
                        groups.screen.scroll_pieces(int(calculation - previous_x))
                    else:
                        unit.posn[0] = unit.x_base + self.calc_knock_x(unit.knock_back_time)

                # pass when the direction is "up" because the unit always experiences a y displacement
                # during a knock back which is accounted for in the next line of code
                else:
                    pass

            unit.posn[1] = unit.y_base - self.calc_knock_y(unit.knock_back_time)
            unit.update_rect()
            unit.knock_back_time += 1

    # updates the physics engine
    def update(self):
        # every time the tick is 4, apply gravity
        if self.tick == 4:
            units = groups.gravity_units.sprites()
            for unit in units:
                # apply gravity and free fall only if the unit is not knocked back
                if not self.is_knocked_back(unit):
                    last_y = unit.posn[1]
                    self.apply_gravity(unit)
                    self.check_platform_collision(unit, last_y)
                    self.check_for_free_fall(unit)
            self.tick = 0
        # every time the tick is 2 and 4, apply knock back
        if self.tick == 4 or self.tick == 2:
            units = groups.gravity_units.sprites()
            for unit in units:
                last_y = unit.posn[1]
                self.apply_knock_back(unit)
                # check for platform collision if the unit is knocked back
                if self.is_knocked_back(unit):
                    self.check_platform_collision(unit, last_y)
            self.tick += 1

        # for each remaining tick, check to see if the unit hit into a platform
        # from the side, no need to check if it was from the top or bottom because
        # that is only possible if the unit is knocked back or experiencing gravity/free fall
        remaining_ticks = [0, 1, 3]
        if self.tick in remaining_ticks:
            units = groups.gravity_units.sprites()
            for unit in units:
                self.check_for_blockage(unit)
            self.tick += 1

    # returns true if the unit is being knocked back
    def is_knocked_back(self, unit):
        return unit.knock_back_time > 0

    # calculates the displacement for a unit that is jumping
    def calc_disp(self, time, max_jump):
        parabola_shift = int(math.sqrt(max_jump))
        return (-2 * ((time - parabola_shift) * (time - parabola_shift))) + (2 * max_jump)

    # calculates the displacement for a unit that is in free fall
    def free_fall(self, time):
        return -3 * time * time

    # calculates the x displacement for a unit that is knocked back
    def calc_knock_x(self, time):
        return math.sqrt(time) + self.knock_back_constant_x

    # calculates the y displacement for a unit that is knocked back
    def calc_knock_y(self, time):
        return (-1 * (time - self.knock_back_constant_y)
                * (time - self.knock_back_constant_y)) + (self.knock_back_constant_y * self.knock_back_constant_y)


# player class to represent the player
class Player(pygame.sprite.Sprite):

    WIDTH = 50
    HEIGHT = 50
    posn = [(size[0] / 2) - (WIDTH / 2), 0] #size[1] - HEIGHT - Rules.floor_height]
    gravity_time = 0
    knock_back_time = 0
    knock_length = 4
    HP = Rules.player_hp
    max_jump = 64
    y_base = posn[1]
    x_base = posn[0]
    free_fall = False
    jumping = False
    y_dir = "down"
    knock_dir = None
    speed = 4
    immortality = False
    knock_back_blocked = False
    immortality_count = 0

    def __init__(self):
        pygame.sprite.Sprite.__init__(self, groups.players, groups.gravity_units)
        self.direction = "right"
        self.motion = False
        self.color = BLACK
        self.rect = None
        self.update_rect()

    # draws the player onto the surface
    def draw_player(self, surface):
        # creates a blinking affect if the player was hit
        if self.immortality:
            if not self.immortality_count % 6 == 0:
                return
        pygame.draw.rect(surface, self.color, self.posn + [self.WIDTH, self.HEIGHT])
        if Rules.debug_mode:
            pygame.draw.rect(surface, self.color, self.rect, 1)

    # keeps the player within the bounds of the screen
    def confine_player(self):
        if self.posn[0] < 0:
            self.posn[0] = 0
            self.motion = False

        elif self.posn[0] > size[0] - self.WIDTH:
            self.posn[0] = size[0] - self.WIDTH
            self.motion = False

    # moves the player based on the players direction
    def move_player(self):

        if self.direction == "right":
            groups.screen.scroll_pieces(self.speed)

        elif self.direction == "left":
            groups.screen.scroll_pieces(self.speed * -1)

        # there are no other directions to account for so pass
        else:
            pass

        self.update_rect()

    # updates the players rect
    def update_rect(self):
        self.rect = pygame.Rect(self.posn + [self.WIDTH, self.HEIGHT])

    def check_for_enemy_collision(self):

        # checks for collision between the player and an enemy
        collision = pygame.sprite.spritecollide(self, groups.enemies.sprites(), False)
        if len(collision) > 0 and not self.immortality:
            self.immortality = True
            self.HP -= collision[0].strength
            self.knock_back_time += 1
            self.gravity_time = 0
            self.jumping = False
            self.free_fall = False
            self.y_dir = "up"
            self.y_base = self.posn[1]
            if self.posn[0] < collision[0].posn[0]:
                self.knock_dir = "left"
            elif self.posn[0] > collision[0].posn[0]:
                self.knock_dir = "right"
            else:
                self.knock_dir = "up"

    # updates the player
    def update(self):
        # constantly update the x_base to where the player is currently placed
        self.x_base = self.posn[0]

        # keep track of how long the player has been 'immortal'
        if self.immortality:
            if self.immortality_count == Rules.clock_tick * Rules.immortality:
                self.immortality = False
                self.immortality_count = 0
            else:
                self.immortality_count += 1

        # if the player has no more HP the player dies
        if self.HP <= 0:
            self.kill()

        # check if the player has collided with an enemy
        self.check_for_enemy_collision()

        # move the player only if the player is in motion
        if self.motion:
            self.move_player()

        # confine the player
        self.confine_player()

        self.update_rect()

    # USED ONLY FOR DEBUGGING
    def print_stats(self):

        floor = None
        platforms = groups.platforms.sprites()
        for platform in platforms:
            if platform.ptype == "FloorPlatform":
                floor = platform

        # helpful to see the most important attributes when fixing a bug
        print "---------------------------------------------"
        print "Gravity time: " + str(self.gravity_time)
        print "Knock back time: " + str(self.knock_back_time)
        print "HP: " + str(self.HP)
        print "Free Fall: " + str(self.free_fall)
        print "Jumping: " + str(self.jumping)
        print "Y Dir: " + str(self.y_dir)
        print "Knock Dir: " + str(self.knock_dir)
        print "x: " + str(self.posn[0])
        print "y: " + str(self.posn[1])
        print "World posn: " + str(groups.world_posn[0])
        print "Floor posn: " + str(floor.rect[0])
        print "---------------------------------------------"


# class to represent a bullet
class Bullet(pygame.sprite.Sprite):

    def __init__(self, player, direction):
        pygame.sprite.Sprite.__init__(self, groups.bullets, groups.scrolling_units)
        self.direction = direction
        if direction == "right":
            self.posn = [player.posn[0] + player.WIDTH,
                         player.posn[1] + (player.HEIGHT / 2)]
        elif direction == "left":
            self.posn = [player.posn[0],
                         player.posn[1] + (player.HEIGHT / 2)]
        self.speed = 5
        self.HEIGHT = 3
        self.WIDTH = 6
        self.rect = None
        self.strength = 1

    # updates the bullets rect
    def update_rect(self):
        self.rect = pygame.Rect(self.posn + [self.WIDTH, self.HEIGHT])

    # updates the bullet
    def update(self):
        self.update_rect()

        # if the bullet is off the screen, kill the bullet
        if self.posn[0] < 0 or self.posn[0] > size[0]:
            self.kill()

        if self.direction == "right":
            self.posn[0] += self.speed

        elif self.direction == "left":
            self.posn[0] -= self.speed

        # there is no other direction to account for so pass
        else:
            pass

        # check to see if the bullet collided with an enemy and decrease the enemy's HP
        enemies_hit = pygame.sprite.spritecollide(self, groups.enemies.sprites(), False)
        for enemy in enemies_hit:
            enemy.HP -= self.strength
            enemy.color = (enemy.color[0] + 10, enemy.color[1] + 10, enemy.color[2] + 10)

        # if the bullet hit an enemy, kill the bullet
        if len(enemies_hit) > 0:
            self.kill()

    # draws the bullet on the surface
    def draw_bullet(self, surface):
        pygame.draw.rect(surface, BLACK, self.posn + [self.WIDTH, self.HEIGHT])


# class to represent an enemy
class Enemy(pygame.sprite.Sprite):

    RADIUS = 25
    HEIGHT = RADIUS * 2
    HP = 10
    direction = None
    jump_speed = 5
    gravity_time = 0
    motion = False
    strength = 1

    WIDTH = RADIUS * 2
    # knock_back_time = 0
    # knock_length = 4

    max_jump = 64

    free_fall = False
    jumping = False
    y_dir = "down"
    knock_dir = None
    # speed = 4

    knock_back_time = 0
    knock_length = 4

    speed = 4
    immortality = False
    knock_back_blocked = False
    immortality_count = 0

    def __init__(self):
        pygame.sprite.Sprite.__init__(self, groups.enemies, groups.gravity_units, groups.scrolling_units)
        self.color = (100, 100, 100)
        self.player = groups.players.sprites()[0]

        # this block of code is attempting to generate a spawn position that is fair to the player
        fair_spawn = False
        while not fair_spawn:
            self.posn = [random.randint(0, size[0]), self.HEIGHT] #size[1] - self.HEIGHT - Rules.floor_height - 100] # size[1] - 425] # size[1] - self.RADIUS]
            if abs(self.player.posn[0] - self.posn[0]) > Rules.spawn_distance:
                fair_spawn = True
            else:
                pass
        self.y_base = self.posn[1]
        self.x_base = self.posn[0]
        self.rect = None
        self.update_rect()

    # draws the enemy onto the surface
    def draw_enemy(self, surface):
        for number in self.color:
            if number > 255:
                self.color = (255, 255, 255)
                break
        pygame.draw.circle(surface, self.color, [self.posn[0] + self.RADIUS, self.posn[1] + self.RADIUS], self.RADIUS)
        pygame.draw.circle(surface, BLACK, [self.posn[0] + self.RADIUS, self.posn[1] + self.RADIUS], self.RADIUS, 1)
        if Rules.debug_mode:
            pygame.draw.rect(surface, BLACK, self.rect, 4)

    # moves the enemy based on the enemys direction
    def move_enemy(self):
        if self.direction == "right":
            self.posn[0] += 1

        elif self.direction == "left":
            self.posn[0] -= 1

        # no other direction to account for so pass
        else:
            pass

    # checks if the enemy fell off the map
    def apply_fell_off(self):
        if self.posn[1] > size[1] - Rules.floor_height:
            self.kill()

    # updates the rect of the enemy
    def update_rect(self):
        self.rect = pygame.Rect(self.posn + [self.WIDTH, self.HEIGHT])

    # updates the enemy
    def update(self):
        self.x_base = self.posn[0]

        # kill the enemy if its HP is less than zero
        if self.HP <= 0:
            self.kill()

        if self.posn[0] < self.player.posn[0]:
            self.direction = "right"

        elif self.posn[0] > self.player.posn[0]:
            self.direction = "left"

        # no other direction to account for so pass
        else:
            pass

        self.move_enemy()
        self.apply_fell_off()
        self.update_rect()
        #print str(self.posn[0]) + " " + str(self.posn[1])

    # USED ONLY FOR DEBUGGING
    def print_stats(self):

            print "---------------------------------------------"
            print "Gravity time: " + str(self.gravity_time)
            print "Knock back time: " + str(self.knock_back_time)
            print "HP: " + str(self.HP)
            print "Free Fall: " + str(self.free_fall)
            print "Jumping: " + str(self.jumping)
            print "Y Dir: " + str(self.y_dir)
            print "Knock Dir: " + str(self.knock_dir)
            print "x: " + str(self.posn[0])
            print "y: " + str(self.posn[1])
            print "---------------------------------------------"

class StartGame:

    # Used for debugging
    display = False

    def __init__(self):
        self.current_level = self.load_level(sys.argv[1])
        pygame.init()
        self.clock = pygame.time.Clock()
        self.surface = pygame.display.set_mode(size)
        self.player = Player()
        self.spawn = 0
        self.killed = 0
        self.physics = Physics()
        self.platforms = self.load_platforms()

    def load_level(self, level_name):

        global world_size

        with open("levels/{}.stg".format(level_name)) as filename:
            level = json.load(filename)

        world_size = level["rules"]["world-size"]

        return level

    # loads all platforms into the game
    def load_platforms(self):

        platforms = []

        # if in the rules, platforms_exist is false, these platforms
        # will not be generated. Otherwise all platforms that appear
        # in the game can be added into this platforms list

        for row in self.current_level["platforms"]:
            if Rules.platforms_exist or row["type"] == "FloorPlatform":
                platforms.append(
                    Platform(groups, (row["x"], row["y"]), row["type"], row["width"], row["height"], row["color"])
                )
            else:
                pass

        return platforms

    # takes in a key press event and responds to it
    def evaluate_keypress(self, event):

        # if the player presses the 'a' key, then generate a bullet
        if event.key == pygame.K_a:
            Bullet(self.player, self.player.direction)

        # used for debugging, lets you print out your stats. could be a game feature later
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_s and Rules.debug_mode:
            self.display = True

        # sets the players direction and motion boolean based on which arrow key was pressed
        elif event.key == pygame.K_RIGHT and event.type == pygame.KEYDOWN:
            self.player.motion = True
            self.player.direction = "right"
        elif event.key == pygame.K_LEFT and event.type == pygame.KEYDOWN:
            self.player.motion = True
            self.player.direction = "left"
        elif event.type == pygame.KEYUP and (event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT):
            self.player.motion = False

        # if the used pressed 'space' then put the player into jumping mode as long as the
        # player is not already jumping, experiencing free fall or being knocked back
        elif event.key == pygame.K_SPACE and event.type == pygame.KEYDOWN \
                and not self.player.jumping and not self.player.free_fall and not self.player.knock_back_time > 0:
            self.player.gravity_time += 1
            self.player.jumping = True
            self.player.y_dir = "up"

        # all other key events are ignored so pass
        else:
            pass

    # draws all the bullets
    def draw_bullets(self):
        for bullet in groups.bullets.sprites():
            bullet.draw_bullet(self.surface)

    # draws all the enemies
    def draw_enemies(self):
        for enemy in groups.enemies.sprites():
            enemy.draw_enemy(self.surface)

    # draws all platforms
    def draw_platforms(self):
        for platform in groups.platforms.sprites():
            platform.draw_platform(self.surface)

    # returns True if the player is alive
    def player_is_alive(self):
        return len(groups.players.sprites()) > 0

    # spawns the enemy at the specified spawn rate in Rules
    def spawn_enemy(self):
        if not len(groups.enemies.sprites()) >= Rules.spawn_count:
            if self.spawn == Rules.spawn_rate * Rules.clock_tick:
                Enemy()
                self.spawn = 0
            else:
                self.spawn += 1

    # displays the game over screen
    def display_game_over(self):
        font = pygame.font.SysFont("monospace", ((size[0] + size[1]) / 18))
        label = font.render("GAME OVER", 1, BLACK)
        self.surface.blit(label, (size[0] / 4, size[0] / 6))
        score = font.render("SCORE:%d" % self.killed, 1, (0, 0, 0))
        self.surface.blit(score, (size[0] / 3, size[0] / 4))

    # runs the main game engine
    def run_engine(self):

        done = False
        while not done:
            # make the clock tick at the rate specified in Rules
            self.clock.tick(Rules.clock_tick)

            # wait for events and interpret them accordingly
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    done = True
                elif event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                    self.evaluate_keypress(event)
                # all other events are ignored so pass
                else:
                    pass

            # fill the background
            self.surface.fill(self.current_level["rules"]["background-color"])

            # draw all necessary elements
            self.draw_platforms()
            self.player.draw_player(self.surface)
            self.draw_bullets()
            self.draw_enemies()

            # if the player is alive, update everything
            if self.player_is_alive():

                groups.bullets.update()

                # spawn the enemy at the specified spawn rate in Rules
                self.spawn_enemy()

                groups.players.update()

                # enemies die when they are updated, therefore keeping track
                # of the enemy count before hand and after, lets you count
                # how many enemies the player was able to kill before dying
                enemies_before = len(groups.enemies.sprites())
                groups.enemies.update()
                enemies_after = len(groups.enemies.sprites())

                # keep track of how many enemies were killed
                self.killed += enemies_before - enemies_after

                # The physics engine must update after all sprites that are dependent on it
                # have been updated first, specifically because this engine accounts for
                # all of the platform collision that occurs in the game
                self.physics.update()

                # if display was set to True, print the player's stats, this can only
                # happen if debug_mode in Rules is set to True and the user presses
                # the 's' key when playing the game
                if self.display:
                    self.player.print_stats()
                    self.display = False

            # if the player is not alive, display the game over screen
            else:
                self.display_game_over()

            # update the general display
            pygame.display.update()

        # quit the game if the while loop is broken
        pygame.quit()

# run the game if this is the first script that is ran
if __name__ == "__main__":
    # initialize the StartGame object
    game = StartGame()
    # run the engine to set the game in motion
    game.run_engine()
