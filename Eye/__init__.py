import cv2
import cv2.aruco as aruco
import json

class Photoreceptor:
    def __init__(self, sticks: bool, cones: bool) -> None:
        self.sticks: bool = sticks
        self.cones: bool = cones

class Iris:
    def __init__(self, r: int, g: int, b: int, hex: str) -> None:
        self.r: int = r
        self.g: int = g
        self.b: int = b
        self.hex: str = hex

    def toLightAbsorption(self) -> float:
        # Нормалізація RGB до шкали 0-1
        rn, gn, bn = self.r / 255.0, self.g / 255.0, self.b / 255.0

        # Розрахунок сприйняття яскравості
        y = 0.2126 * rn + 0.7152 * gn + 0.0722 * bn

        # Розрахунок відсотка поглинання
        absorption = (1.0 - y) * 100.0

        # Біологічні обмеження (опціонально)
        return max(5.0, min(95.0, absorption))


class Lens:
    def __init__(self, ametropia_diopters: float = 0.0, cornea_power: float = 43.0, max_accommodation: float = 3.0) -> None:
        """
        :param ametropia_diopters: Degree of vision impairment (0.0 — perfect, ‘-’ — myopia, ‘+’ — hyperopia).
        :param cornea_power: Refractive power of the cornea (standard ~43.0 diopters).
        :param max_accommodation: Maximum accommodative power of the lens in diopters (standard for an adult ~3.0).
        """
        self.ametropia_diopters = ametropia_diopters
        self.cornea_power = cornea_power
        self.max_accommodation = max_accommodation

        # Сила кришталика в стані повного спокою (фокус вдалечінь)
        self.resting_lens_power = 16.0

        # Фіксована довжина очного яблука (L), розрахована на основі базової рефракції.
        # Формула: L = 1 / (Сила рогівки + Сила кришталика + Аметропія)
        self.eye_length = 1 / (self.cornea_power + self.resting_lens_power + self.ametropia_diopters)

    def calculateRequiredAccommodation(self, distance_m: float) -> float:
        """
        Calculates how many diopters of accommodation the eye NEEDS to focus on an object.
        :param distance_m: Distance to the object in meters.
        :return: Required lens effort in diopters.
        """
        if distance_m <= 0:
            return float('inf')

        # Фізична формула лінзи: D_total = 1/d + 1/L
        # Де d - відстань до об'єкта, L - відстань до сітківки (довжина ока)
        total_required_power = (2 / distance_m) + (1 / self.eye_length)

        # Скільки з цієї сили має забезпечити кришталик
        required_lens_power = total_required_power - self.cornea_power

        # Акомодація — це різниця між потрібною силою та розслабленим станом кришталика
        required_accommodation = required_lens_power - self.resting_lens_power

        return required_accommodation

    def calculatePower(self, distance_m: float, light_absorption: float) -> int:
        """
        Calculates the kernel size for OpenCV.
        :param distance_m: Distance to the object in meters.
        :param light_absorption: Light absorption from 5.0 to 95.0 (simulates pupil size).
        :return: An odd integer (Gaussian kernel size).
        """
        if distance_m <= 0.02:
            return 99

        if self.ametropia_diopters>0:
            required_acc = self.calculateRequiredAccommodation(distance_m/abs(self.ametropia_diopters)*1.35)
        elif self.ametropia_diopters<0:
            required_acc = self.calculateRequiredAccommodation(abs(3.5-distance_m)/abs(1.75*self.ametropia_diopters))
        else: required_acc = self.calculateRequiredAccommodation(distance_m*5)

        if 0 <= required_acc <= self.max_accommodation:
            dioptric_error = 0.0
        elif required_acc < 0:
            dioptric_error = abs(required_acc)
        else:
            dioptric_error = required_acc - self.max_accommodation

        if dioptric_error <= 0.1:
            return 1

        # ВИПРАВЛЕНО: Вплив зіниці
        # light_absorption високе (темно) -> зіниця широка -> фактор > 1.0 (сильніший блюр)
        # light_absorption низьке (яскраво) -> зіниця вузька (pinhole) -> фактор < 1.0 (менший блюр)
        pupil_factor = 0.3 + (light_absorption / 100.0) * 1.5

        # ВИПРАВЛЕНО: Базовий множник розмиття (збільшено для веб-камер)
        base_blur_multiplier = 40.0

        raw_ksize = int(dioptric_error * base_blur_multiplier * pupil_factor)

        if raw_ksize % 2 == 0:
            raw_ksize += 1

        return min(max(3, raw_ksize), 99)

class Eye:
    def __init__(self, iris: Iris, photoreceptor: Photoreceptor, lens: Lens, MARKER_WIDTH: float = .20, debug: bool = False) -> None:

        """

        :param iris: Iridium properties
        :param photoreceptor: Photoreceptor properties
        :param lens: Lens properties
        :param MARKER_WIDTH: Width of Marker
        :param debug: Debug mode
        """

        self.iris = iris
        self.photoreceptor = photoreceptor
        self.lens = lens
        self.MARKER_WIDTH: float = MARKER_WIDTH
        self.debug = debug
        self.focal_length = None
        self.generateConfig()
        self.calibrate()

    def generateConfig(self):
        data = {
                "iris": {"r": self.iris.r, "g": self.iris.g, "b": self.iris.b, "hex": self.iris.hex},
                "photoreceptor": {"sticks": self.photoreceptor.sticks, "cones": self.photoreceptor.cones},
                "lens": {"ametropia_diopters": self.lens.ametropia_diopters}
            }

        with (open("config.json", 'w')) as f:
            json.dump(data, f)

    def willConfigChanged(self):
        with (open("config.json", 'rb')) as f:
            newBinaryData=f.read()
        try:
            with (open("config.old.json", 'rb')) as f:
                oldBinaryData=f.read()
        except FileNotFoundError:
            with (open("config.old.json", 'wb')) as f:
                f.write(newBinaryData)
            self.onConfigChange()
            return

        if newBinaryData != oldBinaryData:
            with (open("config.old.json", 'wb')) as f:
                f.write(newBinaryData)
            self.onConfigChange()

    def onConfigChange(self):
        try:
            data = json.load(open("config.json", 'r'))
            print(data)
        except Exception as ex:
            print(f"ERROR: {ex}")
            return
        self.iris.r = data["iris"]["r"]
        self.iris.g = data["iris"]["g"]
        self.iris.b = data["iris"]["b"]
        self.photoreceptor.cones=data["photoreceptor"]["cones"]
        self.photoreceptor.sticks=data["photoreceptor"]["sticks"]
        self.lens.ametropia_diopters=data["lens"]["ametropia_diopters"]


    def getImage(self):
        """
        Getting image from camera.
        """
        aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        aruco_params = aruco.DetectorParameters()
        detector = aruco.ArucoDetector(aruco_dict, aruco_params)

        distance=None

        cam = cv2.VideoCapture(0)

        if not cam.isOpened():
            print("Error: Could not open camera.")
        else:
            print("Func getImage")
            print(self.focal_length)
            ret, frame = cam.read()
            kblur = 1
            current_absorption=10
            while ret:
                self.willConfigChanged()
                if self.photoreceptor.sticks:
                    ret, frame = cam.read()
                    if not self.photoreceptor.cones:
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                        gray=frame
                    else:
                        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

                    current_w_pixels = 0

                    corners, ids, rejected = detector.detectMarkers(gray)

                    if ids is not None:
                        # Малюємо контур навколо знайденого маркера
                        aruco.drawDetectedMarkers(frame, corners)

                        # Отримуємо кути першого знайденого маркера
                        marker_corners = corners[0][0]
                        # Рахуємо ширину маркера в пікселях між лівим верхнім і правим верхнім кутами
                        current_w_pixels = abs(marker_corners[0][0] - marker_corners[1][0])

                    if self.focal_length and current_w_pixels > 0:
                        distance = (self.MARKER_WIDTH * self.focal_length) / current_w_pixels

                        # 1. Отримуємо рівень поглинання світла від нашої райдужки
                        current_absorption = self.iris.toLightAbsorption()

                        # 2. Передаємо дистанцію та світло в лінзу
                        kblur = self.lens.calculatePower(distance, current_absorption)

                    frame = cv2.convertScaleAbs(frame, beta=100.0 - current_absorption)
                    frame = cv2.GaussianBlur(frame, (kblur, kblur), self.lens.ametropia_diopters)
                    if self.debug:
                        if distance is not None:
                            cv2.putText(frame, f"Distance: {distance:.2f} m", (20, 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                        cv2.imshow('Camera Image', frame)
                    #yield (b'--frame\r\n'
                    #   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                #else: yield (b'--frame\r\n'
                #       b'Content-Type: image/jpeg\r\n\r\n' + b'\r\n')

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cam.release()
            cv2.destroyAllWindows()

    def calibrate(self, CALIBRATION_DIST: float = 1):
        """
        Calibrating camera
        :param CALIBRATION_DIST: Distance to Marker
        :return: Focal length
        """

        # Налаштування детектора ArUco (стандартний словник 4х4)
        aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        aruco_params = aruco.DetectorParameters()
        detector = aruco.ArucoDetector(aruco_dict, aruco_params)

        cap = cv2.VideoCapture(0)
        print(f"Станьте на відстані приблизно {CALIBRATION_DIST}м від аркуша та натисніть 'C' для калібрування.")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Пошук маркера на зображенні
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, rejected = detector.detectMarkers(gray)

            current_w_pixels = 0

            if ids is not None:
                # Малюємо контур навколо знайденого маркера
                aruco.drawDetectedMarkers(frame, corners)

                # Отримуємо кути першого знайденого маркера
                marker_corners = corners[0][0]
                # Рахуємо ширину маркера в пікселях між лівим верхнім і правим верхнім кутами
                current_w_pixels = abs(marker_corners[0][0] - marker_corners[1][0])

            cv2.putText(frame, f"PRESS C TO CALIBRATE CAMERA", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            cv2.imshow("Calibration", frame)
            key = cv2.waitKey(1) & 0xFF

            # Клавіша 'C' рахує фокусну відстань на льоту
            if key == ord('c') and current_w_pixels > 0:
                self.focal_length = (current_w_pixels * CALIBRATION_DIST) / self.MARKER_WIDTH
                if self.debug:
                    print(f"\n[ГОТОВО] Калібрування успішне! Фокусна відстань камери: {self.focal_length:.2f}")
                    print("Тепер ви можете вільно відходити або підходити — відстань вимірюється автоматично.")
                cap.release()
                cv2.destroyAllWindows()

            if key == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    def getWidthByCalibratingDistance(self, DISTANCE_TO_OBJ: float = 1):
        """
        !!! WIP FUNCTION !!!

        :param DISTANCE_TO_OBJ: Distance to object
        :return: Width of object
        """

        cap = cv2.VideoCapture(0)
        print("Наведіть камеру на об'єкт для вимірювання його реальної ширини.")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 60, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for i in range(len(contours)):
                contour = contours[i]
                if cv2.contourArea(contour) > 2000:
                    x, y, w_pixels, h = cv2.boundingRect(contour)

                    # ГОЛОВНА ФОРМУЛА: знаходимо реальну ширину в метрах
                    real_width = (w_pixels * DISTANCE_TO_OBJ) / self.focal_length

                    # Візуалізація контуру та розміру
                    cv2.rectangle(frame, (x, y), (x + w_pixels, y + h), (255, 0, 0), 2)
                    cv2.putText(frame, f"Width: {real_width:.1f} m", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

            if self.debug:
                cv2.imshow("Object Width Measurement", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

