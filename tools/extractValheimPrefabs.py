from pathlib import Path
import json
import sys

import UnityPy


VALHEIM_DIR = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Valheim"
)

BUNDLES_DIR = VALHEIM_DIR / "valheim_Data" / "StreamingAssets" / "SoftRef" / "Bundles"

OUTPUT_FILE = Path("valheim_prefabs.json")


def extract_prefabs():
    if not BUNDLES_DIR.is_dir():
        print(f"ERROR: Bundle directory not found:")
        print(BUNDLES_DIR)
        sys.exit(1)

    bundle_files = [
        path for path in BUNDLES_DIR.iterdir()
        if path.is_file()
    ]

    print(f"Found {len(bundle_files)} bundle files.")
    print(f"Scanning: {BUNDLES_DIR}")
    print()

    prefab_names = set()
    failed_bundles = []

    for index, bundle_path in enumerate(bundle_files, 1):
        print(
            f"[{index}/{len(bundle_files)}] "
            f"{bundle_path.name}",
            end="",
            flush=True
        )

        try:
            env = UnityPy.load(str(bundle_path))

            count = 0

            for obj in env.objects:
                if obj.type.name != "GameObject":
                    continue

                try:
                    name = obj.peek_name()
                except Exception:
                    name = None

                if not name:
                    continue

                prefab_names.add(name)
                count += 1

            print(f" -> {count} GameObjects")

        except Exception as exc:
            print(f" -> FAILED: {exc}")
            failed_bundles.append({
                "file": bundle_path.name,
                "error": str(exc),
            })

    prefab_names = sorted(prefab_names, key=str.lower)

    result = {
        "bundle_directory": str(BUNDLES_DIR),
        "game_object_count": len(prefab_names),
        "failed_bundle_count": len(failed_bundles),
        "prefabs": prefab_names,
        "failed_bundles": failed_bundles,
    }

    OUTPUT_FILE.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("========================================")
    print("Extraction complete!")
    print("========================================")
    print(f"Unique GameObjects: {len(prefab_names)}")
    print(f"Failed bundles:     {len(failed_bundles)}")
    print(f"Output:             {OUTPUT_FILE}")
    print()

    print("First 50 names:")
    for name in prefab_names[:50]:
        print(f"  {name}")


if __name__ == "__main__":
    extract_prefabs()
