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
)


class BackupManagerDialog(QDialog):
    def __init__(self, backup_directory, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Backup Manager")
        self.resize(700, 500)

        self.backup_directory = Path(backup_directory)
        self.main_window = parent

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Character Backups"))

        self.backup_list = QListWidget()
        layout.addWidget(self.backup_list)

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

        self.load_backups()

    def open_backups_folder(self):
        import os

        self.backup_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        os.startfile(str(self.backup_directory))

    def load_backups(self):
        self.backup_list.clear()

        if not self.backup_directory.is_dir():
            return

        for character_dir in sorted(self.backup_directory.iterdir()):
            if not character_dir.is_dir():
                continue

            backups = sorted(
                character_dir.glob("*.fch"),
                key=lambda path: path.stat().st_mtime,
                reverse=True
            )

            for backup_file in backups:
                item = QListWidgetItem(
                    f"{character_dir.name} — {backup_file.name}"
                )

                item.setData(
                    256,
                    str(backup_file)
                )

                self.backup_list.addItem(item)

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
