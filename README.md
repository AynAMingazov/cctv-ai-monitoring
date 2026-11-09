# cctv-ai-monitoring

Video analytics I added on top of the existing cameras of a car-service company (2026).
The owner has several sites and cannot watch all streams. The task was to get useful events from the cameras without buying new hardware.

This repository has the code and an example config. No real video, no images of people.

## What the owner asked for
| Need | Rule |
|---|---|
| Know if someone comes to the doors at night | **Night door**: alert in Telegram with a snapshot |
| Know how many customers really came | **Entrance line**: count of people crossing inward |
| Control the oil dispenser | **Zone visit**: who stood at the dispenser, when, how long |
| Control the cash desk and shelves | **Hands in zone**: wrist activity in the area |
| Check that all customers are registered | **Reconcile**: visitors from the camera vs orders from the office system |

The last one came from a real situation: on some days the number of cars in the yard did not match the number of orders. The camera gives an independent count, and a big gap is a reason to check the day manually.

## How it works
```
IP camera (RTSP) -> YOLOv8n-pose  (people + 17 keypoints, class "person" only)
                 -> ByteTrack     (stable id for each person between frames)
                 -> rules         (zones and lines from JSON config)
                 -> SQLite events + Telegram alerts
reconcile.py <- orders.csv from the office
```

Design decisions:
- **Bottom center of the box** is used as the position of a person. It is where the feet are, so it works on a floor plan and is stable when the upper body is hidden behind a car.
- **Line crossing per track id.** A person is counted once when the side of the line changes, not on every frame.
- **Wrists instead of body** for the cash desk. A worker can stand near the desk all day; what matters is hands inside the drawer area.
- **Every 2nd frame** is processed (`vid_stride=2`). For these rules 12-15 fps is enough and CPU load is half.
- **Cooldown 5 minutes** for night alerts and **minimum time in zone** for visits. Without them there were too many messages.

## Choosing the model
I needed boxes and wrist keypoints from one network that runs on an office PC without a GPU. Pose models give both in one pass.

| Model | mAP pose 50-95 (COCO) | Params | CPU ONNX, ms | Comment |
|---|---|---|---|---|
| YOLO11n-pose | 50.0 | 2.9 M | 52 | Next step, same API |
| YOLO11s-pose | 58.9 | 9.9 M | 90 | If the PC gets better |
| YOLOv8n-pose | 50.4 | 3.3 M | ~130 | Used now |

Numbers are from the Ultralytics documentation. Other options I looked at:
- **RT-DETR**: better in crowded scenes, too slow on CPU for several streams.
- **MediaPipe Hands**: precise hand landmarks, but fails on ceiling cameras where hands are 20-30 pixels.
- **ByteTrack vs BoT-SORT**: ByteTrack (80.3 MOTA on MOT17 in the original paper) keeps up on CPU. BoT-SORT keeps ids better when people cross each other but is heavier. Both are built into Ultralytics, the tracker is changed by one parameter.

## Problems I met
- **Night IR image** is grey and low-contrast, confidence drops. I lowered the threshold for night zones and rely on time in zone instead of single detections.
- **False alerts** from animals and moving shadows of car lights. Class filter `person` and minimum time in zone solved most of them.
- **RTSP drops** on cheap cameras. The script is restarted by the system scheduler; events have timestamps, so gaps are visible in the log. Automatic reconnect inside the script is on the to-do list.
- **Zone drawing**: coordinates are in pixels of the specific camera. I took a frame, measured polygons in an image editor and saved them to JSON.

## Privacy
- No face recognition. People are anonymous track ids that reset on restart.
- Only events and counts are stored. Video stays on the company recorder.
- Snapshots are sent only for night alerts and only to the owner's chat.

## Tests
`pytest -q` checks the rules without a camera or a model (8 tests):
- point in polygon and side of line
- night alert only in closed hours, cooldown, ignoring people outside the zone
- line counter counts one crossing once
- zone visit duration and ignoring short visits
- hands zone uses wrists, not feet
- reconciliation flags days with unregistered visits

On real video I checked the rules on recorded fragments from the client's recorder: the night door at the back entrance and the entrance counter on a working day compared with manual count.

## Run
```
pip install -r requirements.txt
cp zones.example.json zones.json   # set RTSP url and zones
python run.py --config zones.json --show
python reconcile.py --orders orders.csv --day 2026-10-15
pytest -q
```

Python 3.10+, Ultralytics, ByteTrack, OpenCV, SQLite, Telegram Bot API.

## References
- Ultralytics YOLO11 and pose models: https://docs.ultralytics.com/tasks/pose/
- Zhang et al., ByteTrack: Multi-Object Tracking by Associating Every Detection Box, ECCV 2022: https://arxiv.org/abs/2110.06864
- Aharon et al., BoT-SORT: Robust Associations Multi-Pedestrian Tracking, 2022: https://arxiv.org/abs/2206.14651
