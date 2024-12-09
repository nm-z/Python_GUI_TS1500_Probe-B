from PIL import Image, ImageDraw, ImageFont
import os
from typing import Tuple, Dict, Optional

def create_icon(
    name: str,
    text: str,
    size: Tuple[int, int] = (48, 48),
    bg_color: Tuple[int, int, int] = (48, 48, 48),
    fg_color: Tuple[int, int, int] = (255, 255, 255),
    border_radius: int = 8,
    border_color: Optional[Tuple[int, int, int]] = None,
    border_width: int = 2,
    font_size: int = 24,
    style: str = 'flat'  # 'flat', 'rounded', 'circle', 'square'
) -> None:
    """
    Create a visually appealing icon with text and styling options.
    
    Args:
        name: Icon filename without extension
        text: Text to display on the icon
        size: Icon dimensions (width, height)
        bg_color: Background color in RGB
        fg_color: Foreground (text) color in RGB
        border_radius: Radius for rounded corners
        border_color: Border color in RGB, None for no border
        border_width: Border width in pixels
        font_size: Font size in points
        style: Icon style ('flat', 'rounded', 'circle', 'square')
    """
    # Create new image with alpha channel (RGBA)
    image = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Use full size for shape with minimal border space
    shape_bounds = [0, 0, size[0]-1, size[1]-1]
    
    # Create base shape based on style
    if style == 'circle':
        # Draw circle
        draw.ellipse(shape_bounds, fill=bg_color)
        if border_color:
            draw.ellipse(shape_bounds, outline=border_color, width=border_width)
    elif style == 'rounded':
        # Draw rounded rectangle
        draw.rounded_rectangle(shape_bounds, border_radius, fill=bg_color)
        if border_color:
            draw.rounded_rectangle(shape_bounds, border_radius, outline=border_color, width=border_width)
    else:  # 'flat' or 'square'
        # Draw rectangle
        draw.rectangle(shape_bounds, fill=bg_color)
        if border_color and style == 'square':
            draw.rectangle(shape_bounds, outline=border_color, width=border_width)
    
    # Try to load a bold font, fall back to regular if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # Get text size
    text = text[0].upper()  # Use first letter, uppercase
    text_width = draw.textlength(text, font=font)
    text_height = font_size  # Approximate height
    
    # Calculate text position for center alignment
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2 - 2  # Slight upward adjustment
    
    # Draw text with slight shadow for depth
    if style != 'flat':
        # Add subtle shadow
        shadow_offset = 2
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 64))
    
    # Draw main text
    draw.text((x, y), text, font=font, fill=fg_color)
    
    # Save image
    if not os.path.exists('icons'):
        os.makedirs('icons')
    image.save(f'icons/{name}.png')

def get_icon_styles() -> Dict[str, dict]:
    """Define styles for different icon categories"""
    return {
        'file': {
            'style': 'rounded',
            'bg_color': (65, 105, 225),  # Royal Blue
            'border_color': (30, 70, 190)
        },
        'control': {
            'style': 'circle',
            'bg_color': (46, 139, 87),  # Sea Green
            'border_color': (25, 100, 60)
        },
        'view': {
            'style': 'square',
            'bg_color': (147, 112, 219),  # Medium Purple
            'border_color': (110, 80, 190)
        },
        'settings': {
            'style': 'rounded',
            'bg_color': (210, 105, 30),  # Chocolate
            'border_color': (170, 80, 20)
        },
        'tools': {
            'style': 'square',
            'bg_color': (128, 128, 128),  # Gray
            'border_color': (90, 90, 90)
        },
        'help': {
            'style': 'circle',
            'bg_color': (70, 130, 180),  # Steel Blue
            'border_color': (50, 100, 150)
        }
    }

def main():
    """Generate all required icons with appropriate styles"""
    icons = {
        # File Management
        'open': ('Open', 'file'),
        'save': ('Save', 'file'),
        'export': ('Export', 'file'),
        
        # Control
        'start': ('Start', 'control'),
        'pause': ('Pause', 'control'),
        'stop': ('Stop', 'control'),
        
        # View
        'logs': ('Logs', 'view'),
        'plots': ('Plots', 'view'),
        'tilt': ('Tilt', 'view'),
        
        # Settings
        'hardware': ('Hardware', 'settings'),
        'params': ('Parameters', 'settings'),
        'backup': ('Backup', 'settings'),
        
        # Tools
        'upload': ('Upload', 'tools'),
        'sync': ('Sync', 'tools'),
        'reset': ('Reset', 'tools'),
        
        # Help
        'help': ('Help', 'help'),
        'components': ('Components', 'help'),
        'issue': ('Issue', 'help')
    }
    
    styles = get_icon_styles()
    
    for name, (text, category) in icons.items():
        style = styles[category]
        create_icon(
            name,
            text,
            style=style['style'],
            bg_color=style['bg_color'],
            border_color=style['border_color']
        )
        print(f"Created icon: {name}.png with {category} style")

if __name__ == "__main__":
    main() 