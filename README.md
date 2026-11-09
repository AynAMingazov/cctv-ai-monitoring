# cctv-ai-monitoring

Video analytics on existing cameras of a car service. Several sites, no new hardware.
Repository contains code and example config only. No video.

## Rules
| Rule | Output |
|---|---|
| Night door | Telegram alert with snapshot if a person is near the door after closing |
| Entrance line | Visitor count |
| Oil dispenser zone | Who, when, how long |
| Hands in zone | Wrist activity at cash desk or shelves |
| Reconcile | Counted visitors vs registered orders |

## Pipeline
RTSP → YOLOv8-pose (people, wrists) → ByteTrack (ids) → rules → SQLite, Telegram.

Person position is the bottom center of the box. Stable when the body is partly hidden by a car.

## Models
| Model | Notes |
|---|---|
| YOLOv8n-pose | Used. Boxes and keypoints in one pass, runs on CPU. |
| YOLO11-pose | Planned. Higher accuracy, same API. |
| RT-DETR | Better in crowds, slower. |
| MediaPipe Hands | Poor on ceiling cameras with low resolution. |
| ByteTrack / BoT-SORT | ByteTrack is enough. BoT-SORT holds ids better on crossings. |

## Known issues
IR night image lowers detection quality. False alerts from animals and car shadows. Reduced by cooldown and minimum time in zone.

## Privacy
No face recognition. People are anonymous track ids. Only events are stored. Video stays on the local recorder.

## Run
```
pip install -r requirements.txt
cp zones.example.json zones.json
python run.py --config zones.json --show
python reconcile.py --orders orders.csv --day 2026-10-15
pytest -q
```

Python, Ultralytics, ByteTrack, OpenCV, SQLite.
