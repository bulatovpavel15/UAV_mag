import cv2
import numpy as np

"Нарисовать перекрестие в центре кадра. Обозначает точку, к которой БПЛА должен совместить маркер"

def draw_crosshair(frame):

    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    size = 20
    color = (0, 255, 255)   # Жёлтый (BGR)

    cv2.line(frame, (cx - size, cy), (cx + size, cy), color, 1)
    cv2.line(frame, (cx, cy - size), (cx, cy + size), color, 1)
    cv2.circle(frame, (cx, cy), 5, color, 1)

"Нарисовать оси координат маркера на кадре"

def draw_axes(frame, rvec, tvec, camera_matrix, dist_coeffs, length=0.05):

    axis_points = np.float32([
        [0, 0, 0],
        [length, 0, 0],
        [0, length, 0],
        [0, 0, -length]
    ])

    img_points, _ = cv2.projectPoints(
        axis_points, rvec, tvec, camera_matrix, dist_coeffs
    )
    img_points = img_points.astype(int).reshape(-1, 2)

    origin = tuple(img_points[0])
    cv2.line(frame, origin, tuple(img_points[1]), (0, 0, 255), 2)   # X
    cv2.line(frame, origin, tuple(img_points[2]), (0, 255, 0), 2)   # Y
    cv2.line(frame, origin, tuple(img_points[3]), (255, 0, 0), 2)   # Z

"Отобразить полную информацию об обнаруженном маркере"

def draw_detection_info(frame, marker_id, center, offset_px, offset_norm,
                        distance, tvec, angles, fps):

    h, w = frame.shape[:2]
    frame_cx, frame_cy = w // 2, h // 2
    mcx, mcy = int(center[0]), int(center[1])

    # Линия смещения: центр кадра → центр маркера
    cv2.line(frame, (frame_cx, frame_cy), (mcx, mcy), (0, 255, 0), 2)
    cv2.circle(frame, (mcx, mcy), 6, (0, 0, 255), -1)

    # Полупрозрачная панель
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 5), (380, 220), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Текст
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.50
    color = (0, 255, 0)
    y0, dy = 25, 22

    lines = [
        f"Marker ID: {marker_id}",
        f"Status: DETECTED",
        f"Center: ({center[0]:.0f}, {center[1]:.0f}) px",
        f"Offset: ({offset_px[0]:+.0f}, {offset_px[1]:+.0f}) px",
        f"Offset norm: ({offset_norm[0]:+.3f}, {offset_norm[1]:+.3f})",
        f"Distance: {distance:.3f} m",
        f"Tvec: [{tvec[0]:.3f}, {tvec[1]:.3f}, {tvec[2]:.3f}]",
        f"Roll: {angles[0]:+.1f}  Pitch: {angles[1]:+.1f}  Yaw: {angles[2]:+.1f}",
        f"FPS: {fps:.1f}"
    ]

    for i, line in enumerate(lines):
        cv2.putText(frame, line, (10, y0 + i * dy),
                    font, scale, color, 1, cv2.LINE_AA)

"Отобразить статус при отсутствии маркера в кадре"

def draw_no_detection(frame, fps):
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 5), (300, 60), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, "Marker: NOT DETECTED", (10, 25),
                font, 0.55, (0, 0, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 50),
                font, 0.50, (200, 200, 200), 1, cv2.LINE_AA)
