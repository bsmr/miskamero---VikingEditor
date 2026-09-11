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
    QMessageBox
)

from ui.valheim_detection import is_valid_valheim_installation


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.setFixedSize(600, 150)
        self.config = config

        layout = QVBoxLayout(self)

        # Valheim installation
        valheim_section = QVBoxLayout()

        valheim_section.addWidget(QLabel("Valheim Installation"))

        valheim_layout = QHBoxLayout()

        self.valheim_path_input = QLineEdit(
            config.get("valheim_dir", "")
        )

        self.browse_button = QPushButton("Browse...")

        valheim_layout.addWidget(self.valheim_path_input)
        valheim_layout.addWidget(self.browse_button)

        valheim_section.addLayout(valheim_layout)

        layout.addLayout(valheim_section)

        self.browse_button.clicked.connect(self.browse_valheim)

        # Auto backup
        self.auto_backup_checkbox = QCheckBox(
            "Automatically backup save files before saving"
        )
        self.auto_backup_checkbox.setChecked(
            config.get("auto_backup", True)
        )

        layout.addWidget(self.auto_backup_checkbox)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def browse_valheim(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Valheim Installation Folder"
        )

        if folder:
            self.valheim_path_input.setText(folder)

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

        self.accept()

    def get_settings(self):
        return {
            "valheim_dir": self.valheim_path_input.text().strip(),
            "auto_backup": self.auto_backup_checkbox.isChecked()
        }
