import cv2
import os
import argparse

from config import (
    MARKER_ID, MARKER_SIZE, CAMERA_INDEX,
    FRAME_WIDTH, FRAME_HEIGHT, ARUCO_DICTS, ARUCO_DICT_NAME
)
from detector import ArucoDetector

"Разбор аргументов командной строки"
def parse_args():
    parser = argparse.ArgumentParser(
        description="Распознавание посадочной площадки БПЛА (ArUco маркер)"
    )
    parser.add_argument(
        "--camera", type=int, default=CAMERA_INDEX,
        help=f"Индекс камеры (по умолчанию {CAMERA_INDEX})"
    )
    parser.add_argument(
        "--marker_id", type=int, default=MARKER_ID,
        help=f"ID маркера ArUco (по умолчанию {MARKER_ID})"
    )
    parser.add_argument(
        "--marker_size", type=float, default=MARKER_SIZE,
        help=f"Размер стороны маркера в метрах (по умолчанию {MARKER_SIZE})"
    )
    parser.add_argument(
        "--resolution", type=str,
        default=f"{FRAME_WIDTH}x{FRAME_HEIGHT}",
        help=f"Разрешение камеры (по умолчанию {FRAME_WIDTH}x{FRAME_HEIGHT})"
    )
    parser.add_argument(
        "--dict", type=str, default=ARUCO_DICT_NAME,
        choices=list(ARUCO_DICTS.keys()),
        help=f"Словарь ArUco (по умолчанию {ARUCO_DICT_NAME})"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Разрешение
    res_w, res_h = map(int, args.resolution.split('x'))

    # Открытие камеры
    print(f"[КАМЕРА] Открытие камеры {args.camera}...")
    cap = cv2.VideoCapture(args.camera)

    if not cap.isOpened():
        print("[ОШИБКА] Не удалось открыть камеру!")
        print("  Проверьте:")
        print("  1. Камера подключена")
        print("  2. Драйверы установлены")
        print("  3. Попробуйте: python main.py --camera 1")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, res_w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, res_h)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Инициализация детектора
    detector = ArucoDetector(
        marker_id=args.marker_id,
        marker_size=args.marker_size,
        dict_name=args.dict,
        frame_width=actual_w,
        frame_height=actual_h
    )

    # Информация о запуске
    print(f"\n{'=' * 60}")
    print(f"  РАСПОЗНАВАНИЕ ПОСАДОЧНОЙ ПЛОЩАДКИ БПЛА")
    print(f"  Маркер ArUco ID:  {args.marker_id}")
    print(f"  Размер маркера:   {args.marker_size} м")
    print(f"  Словарь:          {args.dict}")
    print(f"  Камера:           {args.camera}")
    print(f"  Разрешение:       {actual_w}x{actual_h}")
    print(f"{'=' * 60}")
    print(f"  q — выход  |  s — скриншот  |  p — пауза\n")

    screenshot_count = 0

    # Главный цикл
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ОШИБКА] Не удалось получить кадр")
                break

            # Обработка кадра
            frame, detected, result = detector.process_frame(frame)

            # Отображение
            cv2.imshow("ArUco Landing Pad Detector", frame)

            # Клавиши
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                screenshot_count += 1
                fname = f"results/screenshot_{screenshot_count}.png"
                os.makedirs("results", exist_ok=True)
                cv2.imwrite(fname, frame)
                print(f"[СКРИНШОТ] Сохранён: {fname}")
            elif key == ord('p'):
                print("[ПАУЗА] Нажмите любую клавишу для продолжения...")
                cv2.waitKey(0)

    except KeyboardInterrupt:
        print("\n[ПРЕРВАНО] Ctrl+C")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()


if __name__ == "__main__":
    main()
