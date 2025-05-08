import cv2
import numpy as np
import datetime
import time
from obswebsocket import obsws, requests
from requests import post
from ultralytics import YOLO
import paho.mqtt.client as mqtt
import json
import torch
from colorama import Fore, Back
import configparser

config = configparser.ConfigParser()
config.read('yolo-obs-cfg.ini')

print(config.sections())

print(Fore.CYAN+"Preparing... ", end=Fore.RESET)

# MQTT Config
if config.getboolean("config.mqtt", "Enabled"):
    mqtt_enabled = True
    broker = config.get("config.mqtt", "Broker")
    mq_port = config.get("config.mqtt", "Port")
    client_id = "yolo-obs"
    mq_username = config.get("config.mqtt", "Username")
    mq_password = config.get("config.mqtt", "Password")
else:
    mqtt_enabled = False

# Configuration
host = config.get("config.obs", "Host")
port = int(config.get("config.obs", "Port"))
password = config.get("config.obs", "Password")

if config.getboolean("config.ntfy", "Enabled"):
    notification_url = config.get("config.ntfy", "URL")
    ntfy_enabled = True
else:
    ntfy_enabled = False

device_info = {"device": {
    "identifiers":[
        "yolobs"
    ],
    "name":"YOLO OBS",
    "manufacturer":"github.com/ChiefBacon",
    "model":"YoloObs",
    "serial_number":"yolo_239894803290",
    }
}

detections_sensor_setup = json.dumps({
    "name": "Animal Detections",
    "icon": "mdi:dog-side",
    "state_topic": "homeassistant/sensor/yolo-obs/detections/value",
    "unique_id": "sensor.yolo-obs_detections",
} | device_info)

camera_active_setup = json.dumps({
    "name": "Camera Status",
    "icon": "mdi:camera",
    "state_topic": "homeassistant/binary_sensor/yolo-obs/camera_active/value",
    "unique_id": "binary_sensor.yolo-obs_camera_active",
} | device_info)

privacy_screen_active_setup = json.dumps({
    "name": "Privacy Screen",
    "icon": "mdi:eye-off",
    "state_topic": "homeassistant/binary_sensor/yolo-obs/privacy/value",
    "unique_id": "binary_sensor.yolo-obs_privacy_mode",
} | device_info)

animal_detected_setup = json.dumps({
    "name": "Animal Presence",
    "icon": "mdi:dog",
    "device_class": "occupancy",
    "state_topic": "homeassistant/binary_sensor/yolo-obs/animal_detected/value",
    "unique_id": "binary_sensor.yolo-obs_animal_seen",
} | device_info)

if mqtt_enabled:
    def connect_mqtt():
        def on_connect(client, userdata, flags, rc):
            if rc == 0: print("Connected to MQTT!")
            else: print("Failed to connect to MQTT")
        client = mqtt.Client()
        client.username_pw_set(mq_username, mq_password)
        client.on_connect = on_connect
        client.connect(broker, mq_port)
        return client


    def publish(client, topic, msg):
        result = client.publish(topic, msg)
        status = result[0]
        if status != 0: print(f"Failed to send message to {topic}")


    print(Fore.GREEN+"Done!"+Fore.RESET)

    print("Connecting To MQTT...")
    mqtt_client = connect_mqtt()

    publish(mqtt_client, 'homeassistant/sensor/yolo-obs/detections/config', detections_sensor_setup)
    publish(mqtt_client, 'homeassistant/binary_sensor/yolo-obs/camera_active/config', camera_active_setup)
    publish(mqtt_client, 'homeassistant/binary_sensor/yolo-obs/privacy/config', privacy_screen_active_setup)
    publish(mqtt_client, 'homeassistant/binary_sensor/yolo-obs/animal_seen/config', animal_detected_setup)

    publish(mqtt_client, 'homeassistant/sensor/yolo-obs/detections/value', 0)
    publish(mqtt_client, 'homeassistant/binary_sensor/yolo-obs/camera_active/value', "OFF")
    publish(mqtt_client, 'homeassistant/binary_sensor/yolo-obs/privacy/value', "OFF")
    publish(mqtt_client, 'homeassistant/binary_sensor/yolo-obs/animal_seen/value', "OFF")

# Connect to websockets
print(f'{Fore.CYAN}Connecting to OBS... {Fore.RESET}', end="")
ws = obsws(host, port, password)
ws.connect()
print(f'{Fore.GREEN}Done!{Fore.RESET}')

# Initialize state variables
target_detections = 0
target_present = False
prev_target_present = False
target_in_frame = False
time_target_last_seen = datetime.datetime.now()
cam_status = False
prev_cam_status = False
privacy_screen = False
prev_privacy_screen = False
scissors_in_frame = False
time_scissors_last_seen = datetime.datetime.now()
processing_device = None

# Colors for drawing boxes
blue = (255, 0, 0)
green = (0, 255, 0)
red = (0, 0, 255)

# Load YOLOv5 model
print(f'{Fore.CYAN}Loading YOLO... {Fore.RESET}', end="")
yolo = YOLO(config.get("config.ai", "YoloModel"), verbose=False)
print(f'{Fore.GREEN}Done!{Fore.RESET}')

if torch.backends.mps.is_available() and config.getboolean("config.ai", "AttemptMPS"):
    print("MPS available, switching to GPU.")
    processing_device = 'mps'

elif torch.backends.cudnn.is_available() and config.getboolean("config.ai", "AttemptCUDNN"):
    print("CUDNN available, switching to GPU.")
    processing_device = 0

else:
    processing_device = 'cpu'

print("Initializing Webcam...")
# Initialize webcam
cap = cv2.VideoCapture(int(config.get("config.ai", "CameraNumber")))

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

print("Webcam Initialized!")

print("Starting Up")
while True:
    start = time.time()
    if mqtt_enabled: publish(mqtt_client, "homeassistant/sensor/yolo-obs/detections/value", target_detections)
    target_in_frame = False
    scissors_in_frame = False

    if privacy_screen != prev_privacy_screen:
        prev_privacy_screen = privacy_screen
        if privacy_screen:
            print("PRIVACY ACTIVE")
            publish(mqtt_client, "homeassistant/binary_sensor/yolo-obs/privacy/value", "ON")
            ws.call(requests.SetCurrentProgramScene(sceneName="Paused"))
        else:
            print("NORMAL OPERATION")
            publish(mqtt_client, "homeassistant/binary_sensor/yolo-obs/privacy/value", "OFF")
            ws.call(requests.SetCurrentProgramScene(sceneName="Away"))

    if prev_cam_status != cam_status and not privacy_screen:
        prev_cam_status = cam_status
        if cam_status:
            print("CAM ON")
            target_detections += 1
            if mqtt_enabled:
                publish(mqtt_client, "homeassistant/sensor/yolo-obs/detections/value", target_detections)
                publish(mqtt_client, "homeassistant/binary_sensor/yolo-obs/camera_active/value", "ON")
            if ntfy_enabled:
                post(notification_url, data="Act NOW: Dog has been detected!", headers={"Title": "Walter CAM LIVE", "Actions": "http, Open Stream, http://10.1.8.26"})
            ws.call(requests.SetCurrentProgramScene(sceneName="Cam 2"))
        else:
            print("CAM OFF")
            publish(mqtt_client, "homeassistant/binary_sensor/yolo-obs/camera_active/value", "OFF")
            ws.call(requests.SetCurrentProgramScene(sceneName="Away"))
            ws.call(requests.SetSceneItemTransform(sceneName="Cam 2", sceneItemId=14, sceneItemTransform={"cropLeft": 0.0, "cropRight": 0.0, "cropTop": 0.0, "cropBottom": 0.0, "scaleX": 1.0, "scaleY": 1.0, "positionX": 0.0, "positionY": 0.0}))

    if prev_target_present != target_present:
        prev_target_present = target_present
        if target_present:
            cam_status = True
            if mqtt_enabled:
                publish(mqtt_client, "homeassistant/binary_sensor/yolo-obs/animal_detected/value", "ON")
        else:
            time_target_last_seen = datetime.datetime.now()
            if mqtt_enabled:
                publish(mqtt_client, "homeassistant/binary_sensor/yolo-obs/animal_detected/value", "OFF")

    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        continue

    # Detecting objects using YOLOv5
    results = yolo.track(frame, stream=False, verbose=False, device=processing_device)

    height, width, _ = frame.shape
    target_in_frame = False
    scissors_in_frame = False

    for result in results:
        classes_names = result.names

        for box in result.boxes:
            if box.conf[0] > 0.4:
                # Object detected
                [x1, y1, x2, y2] = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                cls = int(box.cls[0])
                class_name = classes_names[cls]

                if class_name in ["dog", "cat", "sheep", "horse", "cow"]:
                    color = blue
                    target_present = True
                    target_in_frame = True
                    time_target_last_seen = datetime.datetime.now()
                    if config.getboolean("config.ai", "UseSmartScale"): ws.call(requests.SetSceneItemTransform(sceneName="Cam 2", sceneItemId=14, sceneItemTransform={"cropLeft": x1 - 20, "cropRight": (1920 - x2) - 20, "cropTop": y1 - 20, "cropBottom": (1080 - y2) - 20}))
                elif class_name == "scissors":
                    color = red
                    time_scissors_last_seen = datetime.datetime.now()
                    privacy_screen = True
                    scissors_in_frame = True
                else: color = green

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, class_name, (x1 + 5, y2 - 10), cv2.FONT_HERSHEY_PLAIN, 2, color, 2)
    # Update states
    if not target_in_frame:
        target_present = False
        if (datetime.datetime.now() - time_target_last_seen).seconds > 15:
            cam_status = False

    if not scissors_in_frame and privacy_screen:
        if (datetime.datetime.now() - time_scissors_last_seen).seconds > 5:
            privacy_screen = False

    end = time.time()
    frametime = end - start
    fps = 1/frametime

    cv2.putText(frame, "{:.2f} FPS".format(fps), (5, 30), cv2.FONT_HERSHEY_PLAIN, 2, blue, 2)
    cv2.imshow("YOLO OBS", frame)
    key = cv2.waitKey(1)
    if key == 27:  # Press 'ESC' to exit
        break

cap.release()
cv2.destroyAllWindows()
