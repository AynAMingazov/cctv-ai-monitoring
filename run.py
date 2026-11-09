"""Run monitoring on one camera stream (RTSP URL, video file or webcam index).

Usage:
    python run.py --config zones.example.json [--show]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime

import cv2
from ultralytics import YOLO

from monitor.events import EventLog, send_alert
from monitor.rules import LineCounter, NightDoorRule, Person, ZoneVisitRule

LEFT_WRIST, RIGHT_WRIST = 9, 10      # COCO keypoint indices
MIN_KPT_CONF = 0.5


def build_rules(cfg: dict) -> list:
    rules = []
    for z in cfg.get("night_doors", []):
        rules.append(NightDoorRule(z["name"], z["polygon"], z.get("start", "21:00"), z.get("end", "08:00")))
    for line in cfg.get("entrance_lines", []):
        rules.append(LineCounter(line["name"], tuple(line["a"]), tuple(line["b"]), line.get("inside_sign", 1)))
    for z in cfg.get("visit_zones", []):
        rules.append(ZoneVisitRule(z["name"], z["polygon"], z.get("min_seconds", 3), use_wrists=False))
    for z in cfg.get("hand_zones", []):
        rules.append(ZoneVisitRule(z["name"], z["polygon"], z.get("min_seconds", 2), use_wrists=True))
    return rules


def to_people(result) -> list[Person]:
    people = []
    if result.boxes is None or result.boxes.id is None:
        return people
    boxes = result.boxes.xyxy.cpu().numpy()
    ids = result.boxes.id.int().cpu().tolist()
    kpts = result.keypoints
    for i, (box, tid) in enumerate(zip(boxes, ids)):
        wrists = []
        if kpts is not None and kpts.conf is not None:
            xy, conf = kpts.xy[i].cpu().numpy(), kpts.conf[i].cpu().numpy()
            wrists = [tuple(xy[k]) for k in (LEFT_WRIST, RIGHT_WRIST) if conf[k] >= MIN_KPT_CONF]
        people.append(Person(tid, tuple(box), wrists))
    return people


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="zones.example.json")
    ap.add_argument("--show", action="store_true", help="display annotated video")
    args = ap.parse_args()

    cfg = json.load(open(args.config, encoding="utf-8"))
    model = YOLO(cfg.get("model", "yolov8n-pose.pt"))       # pose model: boxes + wrists
    rules = build_rules(cfg)
    log = EventLog(cfg.get("db", "events.db"))
    source = cfg["source"]

    stream = model.track(source=source, stream=True, persist=True, classes=[0],
                         conf=cfg.get("conf", 0.4), vid_stride=cfg.get("frame_step", 2), verbose=False)
    for result in stream:
        now = datetime.now()
        people = to_people(result)
        for rule in rules:
            for event in rule.update(people, now):
                log.add(cfg["camera"], event, now)
                if event.get("alert"):
                    ok, jpg = cv2.imencode(".jpg", result.plot())
                    send_alert(f"[{cfg['camera']}] {event['type']} in {event['zone']} at {now:%H:%M:%S}",
                               jpg.tobytes() if ok else None)
        if args.show:
            cv2.imshow(cfg["camera"], result.plot())
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


if __name__ == "__main__":
    main()
