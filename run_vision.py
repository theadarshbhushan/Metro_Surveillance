"""Edge vision process: camera/video -> YOLO -> seat occupancy -> telemetry -> Flask.

    python run_vision.py --source videos/coach.mp4       # recorded video
    python run_vision.py --source camera                  # Pi camera / CAMERA_SOURCE
    python run_vision.py --source 0                       # USB webcam
    python run_vision.py --source rtsp://host/stream      # CCTV stream

Defaults come from environment variables (see vision/settings.py); flags override them.
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vision.settings import load_settings  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="video file, 'camera', webcam index or stream URL")
    ap.add_argument("--coach-id", dest="coach_id")
    ap.add_argument("--backend-url", dest="backend_url")
    ap.add_argument("--model", dest="model_path")
    ap.add_argument("--conf", dest="confidence_threshold", type=float)
    ap.add_argument("--imgsz", dest="inference_size", type=int)
    ap.add_argument("--frame-skip", dest="frame_skip", type=int)
    ap.add_argument("--seat-config", dest="seat_config_path")
    ap.add_argument("--occupancy-confirm", dest="occupancy_confirm_frames", type=int)
    ap.add_argument("--empty-confirm", dest="empty_confirm_frames", type=int)
    ap.add_argument("--show", action="store_true", help="show the annotated preview window")
    ap.add_argument("--debug", action="store_true", help="log FPS statistics")
    ap.add_argument("--loop", action="store_true", help="loop a video file forever")
    ap.add_argument("--realtime", action="store_true", help="pace a video file at its native FPS")
    ap.add_argument("--no-send", action="store_true", help="do not send telemetry to the backend")
    ap.add_argument("--max-frames", type=int, help="stop after N processed frames")
    ap.add_argument("--save-video", help="write the annotated video to this path")
    ap.add_argument("--ground-truth", help="JSON {frame: actual_people} for a hand-annotated video")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("run_vision")

    # heavy imports after argument parsing so --help is instant
    import cv2
    from vision.camera import open_source
    from vision.detector import PersonDetector
    from vision.ground_truth import compute_metrics, load_frame_annotations
    from vision.pipeline import Pipeline
    from vision.seat_mapper import SeatMapper
    from vision.telemetry_client import TelemetryClient

    settings = load_settings().with_overrides(
        coach_id=args.coach_id, backend_url=args.backend_url, model_path=args.model_path,
        confidence_threshold=args.confidence_threshold, inference_size=args.inference_size,
        frame_skip=args.frame_skip, seat_config_path=args.seat_config_path,
        occupancy_confirm_frames=args.occupancy_confirm_frames, empty_confirm_frames=args.empty_confirm_frames,
    )

    try:
        source = open_source(args.source, loop=args.loop)
    except (OSError, ValueError) as exc:
        log.error("Cannot open source '%s': %s", args.source, exc)
        return 1

    mapper = SeatMapper.from_file(settings.seat_config_path, settings.coach_id)
    if mapper is None:
        log.warning("No seats configured for %s in %s: seat states will be empty and every person "
                    "will count as standing/unknown. Run tools/seat_mapper.py.", settings.coach_id,
                    settings.seat_config_path)

    annotations = None
    if args.ground_truth:
        try:
            annotations = load_frame_annotations(args.ground_truth)
        except (OSError, ValueError) as exc:
            log.error("Ignoring ground-truth file: %s", exc)

    client = None if args.no_send else TelemetryClient(settings.backend_url, settings.coach_id,
                                                       timeout=settings.request_timeout)
    pipeline = Pipeline(settings, source, detector_factory=lambda: PersonDetector(settings),
                        mapper=mapper, client=client, annotations=annotations)

    writer = None
    if args.save_video:
        ok, frame = source.read()
        if ok:
            h, w = frame.shape[:2]
            writer = cv2.VideoWriter(args.save_video, cv2.VideoWriter_fourcc(*"mp4v"), 15.0, (w, h))
            if hasattr(source, "_cap"):  # rewind the video file we just peeked at
                source._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                source._index = 0

    log.info("Starting: source=%s coach=%s model=%s backend=%s", args.source, settings.coach_id,
             settings.model_path, "disabled" if client is None else settings.backend_url)
    pipeline.run(show=args.show, max_frames=args.max_frames, debug=args.debug, writer=writer,
                 realtime=args.realtime)
    if writer is not None:
        writer.release()

    if pipeline.local_samples:
        log.info("Ground-truth metrics from %s: %s", args.ground_truth, compute_metrics(pipeline.local_samples))
    elif annotations:
        log.warning("Annotation file given but no annotated frame was processed (frame skip?)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
