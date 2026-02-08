import json
import os
from pathlib import Path
from shutil import get_terminal_size

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

DEFAULT_CONFIG = {
    "enterprise_default": False,
    "no_color": False,
    "auto_table_width": False,
    "table_width": 55,
    "purchase_delay_seconds": 0,
    "show_banner": True,
}

CONFIG_ENV_KEY = "MYXL_CONFIG_PATH"


def _merge_config(base: dict, override: dict | None) -> dict:
    merged = base.copy()
    if override:
        for key in base.keys():
            if key in override and override[key] is not None:
                merged[key] = override[key]
    return merged


def get_config_path() -> Path:
    env_path = os.getenv(CONFIG_ENV_KEY)
    if env_path:
        return Path(env_path).expanduser()

    candidates = [Path("config.json"), Path("config.yaml"), Path("config.yml")]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path("config.json")


def load_config(path: Path | None = None) -> dict:
    config_path = path or get_config_path()
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()

    if config_path.suffix in {".yaml", ".yml"}:
        if yaml is None:
            print("PyYAML tidak tersedia, gunakan config.json atau install PyYAML.")
            return DEFAULT_CONFIG.copy()
        with config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
            return _merge_config(DEFAULT_CONFIG, data)

    with config_path.open("r", encoding="utf-8") as file:
        data = json.load(file) or {}
    return _merge_config(DEFAULT_CONFIG, data)


def save_config(config: dict, path: Path | None = None) -> None:
    config_path = path or get_config_path()
    payload = _merge_config(DEFAULT_CONFIG, config)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML tidak tersedia untuk menyimpan config YAML.")
        with config_path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(payload, file, sort_keys=False, allow_unicode=True)
        return

    with config_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
        file.write("\n")


def apply_config(config: dict) -> None:
    if config.get("no_color"):
        os.environ["NO_COLOR"] = "1"
    else:
        os.environ.pop("NO_COLOR", None)


def resolve_table_width(config: dict | None = None) -> int:
    config = config or load_config()
    table_width = config.get("table_width")
    if table_width is None or config.get("auto_table_width"):
        return get_terminal_size(fallback=(80, 24)).columns
    return table_width


def input_with_default(prompt: str, default_value: str) -> str:
    value = input(f"{prompt} [{default_value}]: ").strip()
    return value if value else default_value


def prompt_bool(prompt: str, default: bool) -> bool:
    default_label = "y" if default else "n"
    while True:
        value = input_with_default(prompt, default_label).lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Input tidak valid. Masukkan y/n.")


def prompt_int(prompt: str, default: int) -> int:
    while True:
        raw = input_with_default(prompt, str(default))
        try:
            return int(raw)
        except ValueError:
            print("Input harus berupa angka.")
