from pathlib import Path

import yaml


def get_keys(data, prefix=""):
    keys = set()
    if isinstance(data, dict):
        for k, v in data.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.add(full_key)
            keys.update(get_keys(v, full_key))
    return keys


def main():
    translations_dir = Path("sigenergy2mqtt/translations")
    en_path = translations_dir / "en.yaml"

    with open(en_path, "r", encoding="utf-8") as f:
        en_data = yaml.safe_load(f)

    en_keys = get_keys(en_data)

    for yaml_file in translations_dir.glob("*.yaml"):
        if yaml_file.name == "en.yaml":
            continue

        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        keys = get_keys(data)
        missing = en_keys - keys

        if missing:
            print(f"\nMissing keys in {yaml_file.name}:")
            for key in sorted(missing):
                print(f"  - {key}")


if __name__ == "__main__":
    main()
