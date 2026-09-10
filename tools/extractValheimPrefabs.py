from pathlib import Path
import json

import UnityPy
from UnityPy.enums import ClassIDType


VALHEIM_DIR = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Valheim"
)

BUNDLES_DIR = (
    VALHEIM_DIR
    / "valheim_Data"
    / "StreamingAssets"
    / "SoftRef"
    / "Bundles"
)

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "valheim_items.json"


def int32(value):
    """Convert an integer to C# signed Int32 with overflow behavior."""
    value &= 0xFFFFFFFF

    if value >= 0x80000000:
        value -= 0x100000000

    return value


def get_stable_hash_code(text):
    """
    Exact equivalent of Valheim's C# GetStableHashCode().
    """

    # C# string indexing operates on UTF-16 code units.
    encoded = text.encode("utf-16-le")

    chars = [
        int.from_bytes(encoded[i:i + 2], "little")
        for i in range(0, len(encoded), 2)
    ]

    num = 5381
    num2 = num
    num3 = 0

    while num3 < len(chars) and chars[num3] != 0:

        num = int32(
            ((num << 5) + num) ^ chars[num3]
        )

        if (
            num3 == len(chars) - 1
            or chars[num3 + 1] == 0
        ):
            break

        num2 = int32(
            ((num2 << 5) + num2) ^ chars[num3 + 1]
        )

        num3 += 2

    return int32(
        num + num2 * 1566083941
    )


def get_script_class_name(component):
    try:
        mono = component.read()

        if not mono.m_Script:
            return None

        script = mono.m_Script.deref()

        if script is None:
            return None

        return script.read().m_ClassName

    except Exception:
        return None


def get_item_shared_name(component):
    """Return ItemDrop.m_itemData.m_shared.m_name."""

    try:
        mono = component.read()

        item_data = mono.m_itemData

        if item_data is None:
            return None

        shared = item_data.m_shared

        if shared is None:
            return None

        return shared.m_name

    except Exception:
        return None


def main():
    print("Loading Valheim bundles...")

    env = UnityPy.Environment()

    bundle_files = [
        path
        for path in BUNDLES_DIR.iterdir()
        if path.is_file()
    ]

    for index, bundle_path in enumerate(bundle_files, 1):
        print(
            f"\rLoading {index}/{len(bundle_files)}",
            end="",
            flush=True,
        )

        env.load_file(str(bundle_path))

    print()
    print("All bundles loaded.")
    print()

    script_cache = {}

    # prefab name -> localized shared name
    items = {}

    game_objects_checked = 0
    itemdrops_checked = 0

    for obj in env.objects:

        if obj.type != ClassIDType.GameObject:
            continue

        game_objects_checked += 1

        try:
            prefab_name = obj.peek_name()
        except Exception:
            continue

        if not prefab_name:
            continue

        try:
            game_object = obj.read()
        except Exception:
            continue

        for entry in game_object.m_Component:

            try:
                component = entry.component.deref()

                if component is None:
                    continue

                if component.type != ClassIDType.MonoBehaviour:
                    continue

                cache_key = (
                    component.assets_file.name,
                    component.path_id,
                )

                if cache_key not in script_cache:
                    script_cache[cache_key] = (
                        get_script_class_name(component)
                    )

                if script_cache[cache_key] != "ItemDrop":
                    continue

                itemdrops_checked += 1

                shared_name = get_item_shared_name(component)

                # Only actual localized item names.
                if (
                    shared_name is not None
                    and shared_name.startswith("$item_")
                ):
                    items[prefab_name] = shared_name

                break

            except Exception:
                continue

    # Build hash -> item data.
    hash_to_item = {}

    hash_collisions = []

    for prefab_name, shared_name in sorted(items.items()):

        prefab_hash = get_stable_hash_code(prefab_name)

        existing = hash_to_item.get(prefab_hash)

        if existing is not None:
            if existing["prefab"] != prefab_name:
                hash_collisions.append(
                    {
                        "hash": prefab_hash,
                        "first": existing["prefab"],
                        "second": prefab_name,
                    }
                )

                continue

        hash_to_item[prefab_hash] = {
            "prefab": prefab_name,
            "shared_name": shared_name,
        }

    # JSON object keys must be strings.
    output = {
        "valheim_version": "1.0",
        "source": str(BUNDLES_DIR),
        "item_count": len(hash_to_item),
        "game_objects_checked": game_objects_checked,
        "itemdrops_checked": itemdrops_checked,
        "hash_collision_count": len(hash_collisions),
        "items": {
            str(prefab_hash): item
            for prefab_hash, item in sorted(hash_to_item.items())
        },
    }

    if hash_collisions:
        output["hash_collisions"] = hash_collisions

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("========================================")
    print("Valheim item extraction complete")
    print("========================================")
    print(f"GameObjects checked:     {game_objects_checked}")
    print(f"ItemDrops checked:       {itemdrops_checked}")
    print(f"Unique item prefabs:     {len(items)}")
    print(f"Unique item hashes:      {len(hash_to_item)}")
    print(f"Hash collisions:         {len(hash_collisions)}")
    print()
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()