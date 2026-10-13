from __future__ import annotations

import argparse
import json
import shutil
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


DIFFUSION = "qwen_image_layered_fp8mixed.safetensors"
TEXT_ENCODER = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
VAE = "qwen_image_layered_vae.safetensors"


def request_json(url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def workflow(args: argparse.Namespace, input_name: str, prefix: str) -> dict:
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": input_name}},
        "2": {"class_type": "ImageScaleToMaxDimension", "inputs": {"image": ["1", 0], "upscale_method": "lanczos", "largest_size": args.max_dimension}},
        "3": {"class_type": "GetImageSize", "inputs": {"image": ["2", 0]}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": TEXT_ENCODER, "type": "qwen_image", "device": "default"}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 0], "text": ""}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 0], "text": args.prompt}},
        "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["5", 0]}},
        "9": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["6", 0], "latent": ["8", 0]}},
        "10": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["7", 0], "latent": ["8", 0]}},
        "11": {"class_type": "UNETLoader", "inputs": {"unet_name": DIFFUSION, "weight_dtype": "default"}},
        "12": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["11", 0], "shift": 1.0}},
        "13": {"class_type": "EmptyQwenImageLayeredLatentImage", "inputs": {"width": ["3", 0], "height": ["3", 1], "layers": args.layers, "batch_size": 1}},
        "14": {"class_type": "KSampler", "inputs": {"model": ["12", 0], "positive": ["10", 0], "negative": ["9", 0], "latent_image": ["13", 0], "seed": args.seed, "steps": args.steps, "cfg": args.cfg, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "15": {"class_type": "LatentCut", "inputs": {"samples": ["14", 0], "dim": "t", "index": 1, "amount": 16384}},
        "16": {"class_type": "LatentCutToBatch", "inputs": {"samples": ["15", 0], "dim": "t", "slice_size": 1}},
        "17": {"class_type": "VAEDecode", "inputs": {"samples": ["16", 0], "vae": ["5", 0]}},
        "18": {"class_type": "SaveImage", "inputs": {"images": ["17", 0], "filename_prefix": prefix + "/layers/layer"}},
        "19": {"class_type": "LatentCut", "inputs": {"samples": ["14", 0], "dim": "t", "index": 0, "amount": 1}},
        "20": {"class_type": "VAEDecode", "inputs": {"samples": ["19", 0], "vae": ["5", 0]}},
        "21": {"class_type": "SaveImage", "inputs": {"images": ["20", 0], "filename_prefix": prefix + "/full/full"}},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Qwen-Image-Layered through a local ComfyUI API.")
    parser.add_argument("--comfy-root", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-dimension", type=int, default=1024)
    parser.add_argument("--layers", type=int, default=8)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--cfg", type=float, default=2.5)
    parser.add_argument("--seed", type=int, default=777)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--save-request", type=Path)
    args = parser.parse_args()

    source = args.input.resolve()
    comfy = args.comfy_root.resolve()
    destination = args.output_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if not (comfy / "main.py").is_file():
        raise FileNotFoundError(f"Not a ComfyUI root: {comfy}")
    run_id = "ps-ai-layer-" + uuid.uuid4().hex[:12]
    input_name = run_id + source.suffix.lower()
    comfy_input = comfy / "input" / input_name
    comfy_input.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, comfy_input)

    graph = workflow(args, input_name, run_id)
    payload = {"prompt": graph, "client_id": run_id}
    request_path = args.save_request or destination / "request.json"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    response = request_json(args.server.rstrip("/") + "/prompt", payload)
    prompt_id = response["prompt_id"]
    print(json.dumps({"status": "queued", "prompt_id": prompt_id, "run_id": run_id}, ensure_ascii=False))

    deadline = time.monotonic() + args.timeout
    record = None
    while time.monotonic() < deadline:
        history = request_json(args.server.rstrip("/") + f"/history/{prompt_id}")
        if prompt_id in history:
            record = history[prompt_id]
            status = record.get("status", {})
            if status.get("status_str") == "error":
                print(json.dumps(record, ensure_ascii=False, indent=2))
                return 2
            break
        time.sleep(2)
    if record is None:
        raise TimeoutError(f"Workflow did not finish in {args.timeout} seconds")

    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for node_id, node_output in record.get("outputs", {}).items():
        for item in node_output.get("images", []):
            kind = item.get("type", "output")
            if kind != "output":
                continue
            source_file = comfy / "output" / item.get("subfolder", "") / item["filename"]
            category = "layers" if node_id == "18" else "full"
            target_folder = destination / category
            target_folder.mkdir(parents=True, exist_ok=True)
            target = target_folder / item["filename"]
            shutil.copy2(source_file, target)
            copied.append({"node": node_id, "category": category, "path": str(target), "bytes": target.stat().st_size})
    receipt = {"schema": "qwen_layered_run_receipt_v1", "status": "success", "prompt_id": prompt_id, "run_id": run_id, "source": str(source), "parameters": {"max_dimension": args.max_dimension, "layers": args.layers, "steps": args.steps, "cfg": args.cfg, "seed": args.seed}, "outputs": copied}
    (destination / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
