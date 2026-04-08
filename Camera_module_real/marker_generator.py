import cv2
import cv2.aruco as aruco
import numpy as np
import argparse

from config import MARKER_ID, ARUCO_DICTS, ARUCO_DICT_NAME

"Сгенерировать изображение маркера ArUco для печати"

def generate_marker(marker_id=MARKER_ID, size_px=700,
                    dict_name=ARUCO_DICT_NAME,
                    output_file=None):

    if output_file is None:
        output_file = f"aruco_marker_{marker_id}.png"

    aruco_dict = aruco.getPredefinedDictionary(ARUCO_DICTS[dict_name])

    # Генерация маркера
    marker_img = aruco.generateImageMarker(aruco_dict, marker_id, size_px)

    # Белая рамка вокруг маркера (обязательна для распознавания!)
    border = 50
    result = np.ones(
        (size_px + 2 * border, size_px + 2 * border), dtype=np.uint8
    ) * 255
    result[border:border + size_px, border:border + size_px] = marker_img

    cv2.imwrite(output_file, result)

    print(f"Маркер ArUco сгенерирован:")
    print(f"  ID:       {marker_id}")
    print(f"  Словарь:  {dict_name}")
    print(f"  Размер:   {size_px + 2 * border}x{size_px + 2 * border} пикс.")
    print(f"  Файл:     {output_file}")
    print()
    print(f"  Следующие шаги:")
    print(f"  1. Распечатайте файл на бумаге А4")
    print(f"  2. Измерьте линейкой сторону чёрного квадрата (в метрах)")
    print(f"  3. Укажите размер при запуске: python main.py --marker_size 0.18")

    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Генерация маркера ArUco для печати"
    )
    parser.add_argument("--id", type=int, default=MARKER_ID,
                        help=f"ID маркера (по умолчанию {MARKER_ID})")
    parser.add_argument("--size", type=int, default=700,
                        help="Размер маркера в пикселях (по умолчанию 700)")
    parser.add_argument("--dict", type=str, default=ARUCO_DICT_NAME,
                        choices=list(ARUCO_DICTS.keys()),
                        help=f"Словарь ArUco (по умолчанию {ARUCO_DICT_NAME})")
    parser.add_argument("--output", type=str, default=None,
                        help="Имя выходного файла")
    args = parser.parse_args()

    generate_marker(
        marker_id=args.id,
        size_px=args.size,
        dict_name=args.dict,
        output_file=args.output
    )
