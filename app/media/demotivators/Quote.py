from PIL import Image, ImageDraw, ImageFont
import textwrap
import requests
import os
import sys
import logging

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
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
            '/System/Library/Fonts/Times.ttc',
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


class Quote:
    def __init__(self, text="", author=""):
        self.text = text
        self.author = author
        
    def create(self, image_path, watermark=None, result_filename=None, use_url=False):
        try:
            # Handle URL images
            if use_url:
                response = requests.get(image_path)
                temp_file = "temp_quote_image.jpg"
                with open(temp_file, "wb") as f:
                    f.write(response.content)
                image_path = temp_file
            
            # Validate input image
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Input image not found: {image_path}")
            
            # Open and validate input image
            img = Image.open(image_path)
            img.load()  # This will raise an error if image is invalid
            logging.info(f"Successfully opened input image: {image_path}, size: {img.size}")
            
            # Create drawing context
            draw = ImageDraw.Draw(img)
            
            # Calculate font size based on image width
            base_font_size = int(img.width * 0.1)  # 10% of image width
            base_font_size = max(60, min(base_font_size, 100))  # Between 60 and 100
            watermark_size = int(base_font_size * 0.3)  # 30% of main font size
            
            # Load fonts using get_font helper
            main_font = get_font('Times.ttc', base_font_size)
            watermark_font = get_font('Times.ttc', watermark_size)
            
            # Calculate text position
            text_x = img.width // 2
            text_y = img.height - 100
            
            # Add text
            draw.text((text_x, text_y), self.text, 
                     font=main_font, fill='black', anchor='mt')
            if self.author:
                draw.text((text_x, text_y + 40), f"- {self.author}", 
                         font=main_font, fill='black', anchor='mt')
            
            # Add watermark if provided
            if watermark:
                draw.text((10, img.height-25), f"@{watermark}", 
                         font=watermark_font, fill='black')
            
            # Save result
            if not result_filename:
                result_filename = "quote_result.jpg"
            img.save(result_filename, quality=95)
            logging.info(f"Successfully saved quote to: {result_filename}")
            
            # Clean up temporary file if used
            if use_url and os.path.exists(temp_file):
                os.remove(temp_file)
                
        except Exception as e:
            logging.error(f"Error creating quote: {e}")
            raise
