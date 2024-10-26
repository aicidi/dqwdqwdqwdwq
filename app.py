from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import requests
import datetime
import os
from io import BytesIO

app = Flask(__name__)

# MongoDB 클라이언트 설정
uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['image_storage']
collection = db['images']

# imgbb API 설정
IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY', 'YOUR_DEFAULT_IMGBB_API_KEY') #
IMGBB_UPLOAD_URL = 'https://api.imgbb.com/1/upload'

# A4 용지 크기 (픽셀, 300 DPI 기준)
A4_WIDTH, A4_HEIGHT = 2480, 3508

def text_to_unicode_array(text, cols=10):
    # 문자열을 유니코드 숫자로 변환
    unicode_array = [ord(char) for char in text]
    
    num_elements = len(unicode_array)
    rows = (num_elements + cols - 1) // cols  
    remainder = num_elements % cols

    if remainder != 0:
        padding_size = cols - remainder
        unicode_array.extend([0] * padding_size)

    unicode_array_reshaped = np.zeros((rows, cols), dtype=int)
    for idx, val in enumerate(unicode_array):
        row = idx // cols
        col = idx % cols
        unicode_array_reshaped[row, col] = val

    return unicode_array_reshaped

def create_image_from_array(array, cols, page_number):
    image = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    margin_x, margin_y = 100, 100
    line_height = 40
    col_width = 100

    max_cols = (A4_WIDTH - margin_x * 2) // col_width
    max_cols = min(max_cols, cols)
    max_rows = (A4_HEIGHT - margin_y * 2) // line_height
    max_chars_per_page = max_rows * max_cols

    draw.text((A4_WIDTH - 150, 50), f"Page {page_number}", fill='black', font=font)

    for row_idx in range(min(array.shape[0], max_rows)):
        for col_idx in range(min(array.shape[1], max_cols)):
            num = array[row_idx, col_idx]
            x = margin_x + col_idx * col_width
            y = margin_y + row_idx * line_height

            if num != 0:
                draw.text((x + 10, y + 5), str(num), fill='black', font=font)
            draw.rectangle([x, y, x + col_width, y + line_height], outline="black")

    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output

def upload_to_imgbb(image_data):
    files = {'image': image_data}
    response = requests.post(IMGBB_UPLOAD_URL, files=files, params={'key': IMGBB_API_KEY})
    if response.status_code == 200:
        return response.json()['data']['url']
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = request.form['text']
        cols = int(request.form.get('cols', 10))

        unicode_array = text_to_unicode_array(text, cols)
        line_height, col_width, margin_x, margin_y = 40, 100, 100, 100
        max_cols = min((A4_WIDTH - margin_x * 2) // col_width, cols)
        max_rows = (A4_HEIGHT - margin_y * 2) // line_height
        max_chars_per_page = max_rows * max_cols

        total_pages = (unicode_array.size + max_chars_per_page - 1) // max_chars_per_page
        image_urls = []

        for page_number in range(1, total_pages + 1):
            start_idx = (page_number - 1) * max_chars_per_page
            end_idx = start_idx + max_chars_per_page
            page_array = unicode_array.flat[start_idx:end_idx]
            page_array = np.array(list(page_array) + [0] * (max_chars_per_page - len(page_array)))
            page_array = page_array.reshape(max_rows, max_cols)

            image_data = create_image_from_array(page_array, cols, page_number)
            image_url = upload_to_imgbb(image_data)

            if image_url:
                image_urls.append(image_url)
                collection.insert_one({"filename": f"page_{page_number}", "url": image_url})

        return render_template('result.html', image_urls=image_urls)

    return render_template('index.html')

@app.route('/admin')
def admin():
    images = list(collection.find())
    return render_template('admin.html', images=images)

if __name__ == '__main__':
    app.run(debug=True)

