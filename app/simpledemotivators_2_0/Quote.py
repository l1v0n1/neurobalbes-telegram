import os
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import asyncio

class Quote:
    def __init__(self, quote_text, author_name):
        """
        :param quote_text: текста цитаты
        :param author_name: имя автора цитаты
        """
        self._quote_text = quote_text
        self._author_name = author_name

    async def _download_avatar(self, url, save_path):
        """
        Загружает изображение аватара по URL асинхронно.
        :param url: URL изображения
        :param save_path: путь для сохранения изображения
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(save_path, 'wb') as f:
                        f.write(await response.read())

    def _wrap_text(self, text, font, max_width):
        """
        Функция для оборачивания текста, чтобы он не выходил за пределы максимальной ширины.
        :param text: текст для оборачивания
        :param font: шрифт для текста
        :param max_width: максимальная ширина строки
        :return: список строк, которые помещаются в заданную ширину
        """
        lines = []
        words = text.split()
        line = ""

        for word in words:
            test_line = f"{line} {word}".strip()
            line_width = font.getbbox(test_line)[2]

            if line_width <= max_width:
                line = test_line
            else:
                lines.append(line)
                line = word

        if line:
            lines.append(line)

        return lines

    async def create(self, folder_name, avatar_name, result_filename, use_url=False,
                     headline_text_font='Formular-Italic.ttf', headline_text_size=100,
                     headline_text='Цитаты мудрых людей', author_name_font='PeridotDemoPE-WideExtraBoldItalic.otf',
                     author_name_size=80, quote_text_font='Formular-BlackItalic.ttf') -> bool:
        """
        Создает изображение с цитатой и сохраняет его в указанной папке

        :param folder_name: название папки, где находится аватар
        :param avatar_name: название файла с аватаром или URL для загрузки
        :param result_filename: имя итогового файла
        :param use_url: если True, то загружает фото автора по URL
        :return: True, если метод выполнился успешно
        """

        # Получаем путь к текущей директории, где находится этот файл
        base_path = os.path.dirname(__file__)

        # Формируем пути к шрифтам относительно директории этого файла
        quote_text_font_path = os.path.join(base_path, quote_text_font)
        headline_text_font_path = os.path.join(base_path, headline_text_font)
        author_name_font_path = os.path.join(base_path, author_name_font)

        # Формируем пути к файлам
        save_path = os.path.join(folder_name, result_filename + '_quote.png')

        # Создание изображения размером 1920x1080
        user_img = Image.new('RGBA', (1920, 1080), color='#000000')
        drawer = ImageDraw.Draw(user_img)

        # Устанавливаем пределы области для цитаты
        top_margin = 198
        bottom_margin = 680
        left_margin = 100
        right_margin = 100

        # Устанавливаем максимальную ширину для текста цитаты
        max_text_width = 1920 - left_margin - right_margin  # Отнимаем от ширины изображения 100 пикселей с каждой стороны для отступов

        # Начальный размер шрифта
        font_size = 200

        # Загрузка шрифта с начальным размером
        font_1 = ImageFont.truetype(font=quote_text_font_path, size=font_size, encoding='UTF-8')

        # Расчет текста цитаты с учетом максимальной ширины и уменьшения шрифта
        wrapped_quote_lines = []
        for paragraph in self._quote_text.split("\n"):
            wrapped_quote_lines.extend(self._wrap_text(paragraph, font_1, max_text_width))

        # Проверяем, помещается ли текст в заданную область
        while font_size > 10:  # Уменьшаем шрифт, пока текст не поместится
            # Вычисляем высоту текста и проверяем, помещается ли он в области цитаты
            total_height = sum(font_1.getbbox(line)[3] for line in wrapped_quote_lines) + len(wrapped_quote_lines) * 5
            if total_height <= (bottom_margin - top_margin):
                break  # Текст помещается в область, выходим из цикла
            font_size -= 2  # Уменьшаем размер шрифта

            # Загружаем шрифт с уменьшенным размером
            font_1 = ImageFont.truetype(font=quote_text_font_path, size=font_size, encoding='UTF-8')

            # Перераспределяем строки с текстом с новым размером шрифта
            wrapped_quote_lines = []
            for paragraph in self._quote_text.split("\n"):
                wrapped_quote_lines.extend(self._wrap_text(paragraph, font_1, max_text_width))

        # Рисуем заголовок
        font_2 = ImageFont.truetype(font=headline_text_font_path, size=headline_text_size, encoding='UTF-8')
        size_headline = drawer.textbbox((0, 0), headline_text, font=font_2)
        size_headline = (size_headline[2] - size_headline[0], size_headline[3] - size_headline[1])
        drawer.text(
            ((1920 - size_headline[0]) / 2, 50),
            headline_text,
            font=font_2,
            fill='white',
        )

        # Позиционируем цитату внутри области
        y_offset = top_margin
        for i, line in enumerate(wrapped_quote_lines):
            # Добавляем кавычки только на первой и последней строке
            if i == 0:
                line = f"«{line}"  # Добавляем кавычку в начале первой строки
            if i == len(wrapped_quote_lines) - 1:
                line = f"{line}»"  # Добавляем кавычку в конце последней строки

            drawer.text((left_margin, y_offset), line, fill='white', font=font_1)
            y_offset += font_1.getbbox(line)[3] + 5  # Добавляем небольшой отступ между строками

        # Загружаем фото
        avatar_path = os.path.join(folder_name, avatar_name)

        if use_url:
            # Скачиваем фото по URL асинхронно
            avatar_path = os.path.join(folder_name, "avatar_from_url.jpg")
            await self._download_avatar(avatar_name, avatar_path)

        # Обрезаем фото в круг
        user_photo = Image.open(avatar_path).resize((300, 300), Image.Resampling.LANCZOS).convert("RGBA")
        mask = Image.new('L', (300, 300), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 300, 300), fill=255)
        user_photo.putalpha(mask)
        user_img.paste(user_photo, (50, 730), mask=user_photo)

        # Вычисляем размер и положение имени автора
        author_name_text = f'© {self._author_name}'
        font_3 = ImageFont.truetype(font=author_name_font_path, size=author_name_size, encoding='UTF-8')
        author_text_size = drawer.textbbox((0, 0), author_name_text, font=font_3)

        # Позиционируем имя автора в центре аватарки, сдвигаем на 50 пикселей вправо
        author_x = 50 + 300 + 50  # 50 пикселей от левого края, 300 - ширина аватарки, еще 50 пикселей для сдвига
        author_y = 730 + (300 // 2) - (author_text_size[3] // 2)  # Центрируем по вертикали

        # Рисуем имя автора
        drawer.text((author_x, author_y), author_name_text, fill='white', font=font_3)

        # Сохраняем изображение
        user_img.save(save_path)

        # Если фото было скачано, удаляем его
        if use_url:
            os.remove(avatar_path)

        return True