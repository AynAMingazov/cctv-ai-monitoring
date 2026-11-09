# AI monitoring on top of existing CCTV

Computer-vision rules for a small car-service business with several sites (2026).
The cameras were already installed; the goal was to get objective data from them without buying new hardware.
No video with people is published in this repository.

## Problems it solves
| Rule | Question for the owner |
|---|---|
| **Night door** | Did anyone approach the doors after closing? → instant Telegram alert with a snapshot |
| **Entrance counter** | How many customers actually came today? |
| **Visit zone** (oil dispenser) | Who used the oil dispenser, when and for how long? |
| **Hands in zone** (cash desk, shelves) | When were hands active in a sensitive area? Uses wrist keypoints, not just body position |
| **Reconciliation** | Do counted visitors match registered orders? A gap means unregistered (unpaid) visits |

## How it works
```
RTSP camera ─► YOLOv8-pose + ByteTrack (people, track ids, wrist keypoints)
                    │
                    ▼
     rules: NightDoor · LineCounter · ZoneVisit · HandsInZone
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
   SQLite event log     Telegram alert (+ snapshot)
          │
          ▼
   reconcile.py ◄── orders.csv from the office system
```
- Zones and lines are configured per camera in JSON (pixel polygons)
- A person's position is the bottom-centre of the box (where they stand), which is robust to partial occlusion
- Line crossing is counted per track id, so one person is not counted twice
- Night alerts have a cooldown to avoid spam

## Privacy
- Only events and counts are stored; video stays on the company's own recorder
- No face recognition: people are anonymous track ids
- Snapshots are sent only for night alerts

## Run
```bash
pip install -r requirements.txt
cp zones.example.json zones.json      # set the RTSP source and draw your zones
python run.py --config zones.json --show
python reconcile.py --orders orders.csv --day 2026-10-15
pytest -q                             # rules are tested without a camera or a GPU
```

## Stack
Python 3.10+, Ultralytics YOLOv8-pose, ByteTrack, OpenCV, SQLite, Telegram Bot API, pytest
