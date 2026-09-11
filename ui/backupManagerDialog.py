from pathlib import Path
import shutil

from ui.valheim_detection import get_valheim_character_save_directory

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QMessageBox,
    QComboBox,
)


class BackupManagerDialog(QDialog):
    def __init__(self, backup_directory, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Backup Manager")
        self.resize(700, 500)

        self.backup_directory = Path(backup_directory)
        self.main_window = parent

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Character"))

        self.character_filter = QComboBox()
        layout.addWidget(self.character_filter)

        layout.addWidget(QLabel("Character Backups"))

        self.backup_list = QListWidget()
        self.backup_list.setSpacing(4)

        self.character_filter.currentTextChanged.connect(
            self.filter_backups
        )

        layout.addWidget(self.backup_list)
        layout.addWidget(self.backup_list)

        self.backup_info = QLabel(
            "Select a backup to view its details."
        )
        self.backup_info.setWordWrap(True)
        layout.addWidget(self.backup_info)

        button_layout = QHBoxLayout()

        self.open_button = QPushButton("Open Backup")
        self.restore_button = QPushButton("Restore to current loaded save")
        self.restore_to_valheim_button = QPushButton("Restore to Valheim Saves")
        self.delete_button = QPushButton("Delete")
        self.open_folder_button = QPushButton("Open Backups Folder")

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.restore_to_valheim_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.open_folder_button)

        layout.addLayout(button_layout)

        self.open_button.clicked.connect(self.open_backup)

        self.restore_button.clicked.connect(self.restore_backup)
        self.restore_to_valheim_button.clicked.connect(self.restore_to_valheim)

        self.open_folder_button.clicked.connect(self.open_backups_folder)

        self.backup_list.itemDoubleClicked.connect(
            lambda _: self.open_backup()
        )

        self.backup_list.currentItemChanged.connect(
            self.update_backup_info
        )

        self.load_backups()

    def open_backups_folder(self):
        import os

        self.backup_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        os.startfile(str(self.backup_directory))

    def filter_backups(self, character_name):
        for index in range(self.backup_list.count()):
            item = self.backup_list.item(index)

            backup_path = Path(
                item.data(256)
            )

            if character_name == "All Characters":
                item.setHidden(False)
                continue

            item.setHidden(
                backup_path.parent.name != character_name
            )

    def load_backups(self):
        self.backup_list.clear()
        self.character_filter.blockSignals(True)
        self.character_filter.clear()
        self.character_filter.addItem("All Characters")

        if not self.backup_directory.is_dir():
            self.character_filter.blockSignals(False)
            return

        character_names = []

        for character_dir in sorted(self.backup_directory.iterdir()):
            if not character_dir.is_dir():
                continue

            backups = sorted(
                character_dir.glob("*.fch"),
                key=lambda path: path.stat().st_mtime,
                reverse=True
            )

            if not backups:
                continue

            character_names.append(character_dir.name)

            for backup_file in backups:
                modified_time = backup_file.stat().st_mtime

                from datetime import datetime

                created_time = datetime.fromtimestamp(
                    modified_time
                ).strftime("%B %d, %Y %H:%M:%S")

                size = backup_file.stat().st_size

                if size < 1024:
                    size_text = f"{size} B"
                elif size < 1024 * 1024:
                    size_text = f"{size / 1024:.1f} KB"
                else:
                    size_text = f"{size / (1024 * 1024):.1f} MB"

                item = QListWidgetItem(
                    f"{character_dir.name}\n"
                    f"{created_time} · {size_text}"
                )

                item.setData(
                    256,
                    str(backup_file)
                )

                self.backup_list.addItem(item)

        self.character_filter.addItems(
            character_names
        )

        self.character_filter.blockSignals(False)

    def get_selected_backup(self):
        item = self.backup_list.currentItem()

        if item is None:
            QMessageBox.information(
                self,
                "No Backup Selected",
                "Please select a backup first."
            )
            return None

        return Path(item.data(256))

    def update_backup_info(self, current, previous):
        if current is None:
            self.backup_info.setText(
                "Select a backup to view its details."
            )
            return

        backup_path = Path(
            current.data(256)
        )

        if not backup_path.is_file():
            self.backup_info.setText(
                "The selected backup file no longer exists."
            )
            return

        from datetime import datetime

        character_name = backup_path.parent.name

        created_time = datetime.fromtimestamp(
            backup_path.stat().st_mtime
        ).strftime("%B %d, %Y %H:%M:%S")

        size = backup_path.stat().st_size

        if size < 1024:
            size_text = f"{size} B"
        elif size < 1024 * 1024:
            size_text = f"{size / 1024:.1f} KB"
        else:
            size_text = f"{size / (1024 * 1024):.1f} MB"

        self.backup_info.setText(
            f"<b>Selected Backup</b><br><br>"
            f"<b>Character:</b> {character_name}<br>"
            f"<b>Created:</b> {created_time}<br>"
            f"<b>Size:</b> {size_text}<br>"
            f"<b>Location:</b> {backup_path}"
        )

    def open_backup(self):
        backup_path = self.get_selected_backup()

        if backup_path is None:
            return

        if not backup_path.is_file():
            QMessageBox.warning(
                self,
                "Backup Not Found",
                "The selected backup file no longer exists."
            )
            self.load_backups()
            return

        answer = QMessageBox.question(
            self,
            "Open Backup",
            "Open this backup in Viking Editor?\n\n"
            f"{backup_path.name}\n\n"
            "The backup will be loaded for editing. "
            "Saving will create a new save file rather than "
            "modifying this backup directly.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        if self.main_window is None:
            return

        if not self.main_window.load_backup_file(backup_path):
            return

        self.accept()

    def restore_to_valheim(self):
        backup_path = self.get_selected_backup()

        if backup_path is None:
            return

        if not backup_path.is_file():
            QMessageBox.warning(
                self,
                "Backup Not Found",
                "The selected backup file no longer exists."
            )
            self.load_backups()
            return

        valheim_save_dir = get_valheim_character_save_directory()
        name = backup_path.stem

        timestamp_parts = name.rsplit("_", 2)

        if len(timestamp_parts) == 3:
            character_name = timestamp_parts[0]
        else:
            character_name = name

        target_path = valheim_save_dir / f"{character_name}.fch"

        valheim_save_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        if target_path.exists():
            answer = QMessageBox.question(
                self,
                "Overwrite Character Save?",
                "A character save with this name already exists.\n\n"
                f"{target_path.name}\n\n"
                "Do you want to overwrite it?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            shutil.copy2(
                backup_path,
                target_path
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Restore Failed",
                "Could not restore the backup to the Valheim save directory:\n\n"
                f"{e}"
            )
            return

        QMessageBox.information(
            self,
            "Backup Restored",
            "The backup was restored to the Valheim character saves.\n\n"
            f"File:\n{target_path}"
        )

    def restore_backup(self):
        backup_path = self.get_selected_backup()

        if backup_path is None:
            return

        if not backup_path.is_file():
            QMessageBox.warning(
                self,
                "Backup Not Found",
                "The selected backup file no longer exists."
            )
            self.load_backups()
            return

        if self.main_window is None:
            return

        current_fch = self.main_window.current_fch

        if not current_fch:
            QMessageBox.warning(
                self,
                "No Save Loaded",
                "Load a character save before restoring a backup."
            )
            return

        current_fch = Path(current_fch)

        answer = QMessageBox.question(
            self,
            "Restore Backup",
            "Are you sure you want to restore this backup?\n\n"
            f"Backup:\n{backup_path}\n\n"
            f"Target:\n{current_fch}\n\n"
            "The current save will be replaced.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            # Create a safety backup of the current save
            if self.main_window.config.get("auto_backup", True):
                if current_fch.is_file():
                    safety_backup = self.main_window.create_backup(
                        current_fch
                    )

                    character_name = (
                        self.main_window.root_save.get(
                            "character_name",
                            "Viking"
                        ).strip()
                    )

                    if not character_name:
                        character_name = "Viking"

                    self.main_window.cleanup_old_backups(
                        character_name
                    )

            # Restore the selected backup
            shutil.copy2(backup_path, current_fch)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Restore Failed",
                "Could not restore the backup:\n\n"
                f"{e}"
            )
            return

        except Exception as e:
            QMessageBox.critical(
                self,
                "Restore Failed",
                "Could not restore the backup:\n\n"
                f"{e}"
            )
            return

        QMessageBox.information(
            self,
            "Backup Restored",
            "The backup was restored successfully.\n\n"
            f"Restored:\n{current_fch}\n\n"
            f"Safety backup:\n{safety_backup}"
        )

        self.main_window.load_backup_file(current_fch)
        self.load_backups()

    def delete_backup(self):
        backup_path = self.get_selected_backup()

        if backup_path is None:
            return

        if not backup_path.is_file():
            QMessageBox.warning(
                self,
                "Backup Not Found",
                "The selected backup file no longer exists."
            )
            self.load_backups()
            return

        answer = QMessageBox.question(
            self,
            "Delete Backup",
            "Are you sure you want to permanently delete this backup?\n\n"
            f"{backup_path}",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            backup_path.unlink()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Delete Failed",
                "Could not delete the backup:\n\n"
                f"{e}"
            )
            return

        self.load_backups()
