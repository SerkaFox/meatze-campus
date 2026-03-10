import json
import os
import subprocess
from pathlib import Path

import requests
from PIL import Image

COMFY_BASE = os.getenv("COMFY_BASE", "http://127.0.0.1:8188").rstrip("/")
WORKFLOW_VIDEO = os.getenv("COMFY_WORKFLOW_VIDEO", "/home/iaadmin/tg_comfy_bot/workflow_video.json")
WORKFLOW_IMAGE = os.getenv("COMFY_WORKFLOW_IMAGE", "/home/iaadmin/tg_comfy_bot/workflow_image.json")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))
ROUND_TO = int(os.getenv("ROUND_TO", "64"))

VIDEO_QUALITY_PRESETS = {
    "low": (640, 384),
    "medium": (768, 448),
    "high": (1024, 576),
}

VIDEO_QUALITY_PRESETS_16_9 = {
    "low": (640, 360),
    "medium": (768, 432),
    "high": (1024, 576),
}

IMAGE_QUALITY_PRESETS = {
    "low": 640,
    "medium": 768,
    "high": 1024,
}


def round_to_multiple(v: int, m: int) -> int:
    return max(m, int(round(v / m) * m))


def fit_size_keep_aspect(width: int, height: int, max_side: int, multiple: int = ROUND_TO) -> tuple[int, int]:
    w, h = int(width), int(height)
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        w = max(1, int(w * scale))
        h = max(1, int(h * scale))
    w = round_to_multiple(w, multiple)
    h = round_to_multiple(h, multiple)
    return max(multiple, w), max(multiple, h)


def inspect_image_size(path: str) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def inspect_image_for_photo(path: str, quality: str) -> tuple[int, int, int, int]:
    ow, oh = inspect_image_size(path)
    fw, fh = fit_size_keep_aspect(ow, oh, IMAGE_QUALITY_PRESETS.get(quality, 768))
    return ow, oh, fw, fh


def inspect_image_for_video(path: str, quality: str, aspect_ratio: str = "original") -> tuple[int, int, int, int]:
    ow, oh = inspect_image_size(path)
    if aspect_ratio == "16:9":
        target_w, target_h = VIDEO_QUALITY_PRESETS_16_9.get(quality, (768, 432))
    else:
        target_w, target_h = VIDEO_QUALITY_PRESETS.get(quality, (768, 448))
    return ow, oh, target_w, target_h


def make_seed() -> int:
    return int.from_bytes(os.urandom(8), "big") & ((1 << 53) - 1)


def read_workflow(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def patch_video_workflow(
    wf: dict,
    *,
    prompt: str,
    image_name: str,
    width: int,
    height: int,
    seconds: int,
    seed: int,
) -> dict:
    wf = json.loads(json.dumps(wf))
    wf["93"]["inputs"]["text"] = prompt
    wf["385"]["inputs"]["image"] = image_name
    wf["164"]["inputs"]["value"] = int(width)
    wf["165"]["inputs"]["value"] = int(height)
    wf["243"]["inputs"]["value"] = int(seconds)
    wf["141"]["inputs"]["seed"] = int(seed)
    return wf


def patch_image_workflow(
    wf: dict,
    *,
    prompt: str,
    image_names: list[str],
    seed: int,
) -> dict:
    wf = json.loads(json.dumps(wf))

    wf["435"]["inputs"]["value"] = prompt
    wf["433:3"]["inputs"]["seed"] = int(seed)

    if len(image_names) >= 1:
        wf["78"]["inputs"]["image"] = image_names[0]
    if len(image_names) >= 2:
        wf["436"]["inputs"]["image"] = image_names[1]
    if len(image_names) >= 3:
        wf["437"]["inputs"]["image"] = image_names[2]

    return wf


def upload_image_file(local_path: str, filename: str) -> str:
    with open(local_path, "rb") as f:
        files = {"image": (filename, f, "application/octet-stream")}
        data = {"overwrite": "true", "type": "input"}
        r = requests.post(f"{COMFY_BASE}/upload/image", files=files, data=data, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json().get("name", filename)


def queue_prompt(prompt: dict, client_id: str) -> str:
    r = requests.post(
        f"{COMFY_BASE}/prompt",
        json={"prompt": prompt, "client_id": client_id},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    if "prompt_id" not in data:
        raise RuntimeError(f"ComfyUI prompt error: {data}")
    return data["prompt_id"]


def get_history(prompt_id: str) -> dict:
    r = requests.get(f"{COMFY_BASE}/history/{prompt_id}", timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def pick_video_result(history_item: dict) -> dict | None:
    outputs = history_item.get("outputs") or {}
    if "314" in outputs:
        node = outputs["314"]
        for key in ("gifs", "images"):
            arr = node.get(key, [])
            if arr:
                return arr[0]
    for node in outputs.values():
        for key in ("gifs", "images"):
            arr = node.get(key, [])
            if arr:
                return arr[0]
    return None


def pick_image_result(history_item: dict) -> dict | None:
    outputs = history_item.get("outputs") or {}
    if "60" in outputs:
        node = outputs["60"]
        for key in ("images", "gifs"):
            arr = node.get(key, [])
            if arr:
                return arr[0]
    for node in outputs.values():
        for key in ("images", "gifs"):
            arr = node.get(key, [])
            if arr:
                return arr[0]
    return None


def fetch_file_bytes(filename: str, subfolder: str = "", file_type: str = "output") -> bytes:
    r = requests.get(
        f"{COMFY_BASE}/view",
        params={"filename": filename, "subfolder": subfolder, "type": file_type},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.content


def extract_last_frame(video_path: str, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-sseof",
            "-0.1",
            "-i",
            video_path,
            "-update",
            "1",
            "-q:v",
            "1",
            output_path,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )