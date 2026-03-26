import json
import shutil
import subprocess
import time
from pathlib import Path

CAMERA_CONFIG_FILE = Path(__file__).parent.parent / ".camera_config.json"
SNAPSHOT_DIR = Path(__file__).parent.parent / "snapshots"
MOCK_DIR = Path(__file__).parent.parent / "mock_images"


def _ensure_dirs():
    SNAPSHOT_DIR.mkdir(exist_ok=True)


def load_cameras() -> list[dict]:
    if not CAMERA_CONFIG_FILE.exists():
        return []
    with open(CAMERA_CONFIG_FILE) as f:
        return json.load(f)


def save_cameras(cameras: list[dict]):
    with open(CAMERA_CONFIG_FILE, "w") as f:
        json.dump(cameras, f, ensure_ascii=False, indent=2)


def add_camera(name: str, rtsp_url: str) -> dict:
    cameras = load_cameras()
    for cam in cameras:
        if cam["name"] == name:
            cam["rtsp_url"] = rtsp_url
            save_cameras(cameras)
            return {"status": "updated", "name": name, "rtsp_url": rtsp_url}
    cameras.append({"name": name, "rtsp_url": rtsp_url})
    save_cameras(cameras)
    return {"status": "added", "name": name, "rtsp_url": rtsp_url}


def remove_camera(name: str) -> dict:
    cameras = load_cameras()
    filtered = [c for c in cameras if c["name"] != name]
    if len(filtered) == len(cameras):
        return {"status": "not_found", "name": name}
    save_cameras(filtered)
    return {"status": "removed", "name": name}


def list_cameras() -> list[dict]:
    return load_cameras()


def capture_snapshot(name: str) -> dict:
    cameras = load_cameras()
    cam = next((c for c in cameras if c["name"] == name), None)
    if not cam:
        return {"status": "error", "message": f"未找到摄像头 '{name}'"}

    rtsp_url = cam["rtsp_url"]

    if rtsp_url.startswith("mock://"):
        return _mock_snapshot(name, rtsp_url)

    return _rtsp_snapshot(name, rtsp_url)


def _mock_snapshot(name: str, mock_url: str) -> dict:
    mock_path = mock_url.replace("mock://", "")
    source = Path(mock_path) if Path(mock_path).is_absolute() else MOCK_DIR / mock_path

    if not source.exists():
        return {"status": "error", "message": f"Mock 图片不存在: {source}"}

    if source.is_dir():
        images = sorted(source.glob("*.jpg")) + sorted(source.glob("*.png"))
        if not images:
            return {"status": "error", "message": f"Mock 目录中无图片: {source}"}
        source = images[int(time.time()) % len(images)]

    _ensure_dirs()
    ts = int(time.time())
    dest = SNAPSHOT_DIR / f"{name}_{ts}{source.suffix}"
    shutil.copy2(source, dest)
    return {"status": "ok", "name": name, "path": str(dest.resolve()), "source": "mock"}


def _rtsp_snapshot(name: str, rtsp_url: str) -> dict:
    if not shutil.which("ffmpeg"):
        return {"status": "error", "message": "ffmpeg 未安装，请先 brew install ffmpeg"}

    _ensure_dirs()
    ts = int(time.time())
    dest = SNAPSHOT_DIR / f"{name}_{ts}.jpg"

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-rtsp_transport", "tcp",
                "-i", rtsp_url,
                "-frames:v", "1",
                "-q:v", "2",
                str(dest),
            ],
            capture_output=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "RTSP 截图超时（15秒）"}

    if not dest.exists():
        return {"status": "error", "message": "截图失败，请检查 RTSP 地址是否可访问"}

    return {"status": "ok", "name": name, "path": str(dest.resolve()), "source": "rtsp"}
