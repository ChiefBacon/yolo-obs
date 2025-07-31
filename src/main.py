import sys
import datetime
import time
import configparser
from configparser import NoOptionError
from obswebsocket import obsws, requests
from requests import post
from ultralytics import YOLO
import cv2
import simpleLogger

config = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
config.read('obs-object-detection.ini')
logger = simpleLogger.SimpleLogger("obs-object-detection.log")

logger.logInfo("Preparing OBS Object Detection")

# Configuration
try:
    config.get("config.obs", "Host")
except configparser.NoSectionError:
    logger.logError("Configuration file not found or malformed. Please create or check obs-object-detection.ini")
    sys.exit(1)

host = config.get("config.obs", "Host")
port = int(config.get("config.obs", "Port"))
password = config.get("config.obs", "Password")

if config.getboolean("config.ntfy", "Enabled"):
    notification_url = config.get("config.ntfy", "URL")
    notification_topic = config.get("config.ntfy", "Topic")
    notification_title = config.get("config.ntfy", "Title")
    ntfy_enabled = True
else:
    ntfy_enabled = False

# Connect to websockets
logger.logInfo("Connecting to OBS WebSocket")
try:
    ws = obsws(host, port, password)
    ws.connect()
except Exception as e:
    logger.logError(f"Failed to connect to OBS WebSocket: {e}")
    sys.exit(1)
logger.logSuccess("Connected to OBS WebSocket")

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
canvas_info = ws.call(requests.GetVideoSettings())
scene_height = int(canvas_info.getBaseHeight())
scene_width = int(canvas_info.getBaseWidth())

logger.logInfo("Loading config file")
try:
    detection_objects = config.get("config.ai", "DetectionObjects").split(",")
    avoid_objects = config.get("config.ai", "DisallowList").split(",")
    preview_window_enabled = config.getboolean("config.preview", "Enabled")
    preview_window_fps = config.getboolean("config.preview", "ShowFPS")
    present_scene = config.get("config.obs", "PresentScene")
    away_scene = config.get("config.obs", "AwayScene")
    disallow_scene = config.get("config.obs", "DisallowScene")
    presence_threshold = config.getint("config.ai", "NoPresenceTimeout")
    smart_scale_item_id = config.getint("config.ai", "SmartScaleItemId")
    camera_num    = config.getint("config.ai", "CameraNumber")
    camera_width  = config.getint("config.ai", "CameraWidth")
    camera_height = config.getint("config.ai", "CameraHeight")
    use_gpu = config.getboolean("config.ai", "UseGPU")
except configparser.NoOptionError as e:
    logger.logError("Failed to load config file. Please check obs-object-detection.ini")
    sys.exit(1)
logger.logSuccess("Config Loaded")

# Colors for drawing boxes
blue = (255, 0, 0)
green = (0, 255, 0)
red = (0, 0, 255)

# Load YOLO model
logger.logInfo("Loading YOLO model")
yolo = YOLO(config.get("config.ai", "YoloModel"), verbose=False)
logger.logSuccess("YOLO model loaded")

# Initialize webcam
logger.logInfo("Initializing camera")
cap = cv2.VideoCapture(camera_num)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
logger.logSuccess("Camera initialized")

logger.logInfo("Starting main process")

# Main loop
while True:
    start = time.time()
    target_in_frame = False
    scissors_in_frame = False

    if privacy_screen != prev_privacy_screen:
        prev_privacy_screen = privacy_screen
        if privacy_screen:
            logger.logInfo(f"Disallow list object detected, switching to \"{disallow_scene}\"")
            ws.call(requests.SetCurrentProgramScene(sceneName=disallow_scene))
        else:
            logger.logInfo(f"Disallow list object no longer detected, switching to \"{away_scene}\"")
            ws.call(requests.SetCurrentProgramScene(sceneName=away_scene))

    if prev_cam_status != cam_status and not privacy_screen:
        prev_cam_status = cam_status
        if cam_status:
            logger.logInfo(f"Object detected, switching to \"{present_scene}\"")
            target_detections += 1
            if ntfy_enabled:
                post(notification_url + notification_topic, data="Object has been detected!", headers={"Title": notification_title, "Priority": "high"})
            ws.call(requests.SetCurrentProgramScene(sceneName=present_scene))
        else:
            logger.logInfo(f"No objects of intrest found, switching to \"{away_scene}\"")
            ws.call(requests.SetCurrentProgramScene(sceneName=away_scene))
            ws.call(requests.SetSceneItemTransform(sceneName=present_scene, sceneItemId=smart_scale_item_id, sceneItemTransform={"cropLeft": 0.0, "cropRight": 0.0, "cropTop": 0.0, "cropBottom": 0.0, "scaleX": 1.0, "scaleY": 1.0, "positionX": 0.0, "positionY": 0.0}))

    if prev_target_present != target_present:
        prev_target_present = target_present
        if target_present:
            cam_status = True
        else:
            time_target_last_seen = datetime.datetime.now()

    ret, frame = cap.read()
    if not ret:
        logger.logError("Failed to read frame from camera.")
        break

    # Detecting objects using YOLOv5
    results = yolo(source=frame, stream=False, verbose=False, device=0 if use_gpu else 'cpu')

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

                if class_name in detection_objects:
                    color = blue
                    target_present = True
                    target_in_frame = True
                    time_target_last_seen = datetime.datetime.now()
                    if config.getboolean("config.ai", "UseSmartScale"):
                        ws.call(requests.SetSceneItemTransform(sceneName=present_scene, sceneItemId=smart_scale_item_id, sceneItemTransform={"cropLeft": x1 - 20, "cropRight": (scene_width - x2) - 20, "cropTop": y1 - 20, "cropBottom": (scene_height - y2) - 20}))
                elif class_name in avoid_objects:
                    color = red
                    time_scissors_last_seen = datetime.datetime.now()
                    privacy_screen = True
                    scissors_in_frame = True
                else:
                    color = green

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, class_name, (x1 + 5, y2 - 10), cv2.FONT_HERSHEY_PLAIN, 2, color, 2)
    # Update states
    if not target_in_frame:
        target_present = False
        if (datetime.datetime.now() - time_target_last_seen).seconds > presence_threshold:
            cam_status = False

    if not scissors_in_frame and privacy_screen:
        if (datetime.datetime.now() - time_scissors_last_seen).seconds > 5:
            privacy_screen = False

    end = time.time()
    frametime = end - start
    fps = 1 / frametime

    if preview_window_enabled:
        if preview_window_fps:
            cv2.putText(frame, f"{fps:.2f} FPS", (5, 30), cv2.FONT_HERSHEY_PLAIN, 2, blue, 2)
        cv2.imshow("OBS Object Detection", frame)
        key = cv2.waitKey(1)
        if key == 27:  # Press 'ESC' to exit
            break

cap.release()
cv2.destroyAllWindows()
