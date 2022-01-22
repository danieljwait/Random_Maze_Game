from time import perf_counter
import pygame
import random
import sys

pygame.init()

TITLE_FONT = pygame.font.SysFont('consolas', 100)
MAIN_FONT = pygame.font.SysFont('consolas', 32)
CONTROLS_FONT = pygame.font.SysFont('consolas', 20)
COLOUR = {
    'White': (255, 255, 255),
    'Black': (0, 0, 0),
    'Red': (255, 0, 0),
    'Green': (0, 255, 0)
}

# Unable to do variable window size due to floating point errors in grid
# Eg, a size of 899 produces lines when the square pos has been rounded
WIN_WIDTH = 900

DIFFICULTY = {
    'Simple': 5,
    'Regular': 10,
    'Complex': 15
}

CONTROLS = ['[Q] - Back to menu',
            '[R] - Back to start',
            '[W,A,S,D] - To move',
            ]

# Creates game window
win = pygame.display.set_mode((WIN_WIDTH, WIN_WIDTH))
pygame.display.set_caption('Maze Game')


class Square:
    def __init__(self, game, x: float, y: float, colour: tuple) -> None:
        self.x = x
        self.y = y
        self.colour = colour
        self.rect = pygame.Rect(self.x, self.y, game.small_square, game.small_square)

    def draw(self, game) -> None:
        # Draws squares with offset to centre the maze in the window
        pygame.draw.rect(win, self.colour, self.rect.move(game.offset, game.offset))


class AdjacencyMatrix:
    def __init__(self, game) -> None:
        # This creates an the adjacency matrix for the graph which is an n*n grid
        # of vertices, where each vertices is connected to its neighbour. So there
        # are n^2 vertices and n(2n-2) edges.

        self.vertex_across = game.squares_across
        self.vertex_total = game.squares_total
        self.matrix = []  # Indexed [row][column]

        # Creates empty matrix
        for row in range(self.vertex_total):
            self.matrix.append([0] * self.vertex_total)

        # Fills in matrix
        for vertex in range(self.vertex_total):
            # Square to the left
            adj_pos = vertex - 1
            if adj_pos // self.vertex_across == vertex // self.vertex_across:  # Is on the same row
                self.matrix[vertex][adj_pos] = 1

            # Square to the right
            adj_pos = vertex + 1
            if adj_pos // self.vertex_across == vertex // self.vertex_across:  # Is on the same row
                self.matrix[vertex][adj_pos] = 1

            # Square above
            adj_pos = vertex - self.vertex_across
            if 0 <= adj_pos:  # Is a valid square
                self.matrix[vertex][adj_pos] = 1

            # Square below
            adj_pos = vertex + self.vertex_across
            if adj_pos < self.vertex_total:  # Is a valid square
                self.matrix[vertex][adj_pos] = 1

    def __str__(self) -> None:  # To output matrix to console
        # Header row
        output = '\n\t|\t'
        for header in range(self.vertex_total):
            output += str(header) + '\t'

        # Separator row
        output += '\n' + ('-' * 4 * (self.vertex_total + 2)) + '\n'

        # Matrix data rows
        for row, row_number in zip(self.matrix, range(self.vertex_total)):
            output += str(row_number) + '\t|\t'
            for element in row:
                if element == 1:
                    output += str(element) + '\t'
                else:
                    output += '\t'
            output += '\n'

        return output

    def random_prims(self) -> None:
        # The algorithm is based of the Prim's for an adjacency matrix, but chooses
        # a random vertex coming from an already visited vertex instead of choosing
        # based on edge weights. Unfortunately, the algorithm has a time complexity
        # of O(V^2) even though Prim's is supposed to have O(E log V)

        # Starts at vertex 0
        visited_vertices = [0]
        self.matrix[0] = [0] * self.vertex_total

        # Keeps adding edges until every vertex has been visited
        self.edge_list = []  # Tuples in form (from, to)
        for count in range(self.vertex_total - 1):
            available_vertices = []
            # Single line nested for loop approximately halves execution time
            [[available_vertices.append((row, column)) if self.matrix[row][column] == 1 else
              None for row in range(self.vertex_total)] for column in visited_vertices]

            # Randomly chose an edge to add
            chosen_edge = random.choice(available_vertices)
            self.edge_list.append(chosen_edge)

            # Clear the row corresponding to the 'to' vertex
            self.matrix[chosen_edge[0]] = [0] * self.vertex_total
            visited_vertices.append(chosen_edge[0])


class Game:
    def __init__(self, difficulty: int) -> None:
        # Define size and number of squares in the maze
        self.squares_across = difficulty
        self.squares_total = self.squares_across ** 2
        self.base_square = WIN_WIDTH / self.squares_across  # Distance between base squares
        self.small_square = self.base_square / 2  # Distance between path squares
        self.offset = -self.small_square / 2  # Offset to centre entire maze

        # Number that when added to square index give index of adjacent squares
        self.matrix_offset_list = [-self.squares_total, self.squares_total, -1, 1]  # Up, Down, Left, Right

        # Creates a randomised spanning tree to be the maze
        self.matrix = AdjacencyMatrix(self)
        self.matrix.random_prims()

        # Creates the grid using the matrix
        self.create_grid(self.matrix.edge_list)

        # Creates player object
        player_width = self.small_square / 4
        self.player_velocity = 7 * self.small_square  # Player velocity is relative to grid size
        self.player = Player(self.path_squares[0].x + (self.small_square - player_width) / 2,
                             self.path_squares[0].y + (self.small_square - player_width) / 2,
                             player_width,
                             self.player_velocity)

        # Time the player starts the maze
        self.start_time = perf_counter()

        # Declaring attributes for later
        self.run, self.won, self.to_menu = True, False, False

    def create_grid(self, edge_list: list) -> None:
        # Creates a grid of base squares that are the same in every maze
        self.path_squares = []
        path_colour = COLOUR['Black']
        row, column = 0, 0
        for base_square in range(self.squares_total):
            if column == self.squares_across:
                column = 0
                row += 1
            self.path_squares.append(Square(self,
                                            row * self.base_square + self.small_square,
                                            column * self.base_square + self.small_square,
                                            path_colour))
            column += 1

        # Specifies end winning square
        self.path_squares[-1].colour = COLOUR['Green']
        self.end_square = self.path_squares[-1]

        # Joins base squares as specified by randomly generated matrix to make maze path
        for edge in edge_list:
            path_square_x = 0.5 * (self.path_squares[edge[0]].x + self.path_squares[edge[1]].x)
            path_square_y = 0.5 * (self.path_squares[edge[0]].y + self.path_squares[edge[1]].y)

            self.path_squares.append(Square(self, path_square_x, path_square_y, path_colour))

    def game_loop(self) -> None:
        # Set starting variables
        self.time_last = perf_counter()
        self.run = True
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        # Loops until player reaching the end of the maze
        while self.run:
            # Set frame rate cap of ~66fps
            pygame.time.delay(15)
            self.get_delta_time()

            # Skips exceptionally long frame times
            if self.delta_time > 0.06:
                continue

            # Allows 'X' button to close game
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.run = False

            # Gets a list of all the keys pressed in that tick
            keys = pygame.key.get_pressed()

            # [Q] goes back to main menu
            if keys[pygame.K_q]:
                self.to_menu = True
                self.run = False
            # [R] restart level with same maze
            if keys[pygame.K_r]:
                self.back_to_start()

            # Player movement
            movement_vector = pygame.math.Vector2()
            if keys[pygame.K_w]:  # Up
                movement_vector.y -= 1
            if keys[pygame.K_s]:  # Down
                movement_vector.y += 1
            if keys[pygame.K_d]:  # Right
                movement_vector.x += 1
            if keys[pygame.K_a]:  # Left
                movement_vector.x -= 1
            self.player.move(self, movement_vector)

            # Checks if player is in the end square
            if self.end_square.rect.contains(self.player.rect):
                self.won = True
                self.run = False

            # Draws the frame
            win.fill(COLOUR['Red'])
            self.draw_path()
            self.player.draw(self)
            pygame.display.update()

        # Stops game timer
        self.time_taken = perf_counter() - self.start_time

    def back_to_start(self) -> None:
        # Recreates player object at start of maze
        del self.player
        player_width = self.small_square / 4
        self.player = Player(self.path_squares[0].x + (self.small_square - player_width) / 2,
                             self.path_squares[0].y + (self.small_square - player_width) / 2,
                             player_width,
                             self.player_velocity)

        # Restart timer
        self.start_time = perf_counter()

    def draw_path(self) -> None:
        for square in self.path_squares:
            square.draw(self)

    def get_delta_time(self) -> None:
        # Elapsed time since last frame
        self.time_now = perf_counter()
        self.delta_time = self.time_now - self.time_last
        self.time_last = self.time_now


class Menu:
    def __init__(self):
        # Creates the sections of the main menu screen
        self.create_title('Maze Game')
        self.create_buttons()
        self.create_controls()

        # Initialising attributes for later
        self.exit, self.run_game = False, False

    def create_buttons(self) -> None:
        # Center point for start of button cluster
        self.button_origin_x = WIN_WIDTH // 2
        self.button_origin_y = WIN_WIDTH // 2.1

        # Creates a rect for each button, used for blit and collisions
        self.button_offset = MAIN_FONT.get_height() * 2
        self.rect_list = []
        difficulties_list = list(DIFFICULTY.keys())
        for difficulty in range(len(DIFFICULTY)):
            rect = MAIN_FONT.render(difficulties_list[difficulty], True, COLOUR['White']).get_rect()
            rect.center = (self.button_origin_x, self.button_origin_y + (difficulty * self.button_offset))
            self.rect_list.append(rect)

    def create_title(self, text: str) -> None:
        self.txt_title = TITLE_FONT.render(text, True, COLOUR['White'], COLOUR['Black'])
        self.rect_title = self.txt_title.get_rect()
        self.rect_title.center = (WIN_WIDTH // 2, WIN_WIDTH // 4)

    def create_controls(self):
        self.controls = []
        control_offset = CONTROLS_FONT.get_height()
        for control_index in range(len(CONTROLS)):
            text = CONTROLS_FONT.render(CONTROLS[control_index], True, COLOUR['White'], COLOUR['Black'])
            rect = text.get_rect()
            rect.bottomleft = (control_offset, WIN_WIDTH - (2 * control_offset * control_index) - control_offset)
            self.controls.append([text, rect])

    def display_loop(self) -> None:
        while not (self.exit or self.run_game):
            # Set frame rate cap of ~66fps
            pygame.time.delay(15)

            # Gets mouse pos and state
            self.mouse_pos = pygame.mouse.get_pos()
            self.mouse_click = False
            self.mouse_hovering = False

            for event in pygame.event.get():
                # Allows 'X' button to close game
                if event.type == pygame.QUIT:
                    self.exit = True
                # Registers mouse click
                if event.type == pygame.MOUSEBUTTONUP:
                    self.mouse_click = True

            # Clears the screen
            win.fill(COLOUR['Black'])

            # Displays all the buttons, detects mouse overs and clicks
            for difficulty_index in range(len(DIFFICULTY)):
                self.display_button(difficulty_index, self.rect_list[difficulty_index])

            # Draws rest of frame
            win.blit(self.txt_title, self.rect_title)
            for control in self.controls:
                win.blit(control[0], control[1])
            pygame.display.update()

            # Cursor charge to prompt user to click
            if self.mouse_hovering:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            else:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        # 'Loading' cursor while maze generates
        if self.run_game:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_WAIT)

    def display_button(self, difficulty_index: int, rect: pygame.Rect) -> None:
        # Name of the difficulty
        difficulty_str = list(DIFFICULTY.keys())[difficulty_index]

        # Detects mouse over and clicking button
        if rect.collidepoint(self.mouse_pos):
            self.mouse_hovering = True
            text = MAIN_FONT.render(difficulty_str, True, COLOUR['Red'], COLOUR['Black'])
            rect = text.get_rect()
            rect.center = (self.button_origin_x, self.button_origin_y + (difficulty_index * self.button_offset))
            pygame.draw.rect(win, COLOUR['Red'], rect, 10)
            win.blit(text, rect)

            # Set difficulty to button currently hovering over
            if self.mouse_click:
                self.difficulty = DIFFICULTY[difficulty_str]
                self.run_game = True

        else:
            # Normal button render
            text = MAIN_FONT.render(difficulty_str, True, COLOUR['White'], COLOUR['Black'])
            rect = text.get_rect()
            rect.center = (self.button_origin_x, self.button_origin_y + (difficulty_index * self.button_offset))
            win.blit(text, rect)


class EndScreen(Menu):
    def __init__(self, time: float) -> None:
        # Inherit the rest of __init__ from parent
        super().__init__()

        # Only change is the text in the title
        self.create_title(f'{round(time, 2)}s')


class Player:
    def __init__(self, x: float, y: float, width: float, velocity: float) -> None:
        self.pos = (x, y)
        self.colour = COLOUR['White']
        self.width = width
        self.collide_margin = 1  # Hit box is slightly smaller than player
        self.velocity = velocity
        self.rect = pygame.Rect(self.pos, (self.width, self.width))

    def update_player_rect(self, coordinate: tuple) -> None:
        self.rect = pygame.Rect(coordinate, (self.width, self.width))

    def draw(self, game: Game) -> None:
        # Moved same offset as square grid to center maze
        pygame.draw.rect(win, self.colour, self.rect.move(game.offset, game.offset))

    def move(self, game: Game, movement_vector: pygame.math.Vector2) -> None:
        # Normalise vector to stop diagonal movement being faster
        if not (movement_vector.magnitude() == 0 or movement_vector.magnitude() == 1):
            movement_vector.normalize_ip()

        # Projected position calculated to see if it would put the player off the path
        next_x = self.pos[0] + (movement_vector.x * self.velocity * game.delta_time)
        next_y = self.pos[1] + (movement_vector.y * self.velocity * game.delta_time)
        corners_for_x = self.gen_corners((next_x, self.pos[1]))
        corners_for_y = self.gen_corners((self.pos[0], next_y))

        # List is all True if the player stays on the path
        on_path_for_x = [False, False, False, False]
        on_path_for_y = [False, False, False, False]
        x_complete, y_complete = False, False

        # Check if corners are on the path
        for path_square in game.path_squares:
            for corner in range(4):
                # No need to do collisions, if all points have been verified
                if not x_complete:
                    # When a corner is on the path
                    if path_square.rect.collidepoint(corners_for_x[corner]):
                        on_path_for_x[corner] = True
                    # When the entire player is on the path
                    if on_path_for_x == [True, True, True, True]:
                        x_complete = True

                # No need to do collisions, if all points have been verified
                if not y_complete:
                    # When a corner is on the path
                    if path_square.rect.collidepoint(corners_for_y[corner]):
                        on_path_for_y[corner] = True
                    # When the entire player is on the path
                    if on_path_for_y == [True, True, True, True]:
                        y_complete = True

        # If no collision from x movement, finalise x plane
        if x_complete:
            self.pos = (next_x, self.pos[1])
        # If no collision from y movement, finalise y plane
        if y_complete:
            self.pos = (self.pos[0], next_y)

        self.update_player_rect(self.pos)

    def gen_corners(self, coordinate: tuple) -> list:
        top_right = (coordinate[0] + self.collide_margin, coordinate[1] + self.collide_margin)
        top_left = (coordinate[0] + self.width - self.collide_margin, coordinate[1] + self.collide_margin)
        bot_left = (coordinate[0] + self.collide_margin, coordinate[1] + self.width - self.collide_margin)
        bot_right = (coordinate[0] + self.width - self.collide_margin, coordinate[1] + self.width - self.collide_margin)
        return [top_left, top_right, bot_left, bot_right]


def main() -> None:
    # To break the main while loop
    exit_program = False

    # Shows main menu to choose maze size
    menu = Menu()
    menu.display_loop()
    # When 'X' is pressed
    if menu.exit:
        exit_program = True
    else:
        difficulty = menu.difficulty
    del menu

    # Keeps doing more mazes until exit
    while not exit_program:
        # Creates Game object with random maze
        game = Game(difficulty)
        game.game_loop()

        if game.won:  # When maze completed
            # Shows end screen with completion time
            end_screen = EndScreen(game.time_taken)
            end_screen.display_loop()

            # When 'X' is pressed
            if end_screen.exit:
                exit_program = True
            else:
                difficulty = end_screen.difficulty
            del end_screen

        elif game.to_menu:  # When [Q] key pressed
            # Goes back to main menu
            menu = Menu()
            menu.display_loop()

            # When 'X' is pressed
            if menu.exit:
                exit_program = True
            else:
                difficulty = menu.difficulty
            del menu

        else:  # When 'X' button pressed
            break

    # Graceful exit
    pygame.display.quit()
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
