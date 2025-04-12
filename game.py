from random import randint
import threading
import neat
import pygame

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 750
BIRD_X = 200
GRAVITY = 1.2
JUMP_SPEED = -12
GAME_SPEED = -4
PIPE_WIDTH = 86
PIPE_GAP = 200

PIPE_SPRITE = pygame.image.load('sprites/cano.png')
SPRITES = {'bird': [pygame.image.load('sprites/flap1.png'),
                    pygame.image.load('sprites/flap2.png'),
                    pygame.image.load('sprites/flap3.png')],
           'pipe': [PIPE_SPRITE,
                    pygame.transform.rotate(PIPE_SPRITE, 180)],
           'ground': pygame.image.load('sprites/chao.png'),
           'tree': pygame.image.load('sprites/arvores.png'),
           'building': pygame.image.load('sprites/predios.png'),
           'cloud': pygame.image.load('sprites/nuvens.png')}


class Bird:
    def __init__(self, screen_height):
        self.sprite_index = 0
        self.sprite_buffer = 3
        self.game_over = False
        self.on_ground = False
        self.sprites = SPRITES['bird']
        self.default_y = screen_height // 2
        self.rectangle = pygame.Rect(BIRD_X, self.default_y, 50, 40)
        self.angle = 0
        self.vertical_speed = 0
        self.angle_speed = -3

    def restart(self):
        self.rectangle.y = self.default_y
        self.angle = 0
        self.game_over = False
        self.on_ground = False

    def ground_collision(self):
        self.on_ground = True
        self.vertical_speed = 0

    def jump(self):
        self.angle = 20
        self.vertical_speed = JUMP_SPEED

    def update(self):
        if not self.game_over:
            self.sprite_index += 1
            if self.sprite_index >= len(self.sprites)*self.sprite_buffer:
                self.sprite_index = 0
            if self.angle_speed > -70:
                self.angle += self.angle_speed
        if not self.on_ground:
            self.vertical_speed += GRAVITY
            self.rectangle.y += self.vertical_speed

    def draw(self):
        sprite = pygame.transform.rotate(self.sprites[self.sprite_index//self.sprite_buffer], self.angle)
        screen.blit(sprite, self.rectangle)


class Prop:
    def __init__(self, x, y, width, height, sprite):
        self.width = width
        self.rectangle = pygame.Rect(x, y, width, height)
        self.sprite = sprite

    def draw(self):
        screen.blit(self.sprite, self.rectangle)


class Pipe:
    def __init__(self, x, screen_height):
        self.middle_y_screen = screen_height // 2
        self.height = 836
        self.gap = 200
        self.upper_rectangle = pygame.Rect(x, 0, 86, self.height)
        self.upper_sprite, self.bottom_sprite = SPRITES['pipe']
        self.bottom_rectangle = pygame.Rect(x, 0, 86, self.height)
        self.rectangles = [self.upper_rectangle, self.bottom_rectangle]
        self.opening_y = 0
        self.random_opening()

    def move(self, speed):
        self.upper_rectangle.x += speed
        self.bottom_rectangle.x += speed

    def random_opening(self):
        self.opening_y = self.middle_y_screen + randint(0, 401) - 150
        self.upper_rectangle.y = self.opening_y - self.gap - self.height
        self.bottom_rectangle.y = self.opening_y

    def draw(self):
        screen.blit(self.upper_sprite, self.upper_rectangle)
        screen.blit(self.bottom_sprite, self.bottom_rectangle)


class Pipes:
    def __init__(self, screen_width, screen_height):
        self.pipes = []
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.start_x = 500
        self.build_pipes()

    def build_pipes(self):
        x = self.start_x
        while x <= self.screen_width + self.start_x + PIPE_WIDTH:
            self.pipes.append(Pipe(x, self.screen_height))
            x += PIPE_WIDTH + PIPE_GAP

    def move(self, speed):
        for pipe in self.pipes:
            pipe.move(speed)
            if pipe.upper_rectangle.right <= 0:
                pipe.move(len(self.pipes) * (PIPE_WIDTH + PIPE_GAP))
                pipe.random_opening()

    def draw(self):
        for pipe in self.pipes:
            pipe.draw()


class Game:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.lost = False
        self.ai_mode = False
        self.closest_pipe_index = 0
        self.genomes = []
        self.neural_networks = []
        self.birds = [Bird(screen_height)]
        self.BACKGROUND_COLOR = (112, 197, 206)
        self.grounds = self.create_props(0, 209, 75, SPRITES['ground'])
        self.tress = self.create_props(70, 959, 52, SPRITES['tree'])
        self.buildings = self.create_props(105, 960, 54, SPRITES['building'])
        self.clouds = self.create_props(90, 959, 114, SPRITES['cloud'])
        self.pipes = Pipes(screen_width, screen_height)

    def restart(self):
        self.lost = False
        self.restart_pipes()
        self.birds[0].restart()

    def restart_pipes(self):
        self.closest_pipe_index = 0
        self.pipes = Pipes(self.screen_width, self.screen_height)

    def create_props(self, prop_y ,prop_width, prop_height, sprite):
        i = 1
        props = []
        prop_x = 0
        next_prop_x = 0
        while next_prop_x < self.screen_width + prop_width:
            next_prop_x = i * prop_width
            props.append(Prop(prop_x, self.screen_height-prop_y-prop_height, prop_width, prop_height, sprite))
            i += 1
            prop_x = next_prop_x

        return props

    def input(self):
        if not self.lost:
            self.birds[0].jump()
        else:
            self.restart()

    def over(self, index):
        if not self.ai_mode:
            self.lost = True
            self.birds[0].game_over = True
        else:
            self.birds.pop(index)
            self.genomes.pop(index)
            self.neural_networks.pop(index)

    def reward_birds(self):
        for genome in self.genomes:
            genome.fitness += 5

    def check_collision(self, bird, index):
        if bird.rectangle.y < 0:
            self.over(index)
        elif bird.rectangle.bottom > self.grounds[0].rectangle.top:
            if not self.ai_mode:
                bird.ground_collision()
            self.over(index)
        elif bird.rectangle.collidelist(self.pipes.pipes[self.closest_pipe_index].rectangles) != -1:
            if self.ai_mode:
                self.genomes[index].fitness -= 1
            self.over(index)

    def update(self):
        for index, bird in enumerate(self.birds):
            if self.ai_mode:
                self.genomes[index].fitness += 0.1
                inputs = (
                    bird.rectangle.y,
                    self.pipes.pipes[self.closest_pipe_index].opening_y
                )
                output = self.neural_networks[index].activate(inputs)
                if output[0] > 0.5:
                    bird.jump()

            bird.update()
            self.check_collision(bird, index)
        if self.lost:
            return
        move_props(self.grounds, GAME_SPEED)
        self.pipes.move(GAME_SPEED)
        move_props(self.tress, int(0.75 * GAME_SPEED))
        move_props(self.buildings, int(0.5 * GAME_SPEED))
        move_props(self.clouds, int(0.25 * GAME_SPEED))

        if self.pipes.pipes[self.closest_pipe_index].upper_rectangle.right < BIRD_X:
            self.closest_pipe_index += 1
            if self.ai_mode:
                self.reward_birds()
            if self.closest_pipe_index >= len(self.pipes.pipes):
                self.closest_pipe_index = 0


    def draw(self):
        screen.fill(self.BACKGROUND_COLOR)

        for prop in (*self.clouds, *self.buildings, *self.tress):
            prop.draw()

        self.pipes.draw()

        for prop in (*self.birds, *self.grounds):
            prop.draw()

    def switch_game_mode(self):
        if not self.ai_mode:
            self.lost = False
            self.birds.clear()
            self.ai_mode = True
            start_ai()
        else:
            self.ai_mode = False
            self.genomes.clear()
            self.neural_networks.clear()
            self.birds = [Bird(SCREEN_HEIGHT)]
            self.restart_pipes()

    def eval_genomes(self, genomes, config):
        self.restart_pipes()
        for _, genome in genomes:
            self.birds.append(Bird(SCREEN_HEIGHT))
            genome.fitness = 0
            self.genomes.append(genome)
            net = neat.nn.FeedForwardNetwork.create(genome, config)
            self.neural_networks.append(net)
        while len(game.birds) > 0:
            if not self.ai_mode:
                exit()
            clock.tick(10)


def start_ai():
    config_file_path = 'config.txt'
    config = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_file_path
    )
    population = neat.Population(config)
    threading.Thread(target=lambda: population.run(game.eval_genomes, 50), daemon=True).start()


def move_props(props, speed):
    for prop in props:
        prop.rectangle.x += speed
        if prop.rectangle.right <= 0:
            prop.rectangle.x += len(props) * prop.width


pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), vsync=1)
clock = pygame.Clock()
game = Game(SCREEN_WIDTH, SCREEN_HEIGHT)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_SPACE:
                game.input()
            elif event.key == pygame.K_TAB:
                game.switch_game_mode()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                game.input()

    game.update()
    game.draw()

    pygame.display.flip()
    clock.tick(40)

pygame.quit()
