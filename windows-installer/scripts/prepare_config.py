"""Prepare machine-wide Windows configuration and a unique Django secret key."""

import os
import secrets
from pathlib import Path


def prepare_config(program_data: Path, template: Path) -> Path:
    config_path = program_data / "Finlo-CRM" / "config" / "finlo-crm.conf"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        lines = config_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = template.read_text(encoding="utf-8").splitlines()

    configured_key = next(
        (
            line.partition("=")[2].strip()
            for line in lines
            if line.partition("=")[0].strip() == "SECRET_KEY"
        ),
        "",
    )
    if not configured_key or configured_key == "change-this-in-production":
        lines = [
            line
            for line in lines
            if line.partition("=")[0].strip() != "SECRET_KEY"
        ]
        lines.append(f"SECRET_KEY={secrets.token_urlsafe(64)}")

    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


if __name__ == "__main__":
    program_data = os.environ.get("ProgramData")
    if not program_data:
        raise RuntimeError("The Windows ProgramData directory is unavailable.")
    prepare_config(
        Path(program_data),
        Path(__file__).parent.parent / "config" / "finlo-crm.conf",
    )
