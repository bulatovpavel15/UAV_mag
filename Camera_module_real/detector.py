"""
detector.py — Детектор маркеров ArUco.

Связывает модули pose_estimator, visualizer и logger
в единый конвейер обработки кадров.
"""

import cv2
import cv2.aruco as aruco
import time

from config import (
    ARUCO_DICTS, ARUCO_DICT_NAME, MARKER_ID, MARKER_SIZE,
    get_camera_matrix, DIST_COEFFS
)
from pose_estimator import compute_marker_center, compute_offset, estimate_pose
from visualizer import (
    draw_crosshair, draw_axes, draw_detection_info, draw_no_detection
)
from logger import ExperimentLogger


class ArucoDetector:
    """
    Детектор посадочной площадки на основе маркера ArUco.

    Класс инкапсулирует:
      - Инициализацию детектора ArUco
      - Обработку одного кадра (детекция + оценка позиции)
      - Отрисовку результатов
      - Логирование измерений
    """

    def __init__(self, marker_id=MARKER_ID, marker_size=MARKER_SIZE,
                 dict_name=ARUCO_DICT_NAME, frame_width=640,
                 frame_height=480):
        """
        Args:
            marker_id:    ID маркера для поиска
            marker_size:  размер стороны маркера (метры)
            dict_name:    название словаря ArUco
            frame_width:  ширина кадра
            frame_height: высота кадра
        """
        self.marker_id = marker_id
        self.marker_size = marker_size

        # Словарь и параметры детектора
        self.aruco_dict = aruco.getPredefinedDictionary(
            ARUCO_DICTS[dict_name]
        )
        self.aruco_params = aruco.DetectorParameters()

        # Параметры камеры
        self.camera_matrix = get_camera_matrix(frame_width, frame_height)
        self.dist_coeffs = DIST_COEFFS.copy()

        # Логгер
        self.logger = ExperimentLogger()

        # FPS
        self._frame_times = []
        self.fps = 0.0

    def process_frame(self, frame):
        """
        Обработать один кадр: найти маркер, вычислить позицию, отрисовать.

        Args:
            frame: BGR-кадр с камеры (numpy array)

        Returns:
            frame:    кадр с отрисованными результатами
            detected: True, если маркер найден
            result:   dict с данными (или None)
        """
        t_start = time.time()

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Обнаружение маркеров
        corners, ids, _ = aruco.detectMarkers(
            gray, self.aruco_dict, parameters=self.aruco_params
        )

        # Перекрестие
        draw_crosshair(frame)

        # Поиск нужного маркера
        result = None
        detected = False

        if ids is not None:
            aruco.drawDetectedMarkers(frame, corners, ids)

            for i, mid in enumerate(ids.flatten()):
                if mid == self.marker_id:
                    detected = True
                    marker_corners = corners[i][0]

                    # Вычисления
                    center = compute_marker_center(marker_corners)
                    offset_px, offset_norm = compute_offset(center, w, h)
                    rvec, tvec, distance, angles = estimate_pose(
                        marker_corners, self.marker_size,
                        self.camera_matrix, self.dist_coeffs
                    )

                    if rvec is not None:
                        # Отрисовка
                        draw_axes(frame, rvec, tvec.reshape(3, 1),
                                  self.camera_matrix, self.dist_coeffs,
                                  length=self.marker_size * 0.5)
                        draw_detection_info(
                            frame, mid, center, offset_px,
                            offset_norm, distance, tvec, angles, self.fps
                        )

                        # Логирование
                        self.logger.log(
                            marker_id=mid, detected=True,
                            center=center, offset_px=offset_px,
                            offset_norm=offset_norm, distance=distance,
                            tvec=tvec, angles=angles, fps=self.fps
                        )

                        # Результат
                        result = {
                            "marker_id": mid,
                            "center": center,
                            "offset_px": offset_px,
                            "offset_norm": offset_norm,
                            "distance": distance,
                            "tvec": tvec,
                            "angles": angles,
                        }
                    break

        if not detected:
            draw_no_detection(frame, self.fps)
            self.logger.log(
                marker_id=self.marker_id, detected=False,
                center=(0, 0), offset_px=(0, 0), offset_norm=(0, 0),
                distance=0, tvec=(0, 0, 0), angles=(0, 0, 0),
                fps=self.fps
            )

        # FPS (скользящее среднее по 30 кадрам)
        dt = time.time() - t_start
        self._frame_times.append(dt)
        if len(self._frame_times) > 30:
            self._frame_times.pop(0)
        self.fps = 1.0 / (sum(self._frame_times) / len(self._frame_times))

        return frame, detected, result

    def close(self):
        """Закрыть логгер и освободить ресурсы."""
        self.logger.close()
