import struct
import io


class PlayerDataReader:
    def __init__(self, data: bytes):
        self.stream = io.BytesIO(data)

    def read_bytes(self, n: int) -> bytes:
        data = self.stream.read(n)

        if len(data) != n:
            raise EOFError(
                f"Unexpected end of stream: "
                f"expected {n} bytes, got {len(data)}"
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

    def read_long(self) -> int:
        return struct.unpack("<q", self.read_bytes(8))[0]

    def read_bool(self) -> bool:
        return self.read_bytes(1)[0] != 0

    def read_vector3(self) -> list:
        return list(
            struct.unpack(
                "<fff",
                self.read_bytes(12)
            )
        )

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

        return self.read_bytes(length).decode(
            "utf-8",
            errors="ignore"
        )

    def read_byte_array(self) -> bytes:
        length = self.read_int32()

        if length < 0:
            raise ValueError(
                f"Invalid byte array length: {length}"
            )

        return self.read_bytes(length)

    def read_num_items(self) -> int:
        """
        Valheim/ZPackage variable-size item count.

        < 128:
            one byte

        >= 128:
            two bytes
        """
        first = self.read_byte()

        if (first & 0x80) == 0:
            return first

        return ((first & 0x7F) << 8) | self.read_byte()


class PlayerDataWriter:
    def __init__(self):
        self.stream = io.BytesIO()

    def get_bytes(self) -> bytes:
        return self.stream.getvalue()

    def write_byte(self, val: int):
        self.stream.write(struct.pack("<B", val))

    def write_ushort(self, val: int):
        self.stream.write(struct.pack("<H", val))

    def write_int32(self, val: int):
        self.stream.write(struct.pack("<i", val))

    def write_float(self, val: float):
        self.stream.write(struct.pack("<f", val))

    def write_long(self, val: int):
        self.stream.write(struct.pack("<q", val))

    def write_bool(self, val: bool):
        self.stream.write(
            b"\x01" if val else b"\x00"
        )

    def write_7bit_encoded_int(self, value: int):
        while value >= 0x80:
            self.stream.write(
                bytes([(value & 0x7F) | 0x80])
            )
            value >>= 7

        self.stream.write(bytes([value]))

    def write_string(self, val: str):
        encoded = val.encode("utf-8")

        self.write_7bit_encoded_int(len(encoded))
        self.stream.write(encoded)

    def write_byte_array(self, data: bytes):
        self.write_int32(len(data))
        self.stream.write(data)


# Helpers! Klinoff needs to clean this up later. Nöfnöf.
# TODO: clean up these helpers and maybe even move them to a better location. They are not really part of the core reader/writer classes?

def read_string_list(pkg: PlayerDataReader) -> list:
    count = pkg.read_int32()

    if count < 0:
        raise ValueError(
            f"Invalid list count: {count}"
        )

    return [
        pkg.read_string()
        for _ in range(count)
    ]


def read_string_int_dictionary(pkg: PlayerDataReader) -> dict:
    count = pkg.read_int32()

    if count < 0:
        raise ValueError(
            f"Invalid dictionary count: {count}"
        )

    return {
        pkg.read_string(): pkg.read_int32()
        for _ in range(count)
    }


def read_string_string_dictionary(pkg: PlayerDataReader) -> dict:
    count = pkg.read_int32()

    if count < 0:
        raise ValueError(
            f"Invalid dictionary count: {count}"
        )

    return {
        pkg.read_string(): pkg.read_string()
        for _ in range(count)
    }


# Player.Save / Player.Load

def unpack_player_data_hex(hex_string: str) -> dict:
    """
    parses the nested Player.Save payload from a hex string into a Python dictionary.

    current Valheim player data version: 33
    current inventory version: 109
    """

    if not hex_string:
        return {}

    raw_bytes = bytes.fromhex(hex_string)

    pkg = PlayerDataReader(raw_bytes)

    out = {}

    # player core stats

    out["version"] = pkg.read_int32()

    out["max_health"] = pkg.read_float()
    out["health"] = pkg.read_float()
    out["max_stamina"] = pkg.read_float()

    out["time_since_death"] = pkg.read_float() # wtf?

    out["guardian_power"] = pkg.read_string()
    out["guardian_power_cooldown"] = pkg.read_float()

    # inventory
    #
    # Inventory.Save:
    #
    # int version = 109
    # ushort item count
    # ItemData.Save()... klinoff knows this one

    out["inventory_version"] = pkg.read_int32()

    item_count = pkg.read_ushort()

    out["inventory"] = []

    for _ in range(item_count):

        # ItemData.Save:
        #
        # int durability * 100
        # byte x
        # byte y
        # byte world level
        # byte flags
        # optional fields...
        # byte cheated flags

        durability_raw = pkg.read_int32()

        item = {
            "durability": durability_raw * 0.01,
            "grid_x": pkg.read_byte(),
            "grid_y": pkg.read_byte(),
            "world_level": pkg.read_byte()
        }

        flags = pkg.read_byte()

        # bit 0 = picked up
        item["picked_up"] = bool(flags & 1)

        # bit 1 = equipped
        item["equipped"] = bool(flags & 2)

        # bit 2 = quality present
        if flags & 4:
            item["quality"] = pkg.read_ushort()
        else:
            item["quality"] = 1

        # bit 3 = stack present
        if flags & 8:
            item["stack"] = pkg.read_ushort()
        else:
            item["stack"] = 1

        # bit 4 = variant present
        if flags & 16:
            item["variant"] = pkg.read_int32()
        else:
            item["variant"] = 0

        # bit 5 = crafter present
        if flags & 32:
            item["crafter_id"] = pkg.read_long()
            item["crafter_name"] = pkg.read_string()
        else:
            item["crafter_id"] = 0
            item["crafter_name"] = ""

        # bit 6 = prefab hash present
        #
        # Valheim 1.0 no longer stores the prefab name here!!! important
        if flags & 64:
            item["prefab_hash"] = pkg.read_int32()
        else:
            item["prefab_hash"] = 0

        # keep the old field for now so the existing data model doesn't immediately break
        item["prefab"] = ""

        # bit 7 = custom data present
        if flags & 128:
            custom_count = pkg.read_num_items()
        else:
            custom_count = 0

        item["custom_data"] = {}

        for _ in range(custom_count):
            key = pkg.read_string()
            value = pkg.read_string()

            item["custom_data"][key] = value

        # current item format always has now a extra cheated byte.
        cheated_flags = pkg.read_byte()

        item["cheated"] = bool(
            cheated_flags & 1
        )

        out["inventory"].append(item)


    # recipes, stations, materials, tutorials, uniques, trophies, biomes, known texts
    out["known_recipes"] = read_string_list(pkg)
    out["known_stations"] = read_string_int_dictionary(pkg)
    out["known_material"] = read_string_list(pkg)
    out["shown_tutorials"] = read_string_list(pkg)
    out["uniques"] = read_string_list(pkg)
    out["trophies"] = read_string_list(pkg)
    out["known_biomes"] = read_string_list(pkg)
    out["known_texts"] = read_string_string_dictionary(pkg)

    # Appearance

    out["beard"] = pkg.read_string()
    out["hair"] = pkg.read_string()

    out["skin_color"] = pkg.read_vector3()
    out["hair_color"] = pkg.read_vector3()

    out["model_index"] = pkg.read_int32()

    # foods

    food_count = pkg.read_int32()

    if food_count < 0:
        raise ValueError(
            f"Invalid food count: {food_count}"
        )

    out["foods"] = []

    for _ in range(food_count):
        out["foods"].append({
            "name": pkg.read_string(),
            "time": pkg.read_float()
        })

    # skills, not like kevin, he does not have skills. nöfnöf.
    #
    # Skills.Save:
    # version = 2
    # count
    # id
    # level
    # accumulator

    out["skill_version"] = pkg.read_int32()

    skill_count = pkg.read_int32()

    if skill_count < 0:
        raise ValueError(
            f"Invalid skill count: {skill_count}"
        )

    out["skills"] = []

    for _ in range(skill_count):
        out["skills"].append({
            "id": pkg.read_int32(),
            "level": pkg.read_float(),
            "xp": pkg.read_float()
        })

    out["custom_data"] = read_string_string_dictionary(pkg)

    # Final stats
    out["stamina"] = pkg.read_float()
    out["max_eitr"] = pkg.read_float()
    out["eitr"] = pkg.read_float()

    # build ui state
    #
    # Player.Save:
    #
    # if Hud.instance:
    #     pkg.Write(Hud.instance.m_buildUi.SaveToBinary());
    # else:
    #     pkg.Write(new byte[0]);
    #
    # ZPackage byte[] = int32 length + bytes

    build_ui_data = pkg.read_byte_array()

    out["build_ui_data_hex"] = build_ui_data.hex()

    return out


# ============================================================
# player data compiler
#
# Still based on the old format for now. will update this separately after decompilation works.
# ============================================================

def pack_player_data_hex(data: dict) -> str:
    """
    Serializes Player data payload dictionary back into binary.

    NOTE:
    This function is NOT yet updated for Valheim 1.0.
    Decompilation is being updated first.
    """

    pkg = PlayerDataWriter()

    # old format for now
    pkg.write_int32(data.get("version", 29))

    pkg.write_float(
        data.get("max_health", 25.0)
    )

    pkg.write_float(
        data.get("health", 25.0)
    )

    pkg.write_float(
        data.get("max_stamina", 50.0)
    )

    pkg.write_float(
        data.get("time_since_death", 0.0)
    )

    pkg.write_string(
        data.get("guardian_power", "")
    )

    pkg.write_float(
        data.get("guardian_power_cooldown", 0.0)
    )

    pkg.write_int32(
        data.get("inventory_version", 106)
    )

    inventory = data.get("inventory", [])

    pkg.write_int32(len(inventory))

    for item in inventory:

        pkg.write_string(
            item.get("prefab", "")
        )

        pkg.write_int32(
            item.get("stack", 1)
        )

        pkg.write_float(
            item.get("durability", 100.0)
        )

        pkg.write_int32(
            item.get("grid_x", 0)
        )

        pkg.write_int32(
            item.get("grid_y", 0)
        )

        pkg.write_bool(
            item.get("equipped", False)
        )

        pkg.write_int32(
            item.get("quality", 1)
        )

        pkg.write_int32(
            item.get("variant", 0)
        )

        pkg.write_long(
            item.get("crafter_id", 0)
        )

        pkg.write_string(
            item.get("crafter_name", "")
        )

        custom_data = item.get(
            "custom_data",
            {}
        )

        pkg.write_int32(len(custom_data))

        for k, v in custom_data.items():
            pkg.write_string(k)
            pkg.write_string(v)

        pkg.write_int32(
            item.get("world_level", 0)
        )

        pkg.write_bool(
            item.get("picked_up", False)
        )

    # Recipes
    recipes = data.get(
        "known_recipes",
        []
    )

    pkg.write_int32(len(recipes))

    for recipe in recipes:
        pkg.write_string(recipe)

    # Stations
    stations = data.get(
        "known_stations",
        {}
    )

    pkg.write_int32(len(stations))

    for k, v in stations.items():
        pkg.write_string(k)
        pkg.write_int32(v)

    # Materials
    materials = data.get(
        "known_material",
        []
    )

    pkg.write_int32(len(materials))

    for material in materials:
        pkg.write_string(material)

    # Tutorials
    tutorials = data.get(
        "shown_tutorials",
        []
    )

    pkg.write_int32(len(tutorials))

    for tutorial in tutorials:
        pkg.write_string(tutorial)

    # Uniques
    uniques = data.get(
        "uniques",
        []
    )

    pkg.write_int32(len(uniques))

    for unique in uniques:
        pkg.write_string(unique)

    # Trophies
    trophies = data.get(
        "trophies",
        []
    )

    pkg.write_int32(len(trophies))

    for trophy in trophies:
        pkg.write_string(trophy)

    # Old biome representation
    biomes = data.get(
        "known_biomes",
        []
    )

    pkg.write_int32(len(biomes))

    for biome in biomes:
        pkg.write_int32(biome)

    # Known texts
    texts = data.get(
        "known_texts",
        {}
    )

    pkg.write_int32(len(texts))

    for k, v in texts.items():
        pkg.write_string(k)
        pkg.write_string(v)

    # Appearance
    # pkg.write_string(data.get("beard", ""))
    # pkg.write_string(data.get("hair", ""))
    # for x in data.get("skin_color", [1.0, 1.0, 1.0]):
    #     pkg.write_float(x)
    # for x in data.get("hair_color", [1.0, 1.0, 1.0]):
    #     pkg.write_float(x)
    # pkg.write_int32(data.get("model_index", 0))
    pkg.write_string(
        data.get("beard", "")
    )

    pkg.write_string(
        data.get("hair", "")
    )

    for x in data.get(
        "skin_color",
        [1.0, 1.0, 1.0]
    ):
        pkg.write_float(x)

    for x in data.get(
        "hair_color",
        [1.0, 1.0, 1.0]
    ):
        pkg.write_float(x)

    pkg.write_int32(
        data.get("model_index", 0)
    )

    # Foods
    foods = data.get(
        "foods",
        []
    )

    pkg.write_int32(len(foods))

    for food in foods:
        pkg.write_string(
            food.get("name", "")
        )
        pkg.write_float(
            food.get("time", 0.0)
        )

    # Skills
    pkg.write_int32(
        data.get("skill_version", 2)
    )

    skills = data.get(
        "skills",
        []
    )

    pkg.write_int32(len(skills))

    for skill in skills:
        pkg.write_int32(
            skill.get("id", 0)
        )

        pkg.write_float(
            skill.get("level", 1.0)
        )

        pkg.write_float(
            skill.get("xp", 0.0)
        )

    # Custom data
    c_data = data.get(
        "custom_data",
        {}
    )

    pkg.write_int32(len(c_data))

    for k, v in c_data.items():
        pkg.write_string(k)
        pkg.write_string(v)

    # Final stats
    pkg.write_float(
        data.get("stamina", 50.0)
    )

    pkg.write_float(
        data.get("max_eitr", 0.0)
    )

    pkg.write_float(
        data.get("eitr", 0.0)
    )

    return pkg.get_bytes().hex()
