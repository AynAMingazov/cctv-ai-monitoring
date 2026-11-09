# cctv-ai-monitoring

Scripts that use cameras which were already installed in a car service. Owner has several places and cant watch all cameras, so I tried to make cameras "understand" a bit what happens.

No video with people here, only code and example config.

## What it does
- **night doors** - after closing time if someone comes close to the door, owner gets message in Telegram with a photo
- **counting customers** - line at the entrance, counts people going in
- **oil dispenser** - writes who stood at the oil zone and how long
- **hands in zone** - checks wrists, not the body. Useful for cash desk or shelves
- **reconcile** - compare how many customers camera counted with how many orders were made in the office. If camera saw 5 and office made 3 orders, there is a question :)

## How it works
Camera (RTSP) -> YOLOv8-pose finds people and wrists -> ByteTrack gives each person id -> my rules check zones and lines -> events go to SQLite and alerts to Telegram.

Position of a person is the bottom middle of the box (where legs are). It works better than center of the box when person is partly behind a car.

## Which AI to use (my opinion)
- **YOLOv8n-pose** - I use it because it gives boxes and keypoints in one model and works on usual PC without big GPU. n version is fast, s version is more accurate
- **YOLO11** - newer, a bit better accuracy, same API in ultralytics, I want to switch
- **RT-DETR** - more accurate for crowded scenes but slower
- **MediaPipe Hands** - more detailed hands, but bad from ceiling cameras with low resolution
- **ByteTrack** vs **BoT-SORT** - ByteTrack was enough, BoT-SORT keeps ids better when people cross each other

Problems I saw: at night IR camera image is grey and detection is worse, false alarms from cats and from shadows of cars. Cooldown and minimal time in zone helped a lot.

## Privacy
I think this part is important. No face recognition, people are just numbers. Only events and counts are saved, video stays on the company recorder. Photo is sent only for night alerts.

## Run
```
pip install -r requirements.txt
cp zones.example.json zones.json   # put your rtsp and zones
python run.py --config zones.json --show
python reconcile.py --orders orders.csv --day 2026-10-15
pytest -q
```

Stack: Python, ultralytics YOLOv8-pose, ByteTrack, OpenCV, SQLite, Telegram API
