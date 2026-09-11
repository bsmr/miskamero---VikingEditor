import os
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QDialogButtonBox,
    QLabel,
    QFileDialog,
    QMessageBox,
    QSpinBox
)

from ui.valheim_detection import is_valid_valheim_installation


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.resize(600, 200)
        self.config = config

        layout = QVBoxLayout(self)

        # Auto backup
        self.auto_backup_checkbox = QCheckBox(
            "Automatically backup save files before saving"
        )
        self.auto_backup_checkbox.setChecked(
            config.get("auto_backup", True)
        )

        # Valheim installation
        valheim_section = QVBoxLayout()

        valheim_section.addWidget(QLabel("Valheim Installation"))

        valheim_layout = QHBoxLayout()

        self.valheim_path_input = QLineEdit(
            config.get("valheim_dir", "")
        )

        self.browse_button = QPushButton("Browse...")

        layout.addWidget(self.auto_backup_checkbox)

        valheim_layout.addWidget(self.valheim_path_input)
        valheim_layout.addWidget(self.browse_button)

        valheim_section.addLayout(valheim_layout)

        layout.addLayout(valheim_section)

        self.browse_button.clicked.connect(self.browse_valheim)

        layout.addWidget(QLabel("Backup location (leave empty for default)"))

        backup_layout = QHBoxLayout()

        self.backup_dir_input = QLineEdit(
            config.get("backup_dir", "")
        )

        self.backup_browse_button = QPushButton("Browse...")

        backup_layout.addWidget(self.backup_dir_input)
        backup_layout.addWidget(self.backup_browse_button)

        layout.addLayout(backup_layout)

        self.backup_browse_button.clicked.connect(self.browse_backup_dir)

        layout.addWidget(QLabel("Maximum backups per character"))

        self.max_backups_input = QSpinBox()
        self.max_backups_input.setRange(0, 9999)
        self.max_backups_input.setValue(
            config.get("max_backups_per_character", 20)
        )
        self.max_backups_input.setSpecialValueText("Unlimited")

        layout.addWidget(self.max_backups_input)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def validate_backup_directory(self, path):
        if not path:
            return True

        return (
            os.path.isdir(path)
            and os.access(path, os.W_OK)
        )

    def browse_valheim(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Valheim Installation Folder"
        )

        if folder:
            self.valheim_path_input.setText(folder)

    def browse_backup_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Backup Directory"
        )

        if folder:
            self.backup_dir_input.setText(folder)

    def validate_and_accept(self):
        valheim_path = self.valheim_path_input.text().strip()

        if valheim_path:
            path = Path(valheim_path)

            if not is_valid_valheim_installation(path):
                QMessageBox.warning(
                    self,
                    "Invalid Valheim Installation",
                    "The selected folder does not appear to be a valid "
                    "Valheim installation.\n\n"
                    "Please select the folder containing:\n"
                    "valheim_Data\\StreamingAssets\\SoftRef\\Bundles"
                )
                return

        backup_dir = self.backup_dir_input.text().strip()

        if not self.validate_backup_directory(backup_dir):
            QMessageBox.warning(
                self,
                "Invalid Backup Directory",
                "The selected backup directory is not valid or writable.\n\n"
                "Please choose another directory."
            )
            return

        self.accept()

    def get_settings(self):
        return {
            "valheim_dir": self.valheim_path_input.text().strip(),
            "auto_backup": self.auto_backup_checkbox.isChecked(),
            "backup_dir": self.backup_dir_input.text().strip(),
            "max_backups_per_character": self.max_backups_input.value()
        }
