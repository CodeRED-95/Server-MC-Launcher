from __future__ import annotations

from pathlib import Path


def build_icon(source: Path, target: Path) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit(
            "Pillow no esta instalado. Instala Pillow para convertir app_icon.png a .ico."
        ) from exc

    image = Image.open(source).convert("RGBA")
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    image.save(target, format="ICO", sizes=sizes)


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    source = base / "assets" / "app_icon.png"
    target = base / "assets" / "installer_icon.ico"
    if not source.exists():
        raise SystemExit(f"No existe el icono base: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    build_icon(source, target)
    print(f"Created {target}")
