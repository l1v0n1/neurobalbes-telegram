import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
import aiohttp
import aiofiles
import asyncio

class Demotivator:
    def __init__(self, top_text='', bottom_text=''):
        self._top_text = top_text
        self._bottom_text = bottom_text

    async def _download_image(self, url, local_path):
        """
        Загружает изображение асинхронно.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(local_path, 'wb') as out_file:
                        await out_file.write(await response.read())

    async def create(self, folder_name: str, avatar_name: str, result_filename: str, watermark=None, font_color='white', 
                     fill_color='black', font_name='Impact.ttf', top_size=80, bottom_size=60,
                     arrange=False, use_url=False) -> bool:
        """
        Создает демотиватор с именем файла, основанным на переданном параметре `result_filename`.
        
        :param folder_name: Папка для сохранения файла и загрузки изображения.
        :param avatar_name: Имя изображения, которое будет использовано.
        :param result_filename: Имя итогового файла.
        :param watermark: Текст водяного знака, если None, то не будет добавлен.
        :param font_color: Цвет шрифта.
        :param fill_color: Цвет фона.
        :param font_name: Путь к файлу шрифта.
        :param top_size: Размер шрифта для верхнего текста.
        :param bottom_size: Размер шрифта для нижнего текста.
        :param arrange: True, если фотография должна быть вставлена в рамку.
        :param use_url: True, если `avatar_name` - это URL.
        :return: True, если метод выполнен успешно.
        """
        # Путь к изображению (если это локальный файл или URL)
        avatar_path = os.path.join(folder_name, avatar_name)

        # Если используется URL, скачиваем изображение
        if use_url:
            local_file = os.path.join(folder_name, 'downloaded_image.jpg')
            await self._download_image(avatar_name, local_file)
            avatar_path = local_file  # Теперь используем локальный путь

        # Загружаем изображение
        user_img = Image.open(avatar_path).convert("RGBA")
        (width, height) = user_img.size
        
        # Создаем изображение для демотиватора с рамкой
        if arrange:
            img = Image.new('RGB', (width + 250, height + 260), color=fill_color)
            img_border = Image.new('RGB', (width + 10, height + 10), color='#000000')
            border = ImageOps.expand(img_border, border=2, fill='#ffffff')
            img.paste(border, (111, 96))
            img.paste(user_img, (118, 103))
            drawer = ImageDraw.Draw(img)
        else:
            img = Image.new('RGB', (1280, 1024), color=fill_color)
            img_border = Image.new('RGB', (1060, 720), color='#000000')
            border = ImageOps.expand(img_border, border=2, fill='#ffffff')
            user_img = user_img.resize((1050, 710))
            (width, height) = user_img.size
            img.paste(border, (111, 96))
            img.paste(user_img, (118, 103))
            drawer = ImageDraw.Draw(img)

        # Работа с шрифтами и текстом
        font_1 = ImageFont.truetype(font=os.path.join(os.path.dirname(__file__), font_name), size=top_size, encoding='UTF-8')
        text_bbox = font_1.getbbox(self._top_text)
        text_width = text_bbox[2] - text_bbox[0]

        while text_width >= (width + 250) - 20:
            font_1 = ImageFont.truetype(font=os.path.join(os.path.dirname(__file__), font_name), size=top_size, encoding='UTF-8')
            text_bbox = font_1.getbbox(self._top_text)
            text_width = text_bbox[2] - text_bbox[0]
            top_size -= 1

        font_2 = ImageFont.truetype(font=os.path.join(os.path.dirname(__file__), font_name), size=bottom_size, encoding='UTF-8')
        text_bbox = font_2.getbbox(self._bottom_text)
        text_width = text_bbox[2] - text_bbox[0]

        while text_width >= (width + 250) - 20:
            font_2 = ImageFont.truetype(font=os.path.join(os.path.dirname(__file__), font_name), size=bottom_size, encoding='UTF-8')
            text_bbox = font_2.getbbox(self._bottom_text)
            text_width = text_bbox[2] - text_bbox[0]
            bottom_size -= 1

        size_1_bbox = drawer.textbbox((0, 0), self._top_text, font=font_1)
        size_1 = (size_1_bbox[2] - size_1_bbox[0], size_1_bbox[3] - size_1_bbox[1])
        
        size_2_bbox = drawer.textbbox((0, 0), self._bottom_text, font=font_2)
        size_2 = (size_2_bbox[2] - size_2_bbox[0], size_2_bbox[3] - size_2_bbox[1])

        if arrange:
            drawer.text((((width + 250) - size_1[0]) / 2, ((height + 190) - size_1[1])),
                        self._top_text, fill=font_color,
                        font=font_1)
            drawer.text((((width + 250) - size_2[0]) / 2, ((height + 235) - size_2[1])),
                        self._bottom_text, fill=font_color,
                        font=font_2)
        else:
            drawer.text(((1280 - size_1[0]) / 2, 840), self._top_text, fill=font_color, font=font_1)
            drawer.text(((1280 - size_2[0]) / 2, 930), self._bottom_text, fill=font_color, font=font_2)

        # Добавление водяного знака, если нужно
        if watermark is not None:
            (width, height) = img.size
            idraw = ImageDraw.Draw(img)
            idraw.line((1000 - len(watermark) * 5, 817, 1008 + len(watermark) * 5, 817), fill=0, width=4)

            font_2 = ImageFont.truetype(font=os.path.join(os.path.dirname(__file__), font_name), size=20, encoding='UTF-8')
            size_2_bbox = idraw.textbbox((0, 0), watermark.lower(), font=font_2)
            size_2 = (size_2_bbox[2] - size_2_bbox[0], size_2_bbox[3] - size_2_bbox[1])
            idraw.text((((width + 729) - size_2[0]) / 2, ((height - 192) - size_2[1])),
                       watermark.lower(), font=font_2)

        # Сохраняем результат
        result_filename = f"{result_filename}_dem.jpg"
        result_filepath = os.path.join(folder_name, result_filename)
        img.save(result_filepath)

        # Удаляем файл, если он был загружен по URL
        if use_url:
            os.remove(avatar_path)

        return True
