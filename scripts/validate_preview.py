#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples" / "schema_examples.json"
VALID_TASKS = {
    "descriptors",
    "diagnosis",
    "differential",
    "management",
    "consultation",
}
FORBIDDEN_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff",
    ".dcm", ".nii", ".nii.gz", ".zip", ".tar", ".gz", ".7z",
}
FORBIDDEN_KEYS = {
    "source", "source_id", "source_index", "original_image_id", "original_url",
    "relative_image_path", "patient_id", "case_id",
}


def fail(message: str) -> None:
    raise ValueError(message)


def walk(value, where="root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                fail(f"forbidden reconstructable field at {where}.{key}")
            walk(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk(child, f"{where}[{index}]")
    elif isinstance(value, str):
        lowered = value.lower()
        if "http://" in lowered or "https://" in lowered:
            fail(f"URL found in public example at {where}")


def main() -> int:
    files = [path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts]
    for path in files:
        name = path.name.lower()
        suffix = ".nii.gz" if name.endswith(".nii.gz") else path.suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES:
            fail(f"forbidden image/archive file: {path.relative_to(ROOT)}")

    records = json.loads(DATA.read_text(encoding="utf-8"))
    if not isinstance(records, list) or len(records) != 5:
        fail("preview must contain exactly five synthetic examples")
    if {record.get("task") for record in records} != VALID_TASKS:
        fail("preview must contain exactly one example for each task")

    for index, record in enumerate(records):
        if record.get("example_type") != "synthetic_schema_only":
            fail(f"record {index} is not explicitly synthetic")
        if record.get("image") != "<image-withheld>":
            fail(f"record {index} exposes an image reference")
        conversations = record.get("conversations")
        if not isinstance(conversations, list) or len(conversations) != 2:
            fail(f"record {index} must contain two turns")
        if conversations[0].get("from") != "human" or conversations[1].get("from") != "gpt":
            fail(f"record {index} has invalid roles")
        if "<image>" not in conversations[0].get("value", ""):
            fail(f"record {index} prompt lacks the image token")
        walk(record, f"record[{index}]")

    print("Public preview validation passed")
    print("- exactly five synthetic schema examples")
    print("- no clinical or demo image files")
    print("- no source identifiers, source URLs, or reconstructable paths")
    print("- no complete annotations, taxonomies, audit artifacts, or model files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

