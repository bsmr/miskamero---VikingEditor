from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QGroupBox
)


class ProgressTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.recipes_label = QLabel("Known Recipes: 0")
        self.stations_label = QLabel("Known Stations: 0")
        self.materials_label = QLabel("Known Materials: 0")
        self.trophies_label = QLabel("Trophies: 0")
        self.uniques_label = QLabel("Unique Discoveries: 0")
        self.biomes_label = QLabel("Known Biomes: 0")

        summary_box = QGroupBox("Progress Summary")
        summary_layout = QVBoxLayout(summary_box)

        summary_layout.addWidget(self.recipes_label)
        summary_layout.addWidget(self.stations_label)
        summary_layout.addWidget(self.materials_label)
        summary_layout.addWidget(self.trophies_label)
        summary_layout.addWidget(self.uniques_label)
        summary_layout.addWidget(self.biomes_label)

        layout.addWidget(summary_box)

        self.trophies_list = QListWidget()

        trophies_box = QGroupBox("Trophies")
        trophies_layout = QVBoxLayout(trophies_box)
        trophies_layout.addWidget(self.trophies_list)

        layout.addWidget(trophies_box)

        layout.addStretch()

    def load_data(self, player_data):
        recipes = player_data.get("known_recipes", [])
        stations = player_data.get("known_stations", {})
        materials = player_data.get("known_material", [])
        trophies = player_data.get("trophies", [])
        uniques = player_data.get("uniques", [])
        biomes = player_data.get("known_biomes", [])

        self.recipes_label.setText(
            f"Known Recipes: {len(recipes)}"
        )

        self.stations_label.setText(
            f"Known Stations: {len(stations)}"
        )

        self.materials_label.setText(
            f"Known Materials: {len(materials)}"
        )

        self.trophies_label.setText(
            f"Trophies: {len(trophies)}"
        )

        self.uniques_label.setText(
            f"Unique Discoveries: {len(uniques)}"
        )

        self.biomes_label.setText(
            f"Known Biomes: {len(biomes)}"
        )

        self.trophies_list.clear()
        self.trophies_list.addItems(trophies)
