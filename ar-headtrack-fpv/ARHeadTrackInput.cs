using UnityEngine;

namespace Bulatov.AR
{
    [RequireComponent(typeof(Drone_Inputs))]
    public class ARHeadTrackInput : MonoBehaviour
    {
        [Header("Включение")]
        [Tooltip("Вкл/выкл управление головой. Можно менять в рантайме.")]
        [SerializeField] private bool useHeadTracking = true;

        [Tooltip("Клавиша переключения head tracking")]
        [SerializeField] private KeyCode toggleKey = KeyCode.H;

        [Header("Чувствительность")]
        [Tooltip("Множитель для pitch (вперёд/назад)")]
        [Range(0.1f, 3f)]
        [SerializeField] private float pitchSensitivity = 1.0f;

        [Tooltip("Множитель для roll (наклон влево/вправо)")]
        [Range(0.1f, 3f)]
        [SerializeField] private float rollSensitivity = 1.0f;

        [Tooltip("Множитель для yaw (поворот головы)")]
        [Range(0.1f, 3f)]
        [SerializeField] private float yawSensitivity = 1.0f;

        [Header("Мёртвая зона")]
        [Tooltip("Углы меньше этого значения игнорируются (градусы)")]
        [Range(0f, 15f)]
        [SerializeField] private float deadZone = 3f;

        [Header("Ограничения углов")]
        [Tooltip("Максимальный угол наклона для полного отклонения (градусы)")]
        [Range(15f, 60f)]
        [SerializeField] private float maxTiltAngle = 30f;

        [Tooltip("Максимальный угол yaw для полного отклонения (градусы)")]
        [Range(30f, 90f)]
        [SerializeField] private float maxYawAngle = 60f;

        [Header("Сглаживание")]
        [Tooltip("Скорость интерполяции (больше = резче)")]
        [Range(1f, 20f)]
        [SerializeField] private float smoothingSpeed = 8f;

        [Header("FPV камера")]
        [Tooltip("Камера FPV (если задана, будет поворачиваться по ориентации телефона)")]
        [SerializeField] private Transform fpvCameraTransform;

        [Tooltip("Насколько камера следует за головой (0 = не следует, 1 = полностью)")]
        [Range(0f, 1f)]
        [SerializeField] private float cameraFollowFactor = 0.7f;

        // --- Внутренние переменные ---
        private GyroReceiver gyroReceiver;
        private Drone_Inputs droneInputs;

        // Сглаженные значения
        private float smoothPitch;
        private float smoothRoll;
        private float smoothYaw;

        // Рефлексия для записи в Drone_Inputs (поля private)
        private System.Reflection.FieldInfo cyclicField;
        private System.Reflection.FieldInfo pedalsField;

        #region Unity Lifecycle

        private void Start()
        {
            droneInputs = GetComponent<Drone_Inputs>();
            gyroReceiver = GyroReceiver.Instance;

            if (gyroReceiver == null)
            {
                Debug.LogError("[ARHeadTrackInput] GyroReceiver не найден на сцене! " +
                               "Добавьте GyroReceiver на любой GameObject.");
                enabled = false;
                return;
            }

            // Получить доступ к private полям Drone_Inputs через рефлексию
            var type = typeof(Drone_Inputs);
            var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;

            cyclicField = type.GetField("cyclic", flags);
            pedalsField = type.GetField("pedals", flags);

            if (cyclicField == null || pedalsField == null)
            {
                Debug.LogError("[ARHeadTrackInput] Не удалось найти поля cyclic/pedals в Drone_Inputs. " +
                               "Проверьте имена полей.");
                enabled = false;
                return;
            }

            Debug.Log("[ARHeadTrackInput] Инициализирован. Нажмите H для вкл/выкл head tracking.");
        }

        private void Update()
        {
            // Переключение по клавише
            if (Input.GetKeyDown(toggleKey))
            {
                useHeadTracking = !useHeadTracking;
                Debug.Log($"[ARHeadTrackInput] Head tracking: {(useHeadTracking ? "ВКЛ" : "ВЫКЛ")}");
            }

            if (!useHeadTracking) return;
            if (gyroReceiver == null || !gyroReceiver.IsPhoneConnected) return;

            // Преобразовать кватернион телефона в углы Эйлера
            Quaternion phoneRot = gyroReceiver.PhoneRotation;
            Vector3 euler = phoneRot.eulerAngles;

            // Нормализовать углы в диапазон [-180, 180]
            float pitch = NormalizeAngle(euler.x); // наклон вперёд/назад
            float yaw   = NormalizeAngle(euler.y); // поворот влево/вправо
            float roll  = NormalizeAngle(euler.z); // наклон влево/вправо

            // Применить мёртвую зону
            pitch = ApplyDeadZone(pitch);
            roll  = ApplyDeadZone(roll);
            yaw   = ApplyDeadZone(yaw);

            // Нормализовать в [-1, 1]
            float normalizedPitch = Mathf.Clamp(pitch / maxTiltAngle, -1f, 1f) * pitchSensitivity;
            float normalizedRoll  = Mathf.Clamp(roll  / maxTiltAngle, -1f, 1f) * rollSensitivity;
            float normalizedYaw   = Mathf.Clamp(yaw   / maxYawAngle,  -1f, 1f) * yawSensitivity;

            // Сглаживание
            float dt = Time.deltaTime * smoothingSpeed;
            smoothPitch = Mathf.Lerp(smoothPitch, normalizedPitch, dt);
            smoothRoll  = Mathf.Lerp(smoothRoll,  normalizedRoll,  dt);
            smoothYaw   = Mathf.Lerp(smoothYaw,   normalizedYaw,   dt);

            // Записать в Drone_Inputs
            Vector2 cyclic = new Vector2(smoothRoll, smoothPitch);
            cyclicField.SetValue(droneInputs, cyclic);
            pedalsField.SetValue(droneInputs, smoothYaw);

            // Поворот FPV камеры
            if (fpvCameraTransform != null)
            {
                Quaternion targetCamRot = Quaternion.Slerp(
                    Quaternion.identity,
                    phoneRot,
                    cameraFollowFactor
                );
                fpvCameraTransform.localRotation = Quaternion.Slerp(
                    fpvCameraTransform.localRotation,
                    targetCamRot,
                    dt
                );
            }
        }

        #endregion

        #region Utility

        /// <summary>Нормализовать угол из [0,360] в [-180,180]</summary>
        private float NormalizeAngle(float angle)
        {
            if (angle > 180f) angle -= 360f;
            return angle;
        }

        /// <summary>Обнулить значения внутри мёртвой зоны</summary>
        private float ApplyDeadZone(float value)
        {
            if (Mathf.Abs(value) < deadZone)
                return 0f;

            // Плавный переход от края мёртвой зоны
            float sign = Mathf.Sign(value);
            return (Mathf.Abs(value) - deadZone) * sign;
        }

        #endregion

        #region Debug GUI

        private void OnGUI()
        {
            if (!useHeadTracking) return;

            GUIStyle style = new GUIStyle(GUI.skin.label)
            {
                fontSize = 14,
                normal = { textColor = Color.cyan }
            };

            float y = 10;
            string connected = (gyroReceiver != null && gyroReceiver.IsPhoneConnected)
                ? "<color=lime>ПОДКЛЮЧЁН</color>"
                : "<color=red>НЕТ СВЯЗИ</color>";

            style.richText = true;

            GUI.Label(new Rect(10, y, 400, 25), $"[HEAD TRACK] Телефон: {connected}", style);
            y += 22;
            GUI.Label(new Rect(10, y, 400, 25),
                $"Pitch: {smoothPitch:F2}  Roll: {smoothRoll:F2}  Yaw: {smoothYaw:F2}", style);
            y += 22;
            GUI.Label(new Rect(10, y, 400, 25), $"[H] — вкл/выкл  |  Чувств: P={pitchSensitivity:F1} R={rollSensitivity:F1} Y={yawSensitivity:F1}", style);
        }

        #endregion
    }
}
