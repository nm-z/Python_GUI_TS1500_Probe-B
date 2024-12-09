import os
import pygame
import tkinter as tk

class TiltIndicator:
    def __init__(self, canvas):
        self.canvas = canvas
        self.width = 400
        self.height = 400
        self.setup_pygame()
        
    def setup_pygame(self):
        self.canvas.update()
        os.environ['SDL_WINDOWID'] = str(self.canvas.winfo_id())
        
        if not pygame.get_init():
            pygame.init()
        pygame.display.init()
        
        # Set up the display with exact size match
        self.surface = pygame.display.set_mode(
            (self.width, self.height),
            pygame.NOFRAME | pygame.SCALED | pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        
        pygame.event.set_blocked(None)
        self.canvas.update()
        
    def update(self, pitch, roll):
        try:
            # Import draw_attitude_indicator from tilt_indicator module
            from tilt_indicator import draw_attitude_indicator
            draw_attitude_indicator(pitch, roll, self.surface)
            pygame.display.flip()
        except Exception as e:
            print(f"Error updating tilt indicator: {e}")
    
    def cleanup(self):
        try:
            pygame.quit()
        except Exception:
            pass

    def resize(self, width, height):
        self.width = width
        self.height = height
        self.surface = pygame.display.set_mode(
            (width, height),
            pygame.NOFRAME | pygame.SCALED | pygame.HWSURFACE | pygame.DOUBLEBUF
        ) 