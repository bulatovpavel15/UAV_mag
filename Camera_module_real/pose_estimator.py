"""
pose_estimator.py — Математика: оценка позиции маркера, углы, смещения.

Этот модуль содержит функции для:
  - Вычисления центра маркера по его углам
  - Вычисления смещения маркера от центра кадра
  - Оценки 3D-позиции маркера (расстояние + ориентация)
  - Преобразования матрицы поворота в углы Эйлера
"""

import cv2
import numpy as np
import math


def rotation_matrix_to_euler(R):
    """
    Преобразование матрицы поворота 3x3 в углы Эйлера (roll, pitch, yaw).

    Используется конвенция ZYX (yaw → pitch → roll), совпадающая
    с принятой в аэродинамике квадрокоптера.

    Args:
        R: матрица поворота 3x3 (numpy array)

    Returns:
        (roll, pitch, yaw) в градусах
    """
    sy = math.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
    singular = sy < 1e-6

    if not singular:
        roll = math.atan2(R[2, 1], R[2, 2])
        pitch = math.atan2(-R[2, 0], sy)
        yaw = math.atan2(R[1, 0], R[0, 0])
    else:
        roll = math.atan2(-R[1, 2], R[1, 1])
        pitch = math.atan2(-R[2, 0], sy)
        yaw = 0.0

    return (
        math.degrees(roll),
        math.degrees(pitch),
        math.degrees(yaw)
    )


def compute_marker_center(corners):
    """
    Вычислить центр маркера как среднее четырёх углов.

    Args:
        corners: массив координат 4 углов маркера, shape (4, 2)

    Returns:
        (cx, cy) — координаты центра в пикселях
    """
    cx = float(np.mean(corners[:, 0]))
    cy = float(np.mean(corners[:, 1]))
    return (cx, cy)


def compute_offset(center, frame_width, frame_height):
    """
    Вычислить смещение маркера от центра кадра.

    Знак смещения соответствует направлению коррекции БПЛА:
      offset_x > 0  →  маркер правее центра  →  коптер двигается вправо
      offset_y > 0  →  маркер ниже центра     →  коптер двигается вперёд

    Нормализованные значения лежат в диапазоне [-1.0; +1.0]:
      0.0 означает, что маркер точно в центре кадра по данной оси.

    Args:
        center:       (cx, cy) — центр маркера в пикселях
        frame_width:  ширина кадра (пиксели)
        frame_height: высота кадра (пиксели)

    Returns:
        offset_px:   (dx, dy) — смещение в пикселях
        offset_norm: (dx_norm, dy_norm) — нормализованное смещение [-1; 1]
    """
    frame_cx = frame_width / 2.0
    frame_cy = frame_height / 2.0

    dx = center[0] - frame_cx
    dy = center[1] - frame_cy

    dx_norm = dx / frame_cx
    dy_norm = dy / frame_cy

    return (dx, dy), (dx_norm, dy_norm)


def estimate_pose(corners, marker_size, camera_matrix, dist_coeffs):
    """
    Оценка 3D-позиции маркера относительно камеры методом solvePnP.

    Задача Perspective-n-Point (PnP): по известным 2D-координатам углов
    маркера на изображении и их 3D-координатам в системе координат маркера
    определяется положение и ориентация маркера в пространстве.

    Система координат маркера:
      - Начало координат — центр маркера
      - Ось X — вправо
      - Ось Y — вверх
      - Ось Z — из маркера к камере

    Args:
        corners:       4 угла маркера в пикселях, shape (4, 2)
        marker_size:   физический размер стороны маркера (метры)
        camera_matrix: матрица внутренних параметров камеры (3x3)
        dist_coeffs:   коэффициенты дисторсии

    Returns:
        rvec:     вектор поворота (Rodrigues), shape (3,1), или None
        tvec:     вектор трансляции [x, y, z] в метрах, shape (3,), или None
        distance: расстояние до маркера (метры), или None
        angles:   (roll, pitch, yaw) в градусах, или None
    """
    # 3D-координаты углов маркера в его собственной СК (метры)
    half = marker_size / 2.0
    obj_points = np.array([
        [-half,  half, 0],   # Верхний левый
        [ half,  half, 0],   # Верхний правый
        [ half, -half, 0],   # Нижний правый
        [-half, -half, 0],   # Нижний левый
    ], dtype=np.float64)

    # Решение PnP
    success, rvec, tvec = cv2.solvePnP(
        obj_points,
        corners.astype(np.float64),
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_IPPE_SQUARE
    )

    if not success:
        return None, None, None, None

    tvec = tvec.flatten()
    distance = float(np.linalg.norm(tvec))

    # Матрица поворота из вектора Родригеса
    R, _ = cv2.Rodrigues(rvec)
    angles = rotation_matrix_to_euler(R)

    return rvec, tvec, distance, angles
