import os
from PIL import Image, ImageDraw, ImageFont
import asyncio

class TextImage:
    def __init__(self, folder, text, filename, text_color=(0, 0, 0), bg_color=(255, 255, 255), font_name="Formular-BlackItalic.ttf", max_width=1080, max_height=1080, padding=10):
        self.folder = folder  # Папка для сохранения изображения
        self.text = text
        self.filename = filename
        self.text_color = text_color
        self.bg_color = bg_color
        
        # Более надежный способ получения пути к шрифту
        font_dir = os.path.dirname(os.path.abspath(__file__))
        self.font_path = os.path.join(font_dir, font_name)
        
        # Проверяем существование файла шрифта
        if not os.path.exists(self.font_path):
            raise FileNotFoundError(f"Font file not found: {self.font_path}")
            
        self.max_width = max_width
        self.max_height = max_height
        self.padding = padding

    async def create_image_with_text(self):
        font_size = 100
        font = ImageFont.truetype(self.font_path, font_size)

        def wrap_text(text, font, max_width):
            lines = []
            words = text.split()
            line = ""

            for word in words:
                test_line = f"{line} {word}".strip()
                bbox = font.getbbox(test_line)
                line_width = bbox[2] - bbox[0]

                if line_width <= max_width - 2 * self.padding:
                    line = test_line
                else:
                    lines.append(line)
                    line = word

            if line:
                lines.append(line)

            return lines

        while font_size > 10:
            font = ImageFont.truetype(self.font_path, font_size)

            paragraphs = self.text.strip().split("\n")
            wrapped_text = []
            for paragraph in paragraphs:
                wrapped_text.extend(wrap_text(paragraph, font, self.max_width))
                wrapped_text.append("")

            text_height = 0
            for line in wrapped_text:
                if line:
                    bbox = font.getbbox(line)
                    text_height += (bbox[3] - bbox[1]) + 5
                else:
                    text_height += 5

            if text_height <= self.max_height - 2 * self.padding:
                break
            font_size -= 2

        actual_height = min(text_height + 2 * self.padding + 10, self.max_height)

        img = Image.new('RGB', (self.max_width, actual_height), color=self.bg_color)
        draw = ImageDraw.Draw(img)

        y_offset = self.padding
        for line in wrapped_text:
            if line:
                draw.text((self.padding, y_offset), line, font=font, fill=self.text_color)
                bbox = font.getbbox(line)
                line_height = bbox[3] - bbox[1]
                y_offset += line_height + 5
            else:
                y_offset += 5

        # Убедимся, что указанная папка существует
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

        save_path = os.path.join(self.folder, f"{self.filename}.png")
        
        # Сохранение изображения синхронно
        img.save(save_path)

        return True