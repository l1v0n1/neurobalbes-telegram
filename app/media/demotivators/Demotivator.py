from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import os
import logging
import sys
import textwrap

# Add parent directory to path to import get_font
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from app.core.bot import get_font
except ImportError:
    # Fallback implementation if bot.py can't be imported
    def get_font(font_name, size):
        """Fallback get_font implementation"""
        font_paths = [
            # Относительные пути
            os.path.join('app', 'media', 'fonts', font_name),
            os.path.join('app', 'media', 'demotivators', 'fonts', font_name),
            os.path.join('fonts', font_name),
            os.path.join('demotivators', 'fonts', font_name),
            
            # Абсолютные пути
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts', font_name),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', font_name),
            
            # Системные пути
            'app/media/fonts/times.ttf',    
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
            '/System/Library/Fonts/times.ttf',
            '/System/Library/Fonts/Arial.ttf',
            '/Library/Fonts/Times New Roman.ttf',
            '/Library/Fonts/Arial.ttf',
            'C:\\Windows\\Fonts\\times.ttf',
            'C:\\Windows\\Fonts\\arial.ttf',
            
            # Имя файла как есть
            font_name,
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    logging.info(f"Loading font from path: {path}")
                    return ImageFont.truetype(font=path, size=size, encoding='UTF-8')
                except Exception as e:
                    logging.warning(f"Failed to load font {path}: {e}")
                    continue
        
        logging.warning(f"Using default font as fallback for {font_name}")
        return ImageFont.load_default()


class Demotivator:
    def __init__(self, top_text="", bottom_text=""):
        self.top_text = top_text
        self.bottom_text = bottom_text
        
    def create(self, image_path, watermark=None, result_filename=None, delete_file=True):
        try:
            # Validate input image
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Input image not found: {image_path}")
            
            # Open and validate input image
            img = Image.open(image_path)
            img.load()  # This will raise an error if image is invalid
            logging.info(f"Successfully opened input image: {image_path}, size: {img.size}")
            
            # Calculate frame size
            frame_width = img.width + 250
            frame_height = img.height + 300
            
            # Calculate font size based on image width
            base_font_size = int(img.width * 0.15)  # 15% of image width
            base_font_size = max(80, min(base_font_size, 120))  # Between 80 and 120
            watermark_size = int(base_font_size * 0.3)  # 30% of main font size
            
            # Load fonts using get_font helper
            main_font = get_font('times.ttf', base_font_size)
            watermark_font = get_font('times.tff', watermark_size)
            
            # Calculate image position
            x = (frame_width - img.width) // 2
            y = (frame_height - img.height) // 2 - 40
            
            # Paste input image
            frame = Image.new('RGB', (frame_width, frame_height), color='black')
            frame.paste(img, (x, y))
            
            # Add white frame
            draw = ImageDraw.Draw(frame)
            draw.rectangle((x-2, y-2, x+img.width+2, y+img.height+2), outline='white')
            
            # Calculate text positions
            top_text_y = y + img.height + 20
            bottom_text_y = top_text_y + 45 if self.bottom_text else top_text_y
            
            # Add text
            draw.text((frame_width//2, top_text_y), self.top_text, 
                     font=main_font, fill='white', anchor='mt')
            if self.bottom_text:
                draw.text((frame_width//2, bottom_text_y), self.bottom_text, 
                         font=main_font, fill='white', anchor='mt')
            
            # Add watermark if provided
            if watermark:
                draw.text((10, frame_height-25), f"{watermark}", 
                         font=watermark_font, fill='white')
            
            # Save result
            if not result_filename:
                result_filename = "demresult.jpg"
            frame.save(result_filename, quality=95)
            logging.info(f"Successfully saved demotivator to: {result_filename}")
            
            # Clean up if requested
            if delete_file and os.path.exists(image_path):
                os.remove(image_path)
                
        except Exception as e:
            logging.error(f"Error creating demotivator: {e}")
            raise
