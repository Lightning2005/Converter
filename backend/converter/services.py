import io
import zipfile
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from pdf2image import convert_from_bytes
from django.conf import settings


def convert_images_to_pdf(uploaded_images):
    pdf_buffer = io.BytesIO()
    page_width, page_height = A4
    pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=A4)

    for uploaded_file in uploaded_images:
        # 1. Открываем и исправляем ориентацию (EXIF)
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)

        # 2. Обработка прозрачности (PDF не любит RGBA)
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 3. Расчет масштабирования (вписываем картинку в A4 с отступами)
        margin = 7  # 7 пунктов отступа
        usable_w = page_width - (2 * margin)
        usable_h = page_height - (2 * margin)

        img_w, img_h = img.size
        # Вычисляем соотношение сторон
        ratio = min(usable_w / img_w, usable_h / img_h)

        new_w = img_w * ratio
        new_h = img_h * ratio

        # Центрирование
        x = (page_width - new_w) / 2
        y = (page_height - new_h) / 2

        # 4. Вставка изображения
        img_reader = ImageReader(img)
        pdf_canvas.drawImage(img_reader, x, y, width=new_w, height=new_h)

        # 5. Обязательно фиксируем страницу
        pdf_canvas.showPage()

    pdf_canvas.save()
    pdf_buffer.seek(0)
    return pdf_buffer


def convert_pdf_to_images(uploaded_pdf):
    """
    Принимает PDF-файл из request.FILES.
    Возвращает байтовый поток (BytesIO) с ZIP-архивом страниц.
    """
    pdf_bytes = uploaded_pdf.read()

    # Берем путь к poppler из settings.py (на Linux там будет None)
    pages = convert_from_bytes(pdf_bytes, poppler_path=settings.POPPLER_PATH)

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for index, page in enumerate(pages):
            img_buffer = io.BytesIO()
            page.save(img_buffer, format='JPEG', quality=90)
            img_buffer.seek(0)

            filename = f"page_{index + 1}.jpg"
            zip_file.writestr(filename, img_buffer.read())

    zip_buffer.seek(0)
    return zip_buffer