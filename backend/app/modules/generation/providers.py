"""Provider contracts and the CPU-only deterministic mock."""

import json
import struct
from dataclasses import dataclass
from typing import Protocol

DISCLOSURE = (
    "Dummy mock model — not a reconstruction. AI-generated 3D preview; unseen views are inferred."
)


def disclosure(provider: str) -> str:
    return (
        DISCLOSURE
        if provider == "mock"
        else (
            "AI-generated 3D preview, not a scan. Unseen views are inferred; "
            "product fidelity is not certified. Original seller photographs are authoritative."
        )
    )


@dataclass(frozen=True)
class GenerationResult:
    glb: bytes
    metadata: dict


class Provider(Protocol):
    def generate(self, image_keys: list[str]) -> GenerationResult: ...


def dummy_glb() -> bytes:
    """An original magenta octahedron, CC0. No source product details are represented."""
    vertices = [0, 1, 0, 1, 0, 0, 0, 0, 1, -1, 0, 0, 0, 0, -1, 0, -1, 0]
    indices = [0, 2, 1, 0, 3, 2, 0, 4, 3, 0, 1, 4, 5, 1, 2, 5, 2, 3, 5, 3, 4, 5, 4, 1]
    binary = struct.pack("<18f24H", *vertices, *indices)
    document = {
        "asset": {"version": "2.0", "generator": "Ayna deterministic dummy fixture (CC0)"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "DUMMY — NOT A PRODUCT RECONSTRUCTION"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}]}],
        "materials": [
            {
                "doubleSided": True,
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.85, 0.1, 0.65, 1],
                    "metallicFactor": 0,
                    "roughnessFactor": 0.7,
                },
            }
        ],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 72, "target": 34962},
            {"buffer": 0, "byteOffset": 72, "byteLength": 48, "target": 34963},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 6,
                "type": "VEC3",
                "min": [-1, -1, -1],
                "max": [1, 1, 1],
            },
            {"bufferView": 1, "componentType": 5123, "count": 24, "type": "SCALAR"},
        ],
        "extras": {"disclosure": DISCLOSURE, "license": "CC0-1.0"},
    }
    encoded = json.dumps(document, separators=(",", ":"), ensure_ascii=True).encode()
    encoded += b" " * (-len(encoded) % 4)
    return (
        struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(encoded) + 8 + len(binary))
        + struct.pack("<II", len(encoded), 0x4E4F534A)
        + encoded
        + struct.pack("<II", len(binary), 0x004E4942)
        + binary
    )


class MockProvider:
    def generate(self, image_keys: list[str]) -> GenerationResult:
        return GenerationResult(
            dummy_glb(),
            {
                "provider": "mock",
                "fixture": "octahedron-v1",
                "license": "CC0-1.0",
                "source_image_count": len(image_keys),
                "disclosure": DISCLOSURE,
            },
        )
