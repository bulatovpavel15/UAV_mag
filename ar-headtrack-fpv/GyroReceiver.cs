/*
 * GyroReceiver.cs
 * ===============
 * Скрипт для СИМУЛЯТОРА (ПК).
 * 
 * Принимает UDP пакеты с ориентацией телефона от PhoneGyroSender
 * и предоставляет данные другим скриптам (ARHeadTrackInput).
 *
 * Поставить на любой GameObject на сцене симулятора.
 * Работает в отдельном потоке — не блокирует основной поток Unity.
 */

using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;

namespace Bulatov.AR
{
    public class GyroReceiver : MonoBehaviour
    {
        [Header("Сетевые настройки")]
        [Tooltip("UDP порт (должен совпадать с PhoneGyroSender)")]
        [SerializeField] private int port = 9870;

        [Header("Статус")]
        [SerializeField] private bool isReceiving;
        [SerializeField] private float lastPacketTime;

        // --- Публичные данные (читают другие скрипты) ---
        
        /// <summary>Последняя полученная ориентация телефона (thread-safe)</summary>
        public Quaternion PhoneRotation { get; private set; } = Quaternion.identity;
        
        /// <summary>Подключён ли телефон (были пакеты за последние 2 сек)</summary>
        public bool IsPhoneConnected => (Time.time - lastPacketTime) < 2f;

        /// <summary>Время получения последнего пакета</summary>
        public float LastPacketTimestamp => lastPacketTime;

        // --- Внутренние ---
        private UdpClient udpClient;
        private Thread receiveThread;
        private volatile bool threadRunning;

        // Thread-safe буфер (volatile поля для передачи между потоками)
        private volatile float qx, qy, qz, qw;
        private volatile bool newDataAvailable;

        // Синглтон для удобного доступа
        private static GyroReceiver _instance;
        public static GyroReceiver Instance
        {
            get
            {
                if (_instance == null)
                    _instance = FindObjectOfType<GyroReceiver>();
                return _instance;
            }
        }

        #region Unity Lifecycle

        private void Awake()
        {
            _instance = this;
        }

        private void Start()
        {
            StartReceiving();
        }

        private void Update()
        {
            // Перенос данных из потока приёма в основной поток Unity
            if (newDataAvailable)
            {
                PhoneRotation = new Quaternion(qx, qy, qz, qw);
                lastPacketTime = Time.time;
                isReceiving = true;
                newDataAvailable = false;
            }

            // Обнаружение отключения
            if (isReceiving && !IsPhoneConnected)
            {
                isReceiving = false;
                Debug.Log("[GyroReceiver] Телефон отключился (нет пакетов > 2 сек)");
            }
        }

        private void OnDestroy()
        {
            StopReceiving();
        }

        private void OnApplicationQuit()
        {
            StopReceiving();
        }

        #endregion

        #region Networking

        private void StartReceiving()
        {
            try
            {
                udpClient = new UdpClient(port);
                udpClient.Client.ReceiveTimeout = 1000; // 1 сек таймаут для graceful shutdown

                threadRunning = true;
                receiveThread = new Thread(ReceiveLoop)
                {
                    IsBackground = true,
                    Name = "GyroReceiver_UDP"
                };
                receiveThread.Start();

                Debug.Log($"[GyroReceiver] Слушаю UDP порт {port}");
            }
            catch (Exception e)
            {
                Debug.LogError($"[GyroReceiver] Ошибка запуска: {e.Message}");
            }
        }

        private void StopReceiving()
        {
            threadRunning = false;

            udpClient?.Close();
            udpClient = null;

            if (receiveThread != null && receiveThread.IsAlive)
            {
                receiveThread.Join(2000);
            }
        }

        /// <summary>
        /// Цикл приёма в отдельном потоке.
        /// Парсит пакеты формата PhoneGyroSender (20 байт: qx,qy,qz,qw,timestamp).
        /// </summary>
        private void ReceiveLoop()
        {
            IPEndPoint remoteEP = new IPEndPoint(IPAddress.Any, 0);

            while (threadRunning)
            {
                try
                {
                    byte[] data = udpClient.Receive(ref remoteEP);

                    // Проверка на пакет отключения
                    if (data.Length < 20)
                    {
                        string msg = System.Text.Encoding.UTF8.GetString(data);
                        if (msg == "DISCONNECT")
                        {
                            Debug.Log("[GyroReceiver] Телефон отправил DISCONNECT");
                            continue;
                        }
                    }

                    // Парсинг кватерниона (20 байт)
                    if (data.Length >= 20)
                    {
                        qx = BitConverter.ToSingle(data, 0);
                        qy = BitConverter.ToSingle(data, 4);
                        qz = BitConverter.ToSingle(data, 8);
                        qw = BitConverter.ToSingle(data, 12);
                        // data[16..19] — timestamp (пока не используется)

                        newDataAvailable = true;
                    }
                }
                catch (SocketException)
                {
                    // Таймаут — нормально, просто продолжаем
                }
                catch (ObjectDisposedException)
                {
                    // Сокет закрыт — выход из потока
                    break;
                }
                catch (Exception e)
                {
                    if (threadRunning)
                        Debug.LogWarning($"[GyroReceiver] Ошибка приёма: {e.Message}");
                }
            }
        }

        #endregion
    }
}
