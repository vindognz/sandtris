import pygame
import random

pygame.init()

# Constants
WIDTH, HEIGHT = 300, 600
BLOCK_SIZE = 20
GRID_WIDTH = WIDTH // BLOCK_SIZE
GRID_HEIGHT = HEIGHT // BLOCK_SIZE
GRAIN_SIZE = 2  # 2x2 pixels per grain
GRAINS_PER_BLOCK = BLOCK_SIZE // GRAIN_SIZE  # 10 grains per block
GRAIN_GRID_WIDTH = GRID_WIDTH * GRAINS_PER_BLOCK
GRAIN_GRID_HEIGHT = GRID_HEIGHT * GRAINS_PER_BLOCK
FPS = 60

# Colors
BLACK = (0, 0, 0)
GRAY = (40, 40, 40)
WHITE = (255, 255, 255)

# 4 color palette
COLORS = [
    (210, 50, 50),  # Red
    #(255, 150, 0), # Orange
    (100, 150, 255), # Blue
    (100, 255, 150), # Green
    (255, 220, 100), # Yellow
    #(128, 0, 128),   # Purple
]

# Tetromino shapes
SHAPES = {
    'I': {'shape': [[1, 1, 1, 1]]},
    'O': {'shape': [[1, 1], [1, 1]]},
    'T': {'shape': [[1, 1, 1], [0, 1, 0]]},
    'S': {'shape': [[0, 1, 1], [1, 1, 0]]},
    'Z': {'shape': [[1, 1, 0], [0, 1, 1]]},
    'J': {'shape': [[1, 1, 1], [0, 0, 1]]},
    'L': {'shape': [[1, 1, 1], [1, 0, 0]]},
}


def makeBag():
    bag = list(SHAPES.keys())
    random.shuffle(bag)
    return bag


def rotateTable(table):
    return [[*r][::-1] for r in zip(*table)]


class Piece:
    def __init__(self, shape_id):
        self.id = shape_id
        self.shape = SHAPES[shape_id]['shape']
        self.color = random.choice(COLORS)
        self.x = GRID_WIDTH // 2 - len(self.shape[0]) // 2
        self.y = 0

    def getBlocks(self):
        blocks = []
        for row_idx, row in enumerate(self.shape):
            for col_idx, cell in enumerate(row):
                if cell:
                    blocks.append((self.x + col_idx, self.y + row_idx))
        return blocks

    def rotate(self):
        self.shape = rotateTable(self.shape)


class SandGrain:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = tuple(max(0, min(255, c + random.randint(-15, 15))) for c in color)


class ClearParticle:
    def __init__(self, x, y, color):
        self.x = x * GRAIN_SIZE + GRAIN_SIZE // 2
        self.y = y * GRAIN_SIZE + GRAIN_SIZE // 2
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-6, -2)
        self.color = color
        self.life = 40
        self.size = random.randint(3, 6)
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3
        self.life -= 1
        return self.life > 0
    
    def draw(self, surface):
        alpha = int(255 * (self.life / 40))
        particle_surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        color_with_alpha = (*self.color, alpha)
        pygame.draw.circle(particle_surface, color_with_alpha, (self.size // 2, self.size // 2), self.size // 2)
        surface.blit(particle_surface, (int(self.x) - self.size // 2, int(self.y) - self.size // 2))


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sand Tetris")
        self.clock = pygame.time.Clock()
        # Grain-level grid
        self.grain_grid = [[None for _ in range(GRAIN_GRID_WIDTH)] for _ in range(GRAIN_GRID_HEIGHT)]
        
        self.bag = makeBag()
        self.current_piece = self.fromBag()
        self.next_piece = self.fromBag()
        
        self.drop_timer = 0
        self.drop_speed = 30
        self.move_timer = 0
        self.move_delay = 16
        self.move_repeat_delay = 6
        self.holding_input = False
        
        self.sand_update_counter = 0
        self.sand_update_speed = 1
        
        self.clearing = False
        self.clear_queue = []
        self.clear_timer = 0
        self.clear_flash_duration = 20  # Total flash frames
        self.clear_flash_count = 0
        
        self.particles = []
        self.clears = 0
        
        self.running = True
        self.game_over = False

    def fromBag(self):
        if len(self.bag) == 0:
            self.bag = makeBag()
        shape_id = self.bag.pop(0)
        return Piece(shape_id)

    def checkCollision(self, piece, offset_x=0, offset_y=0):
        for bx, by in piece.getBlocks():
            new_x, new_y = bx + offset_x, by + offset_y
            if new_x < 0 or new_x >= GRID_WIDTH or new_y >= GRID_HEIGHT:
                return True
            if new_y >= 0:
                # Check if any grain in this block position is occupied
                for gy in range(GRAINS_PER_BLOCK):
                    for gx in range(GRAINS_PER_BLOCK):
                        grain_x = new_x * GRAINS_PER_BLOCK + gx
                        grain_y = new_y * GRAINS_PER_BLOCK + gy
                        if self.grain_grid[grain_y][grain_x] is not None:
                            return True
        return False

    def getGhostY(self):
        ghost_y = self.current_piece.y
        while not self.checkCollision(self.current_piece, offset_y=ghost_y - self.current_piece.y + 1):
            ghost_y += 1
        return ghost_y

    def lockPiece(self):
        for bx, by in self.current_piece.getBlocks():
            if by >= 0:
                # Create 10x10 grains for this block
                for gy in range(GRAINS_PER_BLOCK):
                    for gx in range(GRAINS_PER_BLOCK):
                        grain_x = bx * GRAINS_PER_BLOCK + gx
                        grain_y = by * GRAINS_PER_BLOCK + gy
                        self.grain_grid[grain_y][grain_x] = SandGrain(grain_x, grain_y, self.current_piece.color)
            else:
                self.game_over = True
                return
        
        self.current_piece = self.next_piece
        self.next_piece = self.fromBag()
        
        if self.checkCollision(self.current_piece):
            self.game_over = True

    def updateSand(self):
        moved = False
        
        for y in range(GRAIN_GRID_HEIGHT - 1, -1, -1):
            for x in range(GRAIN_GRID_WIDTH):
                grain = self.grain_grid[y][x]
                if grain is None:
                    continue
                
                # Check straight down
                if y + 1 < GRAIN_GRID_HEIGHT and self.grain_grid[y + 1][x] is None:
                    self.grain_grid[y][x] = None
                    self.grain_grid[y + 1][x] = grain
                    grain.y += 1
                    moved = True
                    continue
                
                # Check diagonals
                can_left = x > 0 and y + 1 < GRAIN_GRID_HEIGHT and self.grain_grid[y + 1][x - 1] is None
                can_right = x < GRAIN_GRID_WIDTH - 1 and y + 1 < GRAIN_GRID_HEIGHT and self.grain_grid[y + 1][x + 1] is None
                
                if can_left and can_right:
                    direction = random.choice([-1, 1])
                elif can_left:
                    direction = -1
                elif can_right:
                    direction = 1
                else:
                    continue
                
                self.grain_grid[y][x] = None
                self.grain_grid[y + 1][x + direction] = grain
                grain.x += direction
                grain.y += 1
                moved = True
        
        return moved

    def findConnectedPath(self, start_x, start_y, color):
        """Find all grains connected to start position with same base color using BFS"""
        if self.grain_grid[start_y][start_x] is None:
            return []
        
        target_color = color
        visited = []
        queue = [(start_x, start_y)]
        seen = {(start_x, start_y)}
        
        while queue:
            x, y = queue.pop(0)
            visited.append((x, y))
            
            # Check all 8 directions
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) in seen:
                    continue
                if nx < 0 or nx >= GRAIN_GRID_WIDTH or ny < 0 or ny >= GRAIN_GRID_HEIGHT:
                    continue
                if self.grain_grid[ny][nx] is None:
                    continue
                # Check if base colors match (ignoring variation)
                grain_base_color = self.grain_grid[ny][nx].color
                if not self.colorsMatch(grain_base_color, target_color):
                    continue
                
                seen.add((nx, ny))
                queue.append((nx, ny))
        
        return visited
    
    def colorsMatch(self, c1, c2):
        """Check if two colors are close enough (accounting for variation)"""
        threshold = 30
        return all(abs(c1[i] - c2[i]) < threshold for i in range(3))
    
    def clearPaths(self):
        """Clear any color paths that connect left wall to right wall"""
        # Check grains on left wall
        checked_colors = set()
        for y in range(GRAIN_GRID_HEIGHT):
            if self.grain_grid[y][0] is not None:
                color = self.grain_grid[y][0].color
                # Avoid checking same color multiple times
                color_key = (color[0] // 30, color[1] // 30, color[2] // 30)
                if color_key in checked_colors:
                    continue
                checked_colors.add(color_key)
                
                connected = self.findConnectedPath(0, y, color)
                reaches_right = any(x == GRAIN_GRID_WIDTH - 1 for x, _ in connected)
                
                if reaches_right:
                    self.clearing = True
                    self.clear_queue = list(reversed(connected))
                    return True
        
        return False
    
    def updateClearAnimation(self):
        """Flash white then poof all grains"""
        if not self.clearing:
            return
        
        self.clear_timer += 1
        
        # After flashing, clear everything
        if self.clear_timer >= self.clear_flash_duration:
            for x, y in self.clear_queue:
                if self.grain_grid[y][x] is not None:
                    color = self.grain_grid[y][x].color
                    if random.random() < 0.1:  # Spawn fewer particles
                        self.particles.append(ClearParticle(x, y, color))
                self.grain_grid[y][x] = None
            
            self.clearing = False
            self.clear_timer = 0
            self.clear_queue = []
            self.clears += 1
            if self.clears % 5 == 0 and self.drop_speed > 10:
                self.drop_speed -= 2

    def handleInput(self):
        keys = pygame.key.get_pressed()
        
        if not keys[pygame.K_LEFT] and not keys[pygame.K_RIGHT]:
            self.holding_input = False
            self.move_timer = 0
        
        if keys[pygame.K_LEFT] and not keys[pygame.K_RIGHT]:
            if self.move_timer <= 0:
                if not self.checkCollision(self.current_piece, offset_x=-1):
                    self.current_piece.x -= 1
                if self.holding_input:
                    self.move_timer = self.move_repeat_delay
                else:
                    self.move_timer = self.move_delay
                self.holding_input = True
        
        if keys[pygame.K_RIGHT] and not keys[pygame.K_LEFT]:
            if self.move_timer <= 0:
                if not self.checkCollision(self.current_piece, offset_x=1):
                    self.current_piece.x += 1
                if self.holding_input:
                    self.move_timer = self.move_repeat_delay
                else:
                    self.move_timer = self.move_delay
                self.holding_input = True
        
        if keys[pygame.K_DOWN]:
            if not self.checkCollision(self.current_piece, offset_y=1):
                self.current_piece.y += 1
                self.drop_timer = 0

    def draw(self):
        self.screen.fill(BLACK)
        
        # Draw grid lines (every 10 grains = 1 block)
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                rect = pygame.Rect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                pygame.draw.rect(self.screen, GRAY, rect, 1)
        
        # Draw sand grains
        for y in range(GRAIN_GRID_HEIGHT):
            for x in range(GRAIN_GRID_WIDTH):
                if self.grain_grid[y][x] is not None:
                    grain = self.grain_grid[y][x]
                    rect = pygame.Rect(x * GRAIN_SIZE, y * GRAIN_SIZE, GRAIN_SIZE, GRAIN_SIZE)
                    pygame.draw.rect(self.screen, grain.color, rect)
        
        # Draw clear particles
        for particle in self.particles:
            particle.draw(self.screen)
        
        # Draw current piece
        if not self.game_over:
            # Draw ghost piece
            ghost_y = self.getGhostY()
            if ghost_y != self.current_piece.y:
                for x, y in self.current_piece.getBlocks():
                    ghost_draw_y = y + (ghost_y - self.current_piece.y)
                    if ghost_draw_y >= 0:
                        rect = pygame.Rect(x * BLOCK_SIZE, ghost_draw_y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                        ghost_surface = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE))
                        ghost_surface.fill(self.current_piece.color)
                        ghost_surface.set_alpha(80)
                        self.screen.blit(ghost_surface, rect)
            
            # Draw actual piece
            for x, y in self.current_piece.getBlocks():
                if y >= 0:
                    rect = pygame.Rect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                    pygame.draw.rect(self.screen, self.current_piece.color, rect)
        
        # Draw next piece preview
        preview_x = WIDTH - 100
        preview_y = 20
        font = pygame.font.Font(None, 24)
        text = font.render("NEXT", True, WHITE)
        self.screen.blit(text, (preview_x, preview_y))
        
        for row_idx, row in enumerate(self.next_piece.shape):
            for col_idx, cell in enumerate(row):
                if cell:
                    rect = pygame.Rect(
                        preview_x + col_idx * BLOCK_SIZE,
                        preview_y + 30 + row_idx * BLOCK_SIZE,
                        BLOCK_SIZE,
                        BLOCK_SIZE
                    )
                    pygame.draw.rect(self.screen, self.next_piece.color, rect)
        
        if self.game_over:
            font = pygame.font.Font(None, 48)
            text = font.render("GAME OVER", True, WHITE)
            text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            self.screen.blit(text, text_rect)
        
        pygame.display.flip()

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and not self.game_over:
                    if event.key == pygame.K_UP:
                        old_shape = self.current_piece.shape
                        self.current_piece.rotate()
                        if self.checkCollision(self.current_piece):
                            kicked = False
                            for offset in [-1, 1, -2, 2]:
                                if not self.checkCollision(self.current_piece, offset_x=offset):
                                    self.current_piece.x += offset
                                    kicked = True
                                    break
                            if not kicked:
                                self.current_piece.shape = old_shape
                    elif event.key == pygame.K_SPACE:
                        while not self.checkCollision(self.current_piece, offset_y=1):
                            self.current_piece.y += 1
                        self.lockPiece()
                        self.drop_timer = 0
                    elif event.key == pygame.K_r:
                        self.__init__()
            
            if not self.game_over:
                self.handleInput()
                
                if self.move_timer > 0:
                    self.move_timer -= 1
                
                self.particles = [p for p in self.particles if p.update()]
                
                self.updateClearAnimation()
                
                if not self.clearing:
                    self.drop_timer += 1
                    if self.drop_timer >= self.drop_speed:
                        self.drop_timer = 0
                        if not self.checkCollision(self.current_piece, offset_y=1):
                            self.current_piece.y += 1
                        else:
                            self.lockPiece()
                    
                    self.sand_update_counter += 1
                    if self.sand_update_counter >= self.sand_update_speed:
                        self.sand_update_counter = 0
                        sand_moved = self.updateSand()
                        
                        if not sand_moved:
                            self.clearPaths()
            
            self.draw()
        
        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
