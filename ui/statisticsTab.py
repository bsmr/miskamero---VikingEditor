from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView
)


class StatisticsTab(QWidget):
    def __init__(self):
        super().__init__()

        self.player_data = None
        self.root_save = None

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        self.enemies_table = self.create_table()
        self.pickups_table = self.create_table()
        self.crafted_table = self.create_table()
        self.pickables_table = self.create_table()

        self.tabs.addTab(self.enemies_table, "Enemies")
        self.tabs.addTab(self.pickups_table, "Items Picked Up")
        self.tabs.addTab(self.crafted_table, "Items Crafted")
        self.tabs.addTab(self.pickables_table, "Pickables")

        layout.addWidget(self.tabs)

    def create_table(self):
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Name", "Count"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        return table

    def load_data(self, player_data, root_save):
        self.player_data = player_data
        self.root_save = root_save

        self.clear_tables()

        if not self.root_save:
            return

        profiles = self.root_save.get("profiles", [])

        if not profiles:
            return

        # Combine statistics from all profiles.
        enemy_stats = {}
        pickup_stats = {}
        crafted_stats = {}
        pickable_stats = {}

        for profile in profiles:
            # Enemy statistics are stored as a list of dictionaries.
            for enemy_dict in profile.get("enemy_stats", []):
                for name, count in enemy_dict.items():
                    enemy_stats[name] = (
                        enemy_stats.get(name, 0) + count
                    )

            # Other statistics are dictionaries.
            for name, count in profile.get(
                "item_pickup_stats", {}
            ).items():
                pickup_stats[name] = (
                    pickup_stats.get(name, 0) + count
                )

            for name, count in profile.get(
                "item_craft_stats", {}
            ).items():
                crafted_stats[name] = (
                    crafted_stats.get(name, 0) + count
                )

            for name, count in profile.get(
                "pickable_stats", {}
            ).items():
                pickable_stats[name] = (
                    pickable_stats.get(name, 0) + count
                )

        self.populate_table(
            self.enemies_table,
            enemy_stats
        )

        self.populate_table(
            self.pickups_table,
            pickup_stats
        )

        self.populate_table(
            self.crafted_table,
            crafted_stats
        )

        self.populate_table(
            self.pickables_table,
            pickable_stats
        )

    def get_first_populated(self, dictionaries):
        for data in dictionaries:
            if data:
                return data

        return {}

    def populate_table(self, table, data):
        table.setRowCount(0)

        sorted_items = sorted(
            data.items(),
            key=lambda item: item[1],
            reverse=True
        )

        for name, count in sorted_items:
            row = table.rowCount()
            table.insertRow(row)

            display_name = self.format_name(name)

            table.setItem(
                row,
                0,
                QTableWidgetItem(display_name)
            )

            table.setItem(
                row,
                1,
                QTableWidgetItem(self.format_count(count))
            )

    def format_name(self, name):
        if name.startswith("$"):
            name = name[1:]

        return name.replace("_", " ").strip().title()

    def format_count(self, count):
        if float(count).is_integer():
            return str(int(count))

        return str(count)

    def clear_tables(self):
        self.enemies_table.setRowCount(0)
        self.pickups_table.setRowCount(0)
        self.crafted_table.setRowCount(0)
        self.pickables_table.setRowCount(0)
