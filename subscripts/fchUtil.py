import sys
import json
import struct
import io
import hashlib

# binary read and write utils

class BinaryReader:
    def __init__(self, data: bytes):
        self.stream = io.BytesIO(data)

    def read_bytes(self, n: int) -> bytes:
        data = self.stream.read(n)
        if len(data) != n:
            raise EOFError(
                f"Unexpected end of stream: expected {n} bytes, got {len(data)}"
            )
        return data

    def read_byte(self) -> int:
        return self.read_bytes(1)[0]

    def read_ushort(self) -> int:
        return struct.unpack("<H", self.read_bytes(2))[0]

    def read_int32(self) -> int:
        return struct.unpack("<i", self.read_bytes(4))[0]

    def read_float(self) -> float:
        return struct.unpack("<f", self.read_bytes(4))[0]

    def read_bool(self) -> bool:
        return self.read_bytes(1)[0] != 0

    def read_long(self) -> int:
        return struct.unpack("<q", self.read_bytes(8))[0]

    def read_vector3(self) -> list:
        return list(struct.unpack("<fff", self.read_bytes(12)))

    def read_7bit_encoded_int(self) -> int:
        value = 0
        shift = 0

        while True:
            byte = self.read_byte()
            value |= (byte & 0x7F) << shift

            if (byte & 0x80) == 0:
                break

            shift += 7

        return value

    def read_string(self) -> str:
        length = self.read_7bit_encoded_int()

        if length == 0:
            return ""

        return self.read_bytes(length).decode("utf-8", errors="ignore")

    def read_byte_array(self) -> bytes:
        length = self.read_int32()

        if length < 0:
            raise ValueError(f"Invalid byte array length: {length}")

        return self.read_bytes(length)

    def read_num_items(self) -> int:
        """
        Valheim/ZPackage variable-size item count.

        Values < 128 use one byte.
        Values >= 128 use two bytes:
            first byte: high 7 bits + 0x80
            second byte: low 8 bits
        """
        first = self.read_byte()

        if (first & 0x80) == 0:
            return first

        return ((first & 0x7F) << 8) | self.read_byte()


class BinaryWriter:
    def __init__(self):
        self.stream = io.BytesIO()

    def get_bytes(self) -> bytes:
        return self.stream.getvalue()

    def write_bytes(self, data: bytes):
        self.stream.write(data)

    def write_byte(self, val: int):
        self.stream.write(struct.pack("<B", val))

    def write_ushort(self, val: int):
        self.stream.write(struct.pack("<H", val))

    def write_int32(self, val: int):
        self.stream.write(struct.pack("<i", val))

    def write_float(self, val: float):
        self.stream.write(struct.pack("<f", val))

    def write_bool(self, val: bool):
        self.stream.write(b"\x01" if val else b"\x00")

    def write_long(self, val: int):
        self.stream.write(struct.pack("<q", val))

    def write_vector3(self, val: list):
        self.stream.write(struct.pack("<fff", *val))

    def write_7bit_encoded_int(self, value: int):
        while value >= 0x80:
            self.stream.write(bytes([(value & 0x7F) | 0x80]))
            value >>= 7

        self.stream.write(bytes([value]))

    def write_string(self, val: str):
        encoded = val.encode("utf-8")
        self.write_7bit_encoded_int(len(encoded))
        self.stream.write(encoded)

    def write_byte_array(self, data: bytes):
        self.write_int32(len(data))
        self.stream.write(data)


# current valheim v46 format

def read_string_float_dictionary(pkg: BinaryReader) -> dict:
    count = pkg.read_int32()

    if count < 0:
        raise ValueError(f"Invalid dictionary count: {count}")

    return {
        pkg.read_string(): pkg.read_float()
        for _ in range(count)
    }


def read_string_string_dictionary(pkg: BinaryReader) -> dict:
    count = pkg.read_int32()

    if count < 0:
        raise ValueError(f"Invalid dictionary count: {count}")

    return {
        pkg.read_string(): pkg.read_string()
        for _ in range(count)
    }


def read_string_list(pkg: BinaryReader) -> list:
    count = pkg.read_int32()

    if count < 0:
        raise ValueError(f"Invalid list count: {count}")

    return [
        pkg.read_string()
        for _ in range(count)
    ]

# .fch -> JSON

def decompile_fch(fch_path: str) -> dict:
    print(f"Reading binary save: {fch_path}")

    with open(fch_path, "rb") as f:
        file_bytes = f.read()

    file_reader = BinaryReader(file_bytes)

    #
    # outer .fch container:
    # 
    # int package_length
    # byte[] package
    # int hash_length
    # byte[] hash
    #

    zpackage_len = file_reader.read_int32()

    if zpackage_len < 0:
        raise ValueError(f"Invalid package length: {zpackage_len}")

    zpackage_bytes = file_reader.read_bytes(zpackage_len)

    hash_len = file_reader.read_int32()

    if hash_len < 0:
        raise ValueError(f"Invalid hash length: {hash_len}")

    stored_hash = file_reader.read_bytes(hash_len)

    calculated_hash = hashlib.sha512(zpackage_bytes).digest()

    if calculated_hash != stored_hash:
        print(
            "Warning: File SHA-512 checksum mismatch. "
            "Save may be corrupted, but we'll try to parse it anyway."
        )

    pkg = BinaryReader(zpackage_bytes)

    save_data = {}

    # PlayerProfile version / stat dimensions
    #
    # Current Valheim:
    #
    # version = 46
    # stat count = 205
    # profile count = 10

    version = pkg.read_int32()
    save_data["version"] = version

    stat_count = pkg.read_int32()
    profile_count = pkg.read_int32()

    save_data["stat_count"] = stat_count
    save_data["profile_count"] = profile_count

    if version != 46:
        print(
            f"Warning: This parser targets Valheim Version 46. "
            f"Attempting to parse Version {version} anyway..."
        )

    # 2. player shtats

    save_data["stats"] = []

    save_data["known_worlds"] = {}
    save_data["known_world_keys"] = {}
    save_data["known_commands"] = {}
    save_data["enemy_stats"] = []
    save_data["item_pickup_stats"] = {}
    save_data["item_craft_stats"] = {}
    save_data["pickable_stats"] = {}
    save_data["food_eaten_stats"] = {}
    save_data["pieces_placed_stats"] = {}

    for profile_index in range(profile_count):

        # 205 floats for this profile
        profile_stats = [
            pkg.read_float()
            for _ in range(stat_count)
        ]

        save_data["stats"].append(profile_stats)

        known_worlds = read_string_float_dictionary(pkg)

        known_world_keys = read_string_float_dictionary(pkg)

        known_commands = read_string_float_dictionary(pkg)

        # Klinoff thinks that the current version of Valheim writes 5 enemy-stat groups.
        enemy_group_count = pkg.read_int32()

        if enemy_group_count < 0:
            raise ValueError(
                f"Invalid enemy stat group count: {enemy_group_count}"
            )

        enemy_stats = []

        for _ in range(enemy_group_count):
            enemy_stats.append(
                read_string_float_dictionary(pkg)
            )

        # remaining stat dictionaries after enemy stats, for this profile
        item_pickup_stats = read_string_float_dictionary(pkg)
        item_craft_stats = read_string_float_dictionary(pkg)
        pickable_stats = read_string_float_dictionary(pkg)
        food_eaten_stats = read_string_float_dictionary(pkg)
        pieces_placed_stats = read_string_float_dictionary(pkg)

        # Preserve the existing JSON structure for profile 0, while also keeping all profiles.
        if profile_index == 0:
            save_data["known_worlds"] = known_worlds
            save_data["known_world_keys"] = known_world_keys
            save_data["known_commands"] = known_commands
            save_data["enemy_stats"] = enemy_stats
            save_data["item_pickup_stats"] = item_pickup_stats
            save_data["item_craft_stats"] = item_craft_stats
            save_data["pickable_stats"] = pickable_stats
            save_data["food_eaten_stats"] = food_eaten_stats
            save_data["pieces_placed_stats"] = pieces_placed_stats

    # 3. first spawn

    save_data["first_spawn"] = pkg.read_bool()

    # 4. world data

    world_count = pkg.read_int32()

    if world_count < 0:
        raise ValueError(f"Invalid world count: {world_count}")

    worlds = []

    for _ in range(world_count):

        world = {}

        world["world_id"] = pkg.read_long()

        world["have_custom_spawn"] = pkg.read_bool()
        world["spawn_point"] = pkg.read_vector3()

        world["have_logout_point"] = pkg.read_bool()
        world["logout_point"] = pkg.read_vector3()

        # Current v46 always writes death point. Or so Klinoff believes... Nöfnöf.
        world["have_death_point"] = pkg.read_bool()
        world["death_point"] = pkg.read_vector3()

        world["home_point"] = pkg.read_vector3()

        has_map_data = pkg.read_bool()

        world["map_data_hex"] = (
            pkg.read_byte_array().hex()
            if has_map_data
            else None
        )

        worlds.append(world)

    save_data["worlds"] = worlds

    # 5. character info

    save_data["character_name"] = pkg.read_string()
    save_data["player_id"] = pkg.read_long()
    save_data["start_seed"] = pkg.read_string()

    # 6. metadata

    save_data["used_cheats"] = pkg.read_bool()
    save_data["date_created_unix"] = pkg.read_long()

    # nested Player.Save data

    has_player_data = pkg.read_bool()

    if has_player_data:
        player_data_bytes = pkg.read_byte_array()
        save_data["player_data_hex"] = player_data_bytes.hex()
    else:
        save_data["player_data_hex"] = None

    print("Successfully unpacked save.")

    return save_data

# JSON -> .fch

def compile_fch(json_path: str, fch_path: str):
    print(f"Reading JSON file: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        save_data = json.load(f)

    pkg = BinaryWriter()

    version = save_data["version"]
    pkg.write_int32(version)

    # OLD compiler implementation retained for now, klinoff only wants to update the decompiler first!
    # klinoff will update this separately after the new format has been successfully decompiled and verified.

    pkg.write_int32(len(save_data["stats"]))

    for stat in save_data["stats"]:
        pkg.write_float(stat)

    pkg.write_bool(save_data["first_spawn"])

    pkg.write_int32(len(save_data["worlds"]))

    for world in save_data["worlds"]:
        pkg.write_long(world["world_id"])

        pkg.write_bool(world["have_custom_spawn"])
        pkg.write_vector3(world["spawn_point"])

        pkg.write_bool(world["have_logout_point"])
        pkg.write_vector3(world["logout_point"])

        if version >= 30:
            pkg.write_bool(world["have_death_point"])
            pkg.write_vector3(world["death_point"])

        pkg.write_vector3(world["home_point"])

        has_map_data = world["map_data_hex"] is not None

        pkg.write_bool(has_map_data)

        if has_map_data:
            pkg.write_byte_array(
                bytes.fromhex(world["map_data_hex"])
            )

    pkg.write_string(save_data["character_name"])
    pkg.write_long(save_data["player_id"])
    pkg.write_string(save_data["start_seed"])

    pkg.write_bool(save_data["used_cheats"])
    pkg.write_long(save_data["date_created_unix"])

    pkg.write_int32(len(save_data["known_worlds"]))

    for k, v in save_data["known_worlds"].items():
        pkg.write_string(k)
        pkg.write_float(v)

    pkg.write_int32(len(save_data["known_world_keys"]))

    for k, v in save_data["known_world_keys"].items():
        pkg.write_string(k)
        pkg.write_float(v)

    pkg.write_int32(len(save_data["known_commands"]))

    for k, v in save_data["known_commands"].items():
        pkg.write_string(k)
        pkg.write_float(v)

    if version >= 42:
        pkg.write_int32(len(save_data["enemy_stats"]))

        for k, v in save_data["enemy_stats"].items():
            pkg.write_string(k)
            pkg.write_float(v)

        pkg.write_int32(len(save_data["item_pickup_stats"]))

        for k, v in save_data["item_pickup_stats"].items():
            pkg.write_string(k)
            pkg.write_float(v)

        pkg.write_int32(len(save_data["item_craft_stats"]))

        for k, v in save_data["item_craft_stats"].items():
            pkg.write_string(k)
            pkg.write_float(v)

    has_player_data = save_data["player_data_hex"] is not None

    pkg.write_bool(has_player_data)

    if has_player_data:
        pkg.write_byte_array(
            bytes.fromhex(save_data["player_data_hex"])
        )

    zpackage_bytes = pkg.get_bytes()

    calculated_hash = hashlib.sha512(zpackage_bytes).digest()

    file_writer = BinaryWriter()

    file_writer.write_int32(len(zpackage_bytes))
    file_writer.write_bytes(zpackage_bytes)

    file_writer.write_int32(len(calculated_hash))
    file_writer.write_bytes(calculated_hash)

    with open(fch_path, "wb") as f:
        f.write(file_writer.get_bytes())

    print(
        f"Successfully compiled and hashed! "
        f"File created at: {fch_path}"
    )

# CLI, klinoff likey

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Valheim Save File Utility")
        print("Usage:")
        print(
            "  Decompile: "
            "python valheim_editor.py unpack "
            "<character.fch> <output.json>"
        )
        print(
            "  Compile:   "
            "python valheim_editor.py pack "
            "<input.json> <output.fch>"
        )
        sys.exit(1)

    mode = sys.argv[1].lower()
    source_file = sys.argv[2]
    target_file = sys.argv[3]

    if mode == "unpack":
        save_data = decompile_fch(source_file)

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(
                save_data,
                f,
                indent=4,
                ensure_ascii=False
            )

        print(f"JSON created at: {target_file}")

    elif mode == "pack":
        compile_fch(source_file, target_file)

    else:
        print(
            f"Error: Unknown mode '{mode}'. "
            f"Use 'unpack' or 'pack'."
        )
