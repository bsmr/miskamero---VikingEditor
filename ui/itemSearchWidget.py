from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QComboBox,
    QCompleter
)

from PySide6.QtCore import (
    Qt,
    QStringListModel
)

from subscripts.itemDatabase import load_item_database


class ItemSearchWidget(QWidget):
    """Reusable searchable Valheim item selector."""

    def __init__(self, current_prefab="", parent=None):
        super().__init__(parent)

        self.items = []

        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QComboBox.NoInsert)
        self.combo.setMaxVisibleItems(20)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.combo)

        self.completer_model = QStringListModel()

        self.completer = QCompleter(
            self.completer_model,
            self
        )

        self.completer.setCaseSensitivity(
            Qt.CaseInsensitive
        )

        self.completer.setFilterMode(
            Qt.MatchContains
        )

        self.completer.setCompletionMode(
            QCompleter.PopupCompletion
        )

        self.combo.setCompleter(self.completer)

        self.combo.lineEdit().textEdited.connect(
            self.update_search_results
        )

        self.load_items()
        self.set_prefab(current_prefab)

    def load_items(self):
        """Load known Valheim items into the selector."""

        item_database = load_item_database()

        for prefab in sorted(item_database.values()):

            display_name = (
                prefab
                .replace("_", " ")
                .replace("$item_", "")
                .title()
            )

            self.items.append({
                "display_name": display_name,
                "prefab": prefab
            })

            self.combo.addItem(
                display_name,
                prefab
            )

        self.update_search_results("")

    def update_search_results(self, text):
        """Update autocomplete results and rank them by relevance."""

        query = text.strip().lower()

        if not query:
            results = [
                item["display_name"]
                for item in self.items
            ]

        else:
            def relevance(item):
                name = item["display_name"].lower()

                if name == query:
                    return 0

                if name.startswith(query):
                    return 1

                words = name.split()

                if any(word.startswith(query) for word in words):
                    return 2

                if query in name:
                    return 3

                return 4

            matching_items = [
                item
                for item in self.items
                if query in item["display_name"].lower()
            ]

            matching_items.sort(
                key=lambda item: (
                    relevance(item),
                    item["display_name"].lower()
                )
            )

            results = [
                item["display_name"]
                for item in matching_items
            ]

        self.completer_model.setStringList(results)

        self.completer.setCompletionPrefix(text)

    def set_prefab(self, prefab):
        """Set the current prefab, including unknown/custom prefabs."""

        for index in range(self.combo.count()):
            if self.combo.itemData(index) == prefab:
                self.combo.setCurrentIndex(index)
                return

        self.combo.setCurrentText(prefab)

    def get_prefab(self):
        """Return the actual prefab selected or entered by the user."""

        current_text = self.combo.currentText().strip()

        for item in self.items:
            if item["display_name"] == current_text:
                return item["prefab"]

        return current_text