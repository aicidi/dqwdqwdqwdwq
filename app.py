from flask import Flask, request, render_template, send_file
from PIL import Image, ImageDraw
import os
import io
from datetime import datetime
from PIL import ImageFont

app = Flask(__name__)

font_path = "./DejaVuSans.ttf"
font_size = 50
font = ImageFont.truetype(font_path, font_size)  # 원하는 폰트 크기 설정


def create_image_with_text(input_string, image_index):
    # A4 용지 크기 (210mm x 297mm) -> 픽셀로 변환 (300 DPI 기준)
    dpi = 300
    image_width = int(210 * dpi / 25.4)  # mm를 인치로 변환
    image_height = int(297 * dpi / 25.4)  # mm를 인치로 변환

    # 타일 크기 및 패딩 설정
    tile_size = 40  # 각 타일의 크기
    tile_padding = 5  # 타일 간격
    small_tile_size = 10  # 작은 타일 크기

    # 타일이 시작되는 위치를 2cm (20mm) 떨어진 곳으로 설정
    margin = int(20 * dpi / 25.4)  # mm를 픽셀로 변환
    start_x = margin
    start_y = margin

    # 격자가 배치될 수 있는 이미지 내부의 크기
    available_width = image_width - 2 * margin
    available_height = image_height - 2 * margin

    # 최대 가능한 타일 수 계산
    cols = available_width // (tile_size + tile_padding)
    rows = available_height // (tile_size + tile_padding)
    max_tiles = cols * rows

    # 이미지 생성
    img = Image.new('RGB', (image_width, image_height), color='white')
    draw = ImageDraw.Draw(img)

    # 문자열을 기반으로 타일 생성
    for index in range(max_tiles):
        if index < len(input_string):
            char = input_string[index]
        else:
            break  # 더 이상 문자가 없으면 종료

        # 타일 위치 계산
        col = index % cols
        row = index // cols
        x0 = start_x + col * (tile_size + tile_padding)
        y0 = start_y + row * (tile_size + tile_padding)
        x1 = x0 + tile_size
        y1 = y0 + tile_size

        # 문자를 UTF-16으로 인코딩하여 이진 형태로 변환
        encoded_char = char.encode('utf-16')
        binary_str = ''.join(f"{byte:08b}" for byte in encoded_char[2:])  # 첫 번째 바이트 건너뛰기

        # 16비트에서 4x4 타일로 변환 (4x4는 16비트에 해당)
        for i in range(4):
            for j in range(4):
                sx0 = x0 + i * small_tile_size
                sy0 = y0 + j * small_tile_size
                sx1 = sx0 + small_tile_size
                sy1 = sy0 + small_tile_size

                bit = int(binary_str[i * 4 + j])  # 0 또는 1
                color = (0, 0, 0) if bit == 1 else (255, 255, 255)
                
                draw.rectangle([sx0, sy0, sx1, sy1], fill=color)

        # 타일을 빨간 테두리로 굵게 그리기
        draw.rectangle([x0, y0, x1, y1], outline='red', width=2)

    # 오른쪽 위에 이미지 번호 표시
    draw.text((image_width - 50, 10), f"{image_index + 1}", fill="black", font=font)

    return img

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        input_string = request.form['input_string']
        base_filename = datetime.now().strftime("%Y%m%d_%H%M%S")  # YYYYMMDD_HHMMSS 형식
        
        # 입력 문자열 길이 계산
        max_tiles = int(((210 - 40) * 300 // 25.4 // (40 + 5)) * ((297 - 40) * 300 // 25.4 // (40 + 5)))
        images = []
        
        # 입력 문자열을 기반으로 이미지 생성
        for i in range(0, len(input_string), max_tiles):
            segment = input_string[i:i + max_tiles]
            img = create_image_with_text(segment, len(images))

            file_name = f"{base_filename}_{len(images) + 1}.png" 
            img.save('./images/' + file_name, format='PNG')
            images.append(file_name)  # 이미지와 파일 이름 저장

        return render_template('result.html', images=images)

    return render_template('index.html')

@app.route('/download/<filename>')
def download_image(filename):
    # 저장된 이미지 파일 경로에 맞게 수정
    img_path = f"images/{filename}"
    return send_file(img_path, mimetype='image/png', as_attachment=True)

if __name__ == '__main__':
    # 이미지 저장할 디렉토리 생성
    if not os.path.exists('images'):
        os.makedirs('images')
    app.run(debug=True)

