#!/usr/bin/env python3
"""Diagnostic detail-feature scan for Scene Kit selected ten-view sets.

The script uses Florence-2 for detailed captions and phrase grounding, then
uses an optional ViLT visual-question-answering pass for representative crops.
It writes evidence and annotated review sheets only. It never edits project
state, never writes ``components.detail_audit``, and never marks a stage pass.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont


CONCEPT_VIEW_IDS = (
    "top",
    "bottom",
    "left",
    "right",
    "front",
    "back",
    "front_left_45",
    "front_right_45",
    "back_left_45",
    "back_right_45",
)
DEFAULT_FEATURE_PHRASES = (
    "chimney, window, door, balcony, railing, plant, vine, lantern, "
    "decoration, carving, steps, roof, tower"
)
FEATURE_COLORS = {
    "window": (0, 220, 255),
    "door": (255, 70, 70),
    "chimney": (255, 205, 0),
    "balcony": (70, 230, 100),
    "railing": (40, 180, 90),
    "lantern": (255, 145, 0),
    "steps": (245, 60, 220),
    "vine": (20, 170, 50),
    "plant": (20, 170, 50),
    "tower": (80, 120, 255),
    "roof": (160, 160, 160),
}
VQA_QUESTIONS = {
    "chimney": ("Is this a chimney?", "Is this a tower?"),
    "door": ("Is the door wooden?",),
    "steps": ("Are there steps?",),
    "railing": ("Is there a railing?", "Is the railing wooden?"),
    "lantern": ("Are there lamps?",),
    "plant": ("Is there a plant?",),
    "vine": ("Is there a vine?",),
    "tower": ("Is there a tower?",),
    "balcony": ("Is there a balcony?",),
    "window": (
        "Are there 16 window panes?",
        "Are there four columns of panes?",
        "Are there two narrow panes in the center?",
        "Does the center have four rows?",
        "Are there three major vertical sections?",
        "Is there a horizontal transom?",
        "Is the window frame painted black?",
        "Is the window made of wood?",
    ),
}


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} 必须是 JSON 对象")
    return value


def resolve_selected_views(project: Path) -> tuple[str, dict[str, Path]]:
    concepts = read_json(project / "internal" / "concept_directions.json")
    selected_id = concepts.get("selected_direction")
    selected = next(
        (
            direction
            for direction in concepts.get("directions", [])
            if direction.get("direction_id") == selected_id
        ),
        None,
    )
    if not isinstance(selected, dict):
        raise ValueError("找不到已选中的概念方向")

    raw_paths = selected.get("view_paths")
    if not isinstance(raw_paths, dict):
        raise ValueError("选中方向缺少 view_paths")
    resolved: dict[str, Path] = {}
    missing: list[str] = []
    for view_id in CONCEPT_VIEW_IDS:
        relative = raw_paths.get(view_id)
        if not isinstance(relative, str) or not relative.strip():
            missing.append(f"{view_id}: 路径为空")
            continue
        path = (project / relative).resolve()
        if not path.is_file():
            missing.append(f"{view_id}: {relative}")
            continue
        resolved[view_id] = path
    if missing:
        raise ValueError("选中方向图片不完整：" + "；".join(missing))
    return selected_id, resolved


def resolve_view_source(
    project: Path,
    view_dir: Path | None,
    view_map: Path | None,
) -> tuple[str, dict[str, Path]]:
    """Resolve either the original selected views or model-derived views."""
    if view_dir is not None and view_map is not None:
        raise ValueError("--view-dir 和 --view-map 不能同时使用")
    if view_map is not None:
        mapping_path = view_map.resolve()
        value = read_json(mapping_path)
        resolved: dict[str, Path] = {}
        for view_id in CONCEPT_VIEW_IDS:
            raw = value.get(view_id)
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"view map 缺少 {view_id}")
            path = Path(raw)
            if not path.is_absolute():
                path = project / path
            path = path.resolve()
            if not path.is_file():
                raise ValueError(f"{view_id} 图片不存在：{path}")
            resolved[view_id] = path
        return "model_derived_views", resolved
    if view_dir is not None:
        directory = view_dir.resolve()
        resolved = {}
        for view_id in CONCEPT_VIEW_IDS:
            path = directory / f"{view_id}.png"
            if not path.is_file():
                path = directory / f"{view_id}.jpg"
            if not path.is_file():
                raise ValueError(f"{view_id} 派生视图不存在")
            resolved[view_id] = path
        return "model_derived_views", resolved
    return resolve_selected_views(project)


def clamp_box(
    box: Iterable[float],
    width: int,
    height: int,
    padding_ratio: float = 0.10,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = (float(value) for value in box)
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    pad = max(4.0, max(x2 - x1, y2 - y1) * padding_ratio)
    return (
        max(0, int(round(x1 - pad))),
        max(0, int(round(y1 - pad))),
        min(width, int(round(x2 + pad))),
        min(height, int(round(y2 + pad))),
    )


def summarize_grounding(
    results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    per_view: dict[str, dict[str, int]] = {}
    aggregate: dict[str, dict[str, int]] = defaultdict(
        lambda: {"max": 0, "min": sys.maxsize, "views_seen": 0}
    )
    for view_id in CONCEPT_VIEW_IDS:
        parsed = (
            results.get(view_id, {})
            .get("parsed", {})
            .get("<CAPTION_TO_PHRASE_GROUNDING>", {})
        )
        labels = parsed.get("labels", [])
        counts = dict(Counter(label for label in labels if isinstance(label, str)))
        per_view[view_id] = counts
        for label, count in counts.items():
            item = aggregate[label]
            item["max"] = max(item["max"], count)
            item["min"] = min(item["min"], count)
            item["views_seen"] += 1
    for item in aggregate.values():
        if item["min"] == sys.maxsize:
            item["min"] = 0
    return {"per_view": per_view, "aggregate": dict(aggregate)}


def representative_detections(
    results: dict[str, dict[str, Any]],
    priority: tuple[str, ...] = (
        "front",
        "right",
        "left",
        "top",
        "front_right_45",
        "front_left_45",
    ),
) -> dict[str, dict[str, Any]]:
    chosen: dict[str, dict[str, Any]] = {}
    ordered_views = priority + tuple(
        view_id for view_id in CONCEPT_VIEW_IDS if view_id not in priority
    )
    for view_id in ordered_views:
        parsed = (
            results.get(view_id, {})
            .get("parsed", {})
            .get("<CAPTION_TO_PHRASE_GROUNDING>", {})
        )
        labels = parsed.get("labels", [])
        boxes = parsed.get("bboxes", [])
        for label, box in zip(labels, boxes):
            if label not in chosen:
                chosen[label] = {"view_id": view_id, "box": box}
    return chosen


def grouped_detections(
    results: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for view_id in CONCEPT_VIEW_IDS:
        parsed = (
            results.get(view_id, {})
            .get("parsed", {})
            .get("<CAPTION_TO_PHRASE_GROUNDING>", {})
        )
        labels = parsed.get("labels", [])
        boxes = parsed.get("bboxes", [])
        for label, box in zip(labels, boxes):
            if not isinstance(label, str):
                continue
            grouped[label].append({"view_id": view_id, "box": box})
    return dict(grouped)


def dominant_palette(image: Image.Image, colors: int = 8) -> list[dict[str, Any]]:
    sample = image.convert("RGB")
    sample.thumbnail((96, 96), Image.Resampling.LANCZOS)
    quantized = sample.quantize(
        colors=max(2, colors),
        method=Image.Quantize.MEDIANCUT,
    )
    raw_palette = quantized.getpalette() or []
    output: list[dict[str, Any]] = []
    counts = quantized.getcolors(maxcolors=colors * 4) or []
    for count, index in sorted(counts, reverse=True):
        offset = index * 3
        if offset + 2 >= len(raw_palette):
            continue
        rgb = raw_palette[offset : offset + 3]
        output.append(
            {
                "rgb": rgb,
                "hex": "#" + "".join(f"{value:02X}" for value in rgb),
                "sample_ratio": round(
                    count / max(1, sample.width * sample.height),
                    4,
                ),
            }
        )
    return output


def _line_profiles(
    image: Image.Image,
) -> tuple[list[float], list[float], int, int]:
    gray = image.convert("L")
    width, height = gray.size
    x_margin = max(2, width // 12)
    y_margin = max(2, height // 12)
    pixels = gray.load()
    vertical: list[float] = []
    horizontal: list[float] = []
    for x in range(x_margin, width - x_margin):
        score = 0.0
        for y in range(y_margin, height - y_margin):
            score += abs(pixels[x + 1, y] - pixels[x - 1, y])
        vertical.append(score / max(1, height - 2 * y_margin))
    for y in range(y_margin, height - y_margin):
        score = 0.0
        for x in range(x_margin, width - x_margin):
            score += abs(pixels[x, y + 1] - pixels[x, y - 1])
        horizontal.append(score / max(1, width - 2 * x_margin))
    return vertical, horizontal, x_margin, y_margin


def _candidate_line_ratios(
    profile: list[float],
    offset: int,
    full_size: int,
    limit: int = 20,
) -> list[float]:
    if not profile:
        return []
    smoothed = [
        sum(profile[max(0, index - 1) : index + 2])
        / len(profile[max(0, index - 1) : index + 2])
        for index in range(len(profile))
    ]
    ordered = sorted(smoothed)
    threshold = ordered[int(len(ordered) * 0.72)]
    candidates: list[tuple[float, int]] = []
    for index, score in enumerate(smoothed):
        left = smoothed[max(0, index - 2) : index]
        right = smoothed[index + 1 : index + 3]
        if score < threshold or score < 4.0:
            continue
        if left and score < max(left):
            continue
        if right and score < max(right):
            continue
        candidates.append((score, index + offset))
    candidates.sort(reverse=True)
    positions = sorted(index for _, index in candidates[:limit])
    return [
        round(min(1.0, max(0.0, index / max(1, full_size))), 4)
        for index in positions
    ]


def analyze_fine_structure(image: Image.Image) -> dict[str, Any]:
    """Return conservative line-profile evidence for repeated lattice details."""
    vertical, horizontal, x_margin, y_margin = _line_profiles(image)
    return {
        "status": "diagnostic_only",
        "method": "luminance directional-gradient line profile",
        "vertical_line_ratios": _candidate_line_ratios(
            vertical,
            x_margin,
            image.width,
        ),
        "horizontal_line_ratios": _candidate_line_ratios(
            horizontal,
            y_margin,
            image.height,
        ),
        "note": (
            "候选线位只用于放大后人工/视觉模型交叉复核；"
            "不能直接把数量写入 detail_audit。"
        ),
    }


def annotate_view(
    image_path: Path,
    parsed: dict[str, Any],
    output_path: Path,
) -> None:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(
            "C:/Windows/Fonts/arialbd.ttf",
            max(16, image.width // 90),
        )
    except OSError:
        font = ImageFont.load_default()

    labels = parsed.get("labels", [])
    boxes = parsed.get("bboxes", [])
    counts: Counter[str] = Counter()
    for label, box in zip(labels, boxes):
        if not isinstance(label, str):
            continue
        counts[label] += 1
        color = FEATURE_COLORS.get(label, (255, 255, 255))
        x1, y1, x2, y2 = clamp_box(box, image.width, image.height, 0.0)
        draw.rectangle(
            (x1, y1, x2, y2),
            outline=color,
            width=max(2, image.width // 350),
        )
    if counts:
        summary = " | ".join(f"{key}:{value}" for key, value in sorted(counts.items()))
        draw.rectangle((0, 0, image.width, max(36, image.height // 35)), fill=(18, 18, 18))
        draw.text(
            (image.width // 80, image.height // 120),
            summary,
            font=font,
            fill=(245, 245, 245),
        )
    image.save(output_path, quality=92)


def make_contact_sheet(image_paths: list[Path], output_path: Path) -> None:
    if not image_paths:
        return
    thumb_w, thumb_h = 600, 400
    margin = 16
    cols = 2
    rows = (len(image_paths) + cols - 1) // cols
    canvas = Image.new(
        "RGB",
        (cols * thumb_w + (cols + 1) * margin, rows * (thumb_h + 34) + (rows + 1) * margin),
        (235, 235, 233),
    )
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    for index, path in enumerate(image_paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        col = index % cols
        row = index // cols
        x = margin + col * (thumb_w + margin)
        y = margin + row * (thumb_h + 34 + margin)
        tile = Image.new("RGB", (thumb_w, thumb_h), (245, 245, 243))
        tile.paste(image, ((thumb_w - image.width) // 2, (thumb_h - image.height) // 2))
        canvas.paste(tile, (x, y))
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + 34), fill=(30, 30, 28))
        draw.text((x + 10, y + thumb_h + 7), path.stem.upper(), font=font, fill=(245, 245, 240))
    canvas.save(output_path, quality=92, optimize=True)


def collect_multi_view_crops(
    project: Path,
    views: dict[str, Path],
    results: dict[str, dict[str, Any]],
    output_dir: Path,
    padding_ratio: float,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, Any] = {}
    priority = (
        "front",
        "back",
        "left",
        "right",
        "front_left_45",
        "front_right_45",
        "back_left_45",
        "back_right_45",
        "top",
        "bottom",
    )
    for label, detections in sorted(grouped_detections(results).items()):
        per_view: dict[str, dict[str, Any]] = {}
        crop_paths: list[Path] = []
        for view_id in priority:
            detection = next(
                (
                    item
                    for item in detections
                    if item["view_id"] == view_id
                ),
                None,
            )
            if detection is None:
                continue
            source = Image.open(views[view_id]).convert("RGB")
            box = clamp_box(
                detection["box"],
                source.width,
                source.height,
                padding_ratio,
            )
            crop = source.crop(box)
            path = output_dir / f"{label}_{view_id}.png"
            crop.save(path)
            crop_paths.append(path)
            per_view[view_id] = {
                "crop": str(path.relative_to(project)),
                "palette": dominant_palette(crop),
                "size": list(crop.size),
            }
        if not per_view:
            continue
        contact = output_dir.parent / f"{label}_multi_view_contact_sheet.jpg"
        if len(crop_paths) >= 2:
            make_contact_sheet(crop_paths, contact)
        evidence[label] = {
            "view_count": len(per_view),
            "views": per_view,
            "contact_sheet": (
                str(contact.relative_to(project))
                if contact.is_file()
                else None
            ),
        }
    return evidence


def run(args: argparse.Namespace) -> int:
    project = args.project.resolve()
    selected_id, views = resolve_view_source(
        project,
        args.view_dir,
        args.view_map,
    )
    output_dir = (args.output_dir or project / "preview" / "detail-scan").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    crops_dir = output_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)

    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass

    try:
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoProcessor,
            ViltForQuestionAnswering,
            ViltProcessor,
        )
    except ImportError as exc:
        print(
            "缺少视觉审计依赖。请阅读 references/detail-vision-audit.md "
            "创建独立虚拟环境并固定 transformers==4.48.3。",
            file=sys.stderr,
        )
        return 2

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    local_only = args.offline

    florence_processor = AutoProcessor.from_pretrained(
        args.florence_model,
        trust_remote_code=True,
        local_files_only=local_only,
    )
    florence_model = AutoModelForCausalLM.from_pretrained(
        args.florence_model,
        trust_remote_code=True,
        torch_dtype=dtype,
        local_files_only=local_only,
    ).to(device)
    florence_model.eval()

    def florence(image: Image.Image, task: str) -> dict[str, Any]:
        inputs = florence_processor(text=task, images=image, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            generated = florence_model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=args.max_new_tokens,
                num_beams=args.num_beams,
            )
        text = florence_processor.batch_decode(
            generated,
            skip_special_tokens=False,
        )[0]
        parse_task = task.split(">", 1)[0] + ">"
        return {
            "raw": text,
            "parsed": florence_processor.post_process_generation(
                text,
                task=parse_task,
                image_size=image.size,
            ),
        }

    audit: dict[str, Any] = {
        "status": "diagnostic_only",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "project": str(project),
        "selected_direction": selected_id,
        "florence_model": args.florence_model,
        "vqa_model": None if args.skip_vqa else args.vqa_model,
        "device": device,
        "views": {},
    }

    for view_id, image_path in views.items():
        image = Image.open(image_path).convert("RGB")
        caption = florence(image, "<MORE_DETAILED_CAPTION>")
        grounding = florence(
            image,
            f"<CAPTION_TO_PHRASE_GROUNDING>{args.feature_phrases}",
        )
        audit["views"][view_id] = {
            "path": str(image_path.relative_to(project)),
            "caption": caption,
            "grounding": grounding,
        }
        print(f"{view_id}: caption and grounding complete", flush=True)

    grounding_results = {
        view_id: record["grounding"] for view_id, record in audit["views"].items()
    }
    audit["grounding_summary"] = summarize_grounding(grounding_results)

    annotated_paths: list[Path] = []
    for view_id, record in audit["views"].items():
        parsed = (
            record["grounding"]["parsed"].get(
                "<CAPTION_TO_PHRASE_GROUNDING>",
                {},
            )
        )
        output_path = output_dir / f"annotated_{view_id}.jpg"
        annotate_view(views[view_id], parsed, output_path)
        annotated_paths.append(output_path)
    make_contact_sheet(annotated_paths, output_dir / "annotated-overview.jpg")
    multi_view_evidence = collect_multi_view_crops(
        project,
        views,
        grounding_results,
        crops_dir / "multi_view",
        args.crop_padding,
    )
    audit["multi_view_evidence"] = multi_view_evidence

    representatives = representative_detections(grounding_results)
    focused: dict[str, Any] = {}
    fine_structure_candidates: dict[str, Any] = {}
    if not args.skip_focused_crops:
        for label, detection in sorted(representatives.items()):
            view_id = detection["view_id"]
            source = Image.open(views[view_id]).convert("RGB")
            box = clamp_box(
                detection["box"],
                source.width,
                source.height,
                args.crop_padding,
            )
            crop = source.crop(box)
            crop_path = crops_dir / f"{label}_{view_id}.png"
            crop.save(crop_path)
            caption = florence(crop, "<MORE_DETAILED_CAPTION>")
            focused[label] = {
                "source_view": view_id,
                "box": list(box),
                "crop": str(crop_path.relative_to(project)),
                "caption": caption,
            }
            fine_structure_candidates[label] = {
                "source_view": view_id,
                "crop": str(crop_path.relative_to(project)),
                "analysis": analyze_fine_structure(crop),
            }
            if label == "window":
                enlarged_path = crops_dir / f"window_{view_id}_detail_4x.png"
                crop.resize(
                    (crop.width * 4, crop.height * 4),
                    Image.Resampling.LANCZOS,
                ).save(enlarged_path)
                focused[label]["detail_closeup"] = str(
                    enlarged_path.relative_to(project)
                )
            print(f"focused crop: {label} ({view_id})", flush=True)

    if not args.skip_vqa:
        vqa_processor = ViltProcessor.from_pretrained(
            args.vqa_model,
            local_files_only=local_only,
        )
        vqa_model = ViltForQuestionAnswering.from_pretrained(
            args.vqa_model,
            local_files_only=local_only,
        ).to(device)
        vqa_model.eval()
        for label, record in focused.items():
            questions = VQA_QUESTIONS.get(label)
            if not questions:
                continue
            crop_path = project / record["crop"]
            image = Image.open(crop_path).convert("RGB")
            answers: dict[str, str] = {}
            for question in questions:
                encoded = vqa_processor(image, question, return_tensors="pt")
                encoded = {key: value.to(device) for key, value in encoded.items()}
                with torch.no_grad():
                    output = vqa_model(**encoded)
                answers[question] = vqa_model.config.id2label[
                    output.logits.argmax(-1).item()
                ]
            record["vqa"] = answers
            print(f"vqa: {label} {answers}", flush=True)

    (output_dir / "detail_vision_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "focused_detail_audit.json").write_text(
        json.dumps(focused, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "fine_structure_candidates.json").write_text(
        json.dumps(
            fine_structure_candidates,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "multi_view_evidence.json").write_text(
        json.dumps(multi_view_evidence, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Evidence written to {output_dir}", flush=True)
    print(
        "Diagnostic only: inspect disagreements and multi-view counts before "
        "writing components.detail_audit.",
        flush=True,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Scene Kit visual detail-audit evidence without changing project state."
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--view-dir",
        type=Path,
        help="Canonical ten-view directory rendered from the reference model.",
    )
    parser.add_argument(
        "--view-map",
        type=Path,
        help="JSON object mapping canonical ten-view IDs to image paths.",
    )
    parser.add_argument(
        "--florence-model",
        default="microsoft/Florence-2-base-ft",
    )
    parser.add_argument(
        "--vqa-model",
        default="dandelin/vilt-b32-finetuned-vqa",
    )
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--skip-vqa", action="store_true")
    parser.add_argument("--skip-focused-crops", action="store_true")
    parser.add_argument("--num-beams", type=int, default=3)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--crop-padding", type=float, default=0.12)
    parser.add_argument(
        "--feature-phrases",
        default=DEFAULT_FEATURE_PHRASES,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except (OSError, ValueError) as exc:
        print(f"detail vision audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
