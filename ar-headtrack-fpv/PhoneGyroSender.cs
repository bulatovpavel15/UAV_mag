using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;
using UnityEngine.XR.ARFoundation;

namespace Bulatov.AR
{
    public class PhoneGyroSender : MonoBehaviour
    {
        [Header("Сетевые настройки")]
        [Tooltip("IP-адрес ПК с симулятором (в одной Wi-Fi сети)")]
        [SerializeField] private string simulatorIP = "192.168.1.100";

        [Tooltip("UDP порт (должен совпадать с GyroReceiver)")]
        [SerializeField] private int port = 9870;

        [Header("Параметры отправки")]
        [Tooltip("Частота отправки пакетов (Гц)")]
        [SerializeField] private int sendRate = 60;

        [Header("Калибровка")]
        [Tooltip("Нажмите для сброса нулевой ориентации (смотреть вперёд)")]
        [SerializeField] private bool calibrateOnStart = true;

        [Header("AR компоненты")]
        [Tooltip("Камера AR Session Origin (автоматически найдётся если пусто)")]
        [SerializeField] private Camera arCamera;

        // --- Внутренние переменные ---
        private UdpClient udpClient;
        private IPEndPoint endPoint;
        private float sendInterval;
        private float lastSendTime;
        private Quaternion calibrationOffset = Quaternion.identity;
        private bool isConnected;

        // --- UI для отладки ---
        private string statusMessage = "Инициализация...";
        private Quaternion lastSentRotation;

        #region Unity Lifecycle

        private void Start()
        {
            // Не давать экрану гаснуть
            Screen.sleepTimeout = SleepTimeout.NeverSleep;

            // Найти AR камеру
            if (arCamera == null)
            {
                arCamera = FindObjectOfType<ARCameraManager>()?.GetComponent<Camera>();
                if (arCamera == null)
                {
                    arCamera = Camera.main;
                }
            }

            if (arCamera == null)
            {
                statusMessage = "ОШИБКА: AR камера не найдена!";
                Debug.LogError("[PhoneGyroSender] AR камера не найдена. Добавьте AR Session Origin на сцену.");
                return;
            }

            // Настройка UDP
            sendInterval = 1f / sendRate;

            try
            {
                udpClient = new UdpClient();
                endPoint = new IPEndPoint(IPAddress.Parse(simulatorIP), port);
                isConnected = true;
                statusMessage = $"Подключено → {simulatorIP}:{port}";
                Debug.Log($"[PhoneGyroSender] UDP отправка на {simulatorIP}:{port}");
            }
            catch (Exception e)
            {
                statusMessage = $"ОШИБКА UDP: {e.Message}";
                Debug.LogError($"[PhoneGyroSender] Ошибка создания UDP: {e.Message}");
                return;
            }

            // Калибровка начальной ориентации
            if (calibrateOnStart)
            {
                Invoke(nameof(Calibrate), 0.5f); // дать AR полсекунды на инициализацию
            }
        }

        private void Update()
        {
            if (!isConnected || arCamera == null) return;

            // Ограничение частоты отправки
            if (Time.time - lastSendTime < sendInterval) return;
            lastSendTime = Time.time;

            // Получить ориентацию AR камеры (уже с sensor fusion)
            Quaternion rawRotation = arCamera.transform.rotation;

            // Применить калибровку (вычесть начальную ориентацию)
            Quaternion calibratedRotation = Quaternion.Inverse(calibrationOffset) * rawRotation;

            lastSentRotation = calibratedRotation;

            // Отправить
            SendOrientationPacket(calibratedRotation);
        }

        private void OnDestroy()
        {
            // Отправить пакет "отключение"
            if (isConnected && udpClient != null)
            {
                try
                {
                    byte[] disconnectPacket = Encoding.UTF8.GetBytes("DISCONNECT");
                    udpClient.Send(disconnectPacket, disconnectPacket.Length, endPoint);
                }
                catch { }
            }

            udpClient?.Close();
        }

        #endregion

        #region Networking

        /// <summary>
        /// Формат пакета (20 байт, little-endian):
        ///   [0..3]   float q.x
        ///   [4..7]   float q.y
        ///   [8..11]  float q.z
        ///   [12..15] float q.w
        ///   [16..19] float timestamp (Time.time)
        /// </summary>
        private void SendOrientationPacket(Quaternion q)
        {
            try
            {
                byte[] data = new byte[20];
                Buffer.BlockCopy(BitConverter.GetBytes(q.x), 0, data, 0, 4);
                Buffer.BlockCopy(BitConverter.GetBytes(q.y), 0, data, 4, 4);
                Buffer.BlockCopy(BitConverter.GetBytes(q.z), 0, data, 8, 4);
                Buffer.BlockCopy(BitConverter.GetBytes(q.w), 0, data, 12, 4);
                Buffer.BlockCopy(BitConverter.GetBytes(Time.time), 0, data, 16, 4);

                udpClient.Send(data, data.Length, endPoint);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[PhoneGyroSender] Ошибка отправки: {e.Message}");
            }
        }

        #endregion

        #region Calibration

        /// <summary>
        /// Сброс нулевого положения. Вызывайте когда телефон направлен "вперёд".
        /// </summary>
        public void Calibrate()
        {
            if (arCamera != null)
            {
                calibrationOffset = arCamera.transform.rotation;
                statusMessage = "Откалибровано! Текущее направление = вперёд";
                Debug.Log("[PhoneGyroSender] Калибровка выполнена");
            }
        }

        #endregion

        #region Debug UI

        /// <summary>
        /// Простой отладочный GUI прямо на экране телефона.
        /// Показывает статус, углы Эйлера и кнопку калибровки.
        /// </summary>
        private void OnGUI()
        {
            float scale = Screen.dpi / 160f;
            int fontSize = Mathf.RoundToInt(14 * scale);

            GUIStyle style = new GUIStyle(GUI.skin.label)
            {
                fontSize = fontSize,
                normal = { textColor = Color.white }
            };

            GUIStyle btnStyle = new GUIStyle(GUI.skin.button)
            {
                fontSize = fontSize
            };

            float y = 10 * scale;
            float x = 10 * scale;
            float w = Screen.width - 20 * scale;
            float h = fontSize * 1.8f;

            // Статус
            GUI.Label(new Rect(x, y, w, h), $"Статус: {statusMessage}", style);
            y += h;

            // Углы
            Vector3 euler = lastSentRotation.eulerAngles;
            GUI.Label(new Rect(x, y, w, h),
                $"Pitch: {euler.x:F1}°  Yaw: {euler.y:F1}°  Roll: {euler.z:F1}°", style);
            y += h;

            // IP
            GUI.Label(new Rect(x, y, w, h), $"Цель: {simulatorIP}:{port}", style);
            y += h * 1.5f;

            // Кнопка калибровки
            if (GUI.Button(new Rect(x, y, w * 0.5f, h * 2), "КАЛИБРОВКА\n(сброс нуля)", btnStyle))
            {
                Calibrate();
            }
        }

        #endregion
    }
}
