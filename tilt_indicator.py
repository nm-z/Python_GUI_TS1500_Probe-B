import pygame  # type: ignore
import os

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 1000, 1000

# Colors
BLUE = (0, 153, 255)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Load Ubuntu Light font
try:
    font_path = "/usr/share/fonts/truetype/ubuntu/Ubuntu-Light.ttf"
    if not os.path.exists(font_path):
        font_path = "Ubuntu-Light.ttf"  # Fallback to local directory
    FONT = pygame.font.Font(font_path, 54)
except:
    FONT = pygame.font.Font(None, 54)  # Fallback to default font


# Function to draw the attitude indicator
def draw_attitude_indicator(pitch, roll, surface=None):
    if surface is None:
        surface = pygame.display.get_surface()
    surface.fill(BLACK)

    # Get current screen size dynamically
    WIDTH, HEIGHT = surface.get_size()
    
    # Calculate exact center with slight downward adjustment
    center_x = WIDTH // 2.6
    center_y = (HEIGHT // 2) + (HEIGHT * 0.1)  # Move down by 5% of height

    # Create a larger surface to draw the horizon
    horizon_surface = pygame.Surface((WIDTH * 2, HEIGHT * 2))
    horizon_surface.fill(BLACK)

    # Draw sky and ground with adjusted center point
    horizon_height = HEIGHT + (pitch * HEIGHT / 90)  # Adjust for pitch
    pygame.draw.rect(horizon_surface, BLUE, (0, 0, WIDTH * 2, horizon_height))
    pygame.draw.rect(horizon_surface, BLACK, (0, horizon_height, WIDTH * 2, HEIGHT * 2 - horizon_height))

    # Rotate the horizon surface based on the roll angle
    rotated_horizon = pygame.transform.rotate(horizon_surface, -roll)
    
    # Center the rotated surface precisely
    horizon_rect = rotated_horizon.get_rect(center=(center_x, center_y))
    surface.blit(rotated_horizon, horizon_rect.topleft)

    # Draw the reference lines with adjusted positioning
    line_length = WIDTH / 8
    gap_size = WIDTH / 6

    # Left line
    pygame.draw.line(
        surface,
        WHITE,
        (center_x - line_length - gap_size, center_y),
        (center_x - gap_size, center_y),
        2,
    )

    # Right line
    pygame.draw.line(
        surface,
        WHITE,
        (center_x + gap_size, center_y),
        (center_x + line_length + gap_size, center_y),
        2,
    )

    # Display roll angle at the same adjusted center point
    roll_text = FONT.render(f"{int(roll)}°", True, WHITE)
    text_rect = roll_text.get_rect()
    text_rect.center = (center_x, center_y)
    surface.blit(roll_text, text_rect)


# Main loop
def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    running = True
    roll = 0  # Initial roll value

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Simulate roll changes
        roll = (roll + 1) % 360

        # Draw the attitude indicator
        draw_attitude_indicator(0, roll, screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
