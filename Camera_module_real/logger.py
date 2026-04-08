import csv
import os
import time
from datetime import datetime

"Логирование результатов распознавания маркера в CSV-файл"
class ExperimentLogger:

    # Заголовки столбцов CSV
    HEADERS = [
        "timestamp",        # Время от старта (сек)
        "marker_id",        # ID маркера
        "detected",         # 1 — найден, 0 — нет
        "center_x_px",      # Центр маркера X (пиксели)
        "center_y_px",      # Центр маркера Y (пиксели)
        "offset_x_px",      # Смещение от центра кадра X (пиксели)
        "offset_y_px",      # Смещение от центра кадра Y (пиксели)
        "offset_x_norm",    # Нормализованное смещение X [-1; 1]
        "offset_y_norm",    # Нормализованное смещение Y [-1; 1]
        "distance_m",       # Расстояние до маркера (метры)
        "tvec_x",           # Вектор трансляции X (метры)
        "tvec_y",           # Вектор трансляции Y (метры)
        "tvec_z",           # Вектор трансляции Z (метры)
        "roll_deg",         # Угол крена (градусы)
        "pitch_deg",        # Угол тангажа (градусы)
        "yaw_deg",          # Угол рыскания (градусы)
        "fps",              # Частота обработки кадров
    ]

    def __init__(self, output_dir="results"):

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(output_dir, f"aruco_log_{timestamp}.csv")

        self.csv_file = open(self.filepath, mode='w', newline='',
                             encoding='utf-8')
        self.writer = csv.writer(self.csv_file, delimiter=';')
        self.writer.writerow(self.HEADERS)

        self.start_time = time.time()
        self.frame_count = 0
        self.detection_count = 0

        print(f"[ЛОГГЕР] Файл: {self.filepath}")
        

    "Записать одну строку измерений"
    def log(self, marker_id, detected, center, offset_px, offset_norm,
            distance, tvec, angles, fps):
    
        t = round(time.time() - self.start_time, 3)

        if detected:
            self.detection_count += 1
            row = [
                t, marker_id, 1,
                round(center[0], 1), round(center[1], 1),
                round(offset_px[0], 1), round(offset_px[1], 1),
                round(offset_norm[0], 4), round(offset_norm[1], 4),
                round(distance, 3),
                round(tvec[0], 4), round(tvec[1], 4), round(tvec[2], 4),
                round(angles[0], 2), round(angles[1], 2), round(angles[2], 2),
                round(fps, 1)
            ]
        else:
            row = [t, marker_id, 0,
                   "", "", "", "", "", "", "", "", "", "", "", "", "", 
                   round(fps, 1)]

        self.writer.writerow(row)
        self.frame_count += 1
        
        "Закрыть файл и вывести итоговую статистику"
    def close(self):
        self.csv_file.close()
        elapsed = time.time() - self.start_time

        print(f"\n[ЛОГГЕР] Завершено.")
        print(f"  Всего кадров:        {self.frame_count}")
        print(f"  Маркер обнаружен:    {self.detection_count} "
              f"({self._percent(self.detection_count, self.frame_count)})")
        print(f"  Время работы:        {elapsed:.1f} сек")
        if elapsed > 0:
            print(f"  Средний FPS:         {self.frame_count / elapsed:.1f}")
        print(f"  Файл:                {self.filepath}")

    @staticmethod
    def _percent(part, total):
        "Процент с защитой от деления на ноль"
        if total == 0:
            return "0.0%"
        return f"{100.0 * part / total:.1f}%"
