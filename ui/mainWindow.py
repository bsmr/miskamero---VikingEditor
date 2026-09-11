import json
import os

from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QThread, Signal
from pathlib import Path

from ui.inventoryTab import InventoryTab
from ui.skillsTab import SkillsTab
from ui.statsTab import StatsTab
from ui.appearanceTab import AppearanceTab
from ui.miscTab import MiscTab
from data.info import INFO_TEXT

from ui.valheim_detection import (
    is_valheim_running,
    valheim_warning_message,
    find_valheim_installation,
    is_valid_valheim_installation,
    load_saved_valheim_path,
    save_valheim_path
)

from subscripts.fchUtil import (
    decompile_fch,
    compile_fch
)

from subscripts.playerDataUtil import (
    unpack_player_data_hex,
    pack_player_data_hex,
    reload_item_database
)

from subscripts.itemDatabase import (
    ITEM_DATABASE_PATH,
    update_item_database as scan_item_database
)

class ItemDatabaseWorker(QThread):
    progress = Signal(int, int, str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, valheim_dir):
        super().__init__()
        self.valheim_dir = valheim_dir
        self.cancel_requested = False

    def run(self):
        try:
            item_database = scan_item_database(
                self.valheim_dir,
                progress_callback=self.update_progress,
                cancel_callback=self.is_cancelled
            )

            self.finished.emit(item_database)

        except Exception as e:
            self.error.emit(str(e))

    def update_progress(self, current, total, message):
        self.progress.emit(current, total, message)

    def is_cancelled(self):
        return self.cancel_requested

    def cancel(self):
        self.cancel_requested = True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # valheim check, nöfnöf
        if is_valheim_running():
            warning_msg = valheim_warning_message()
            msg = QMessageBox(self)
            msg.setWindowTitle("Valheim Running Warning")
            msg.setText(warning_msg)
            msg.setIcon(QMessageBox.Warning)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

        self.root_save = None       # Container data (.fch level dict)
        self.player_data = None     # Decoded character attributes dict
        self.current_fch = None

        self.setWindowTitle("Viking Editor")
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        button_layout = QHBoxLayout()

        self.btn_open_save = QPushButton("Open Save File (.fch)")
        self.btn_open_json = QPushButton("Open JSON")
        self.btn_save_json = QPushButton("Save JSON")
        self.btn_save_save = QPushButton("Save Savefile")
        self.btn_update_items = QPushButton("Update Item Database")

        button_layout.addWidget(self.btn_open_save)
        button_layout.addWidget(self.btn_open_json)
        button_layout.addWidget(self.btn_save_json)
        button_layout.addWidget(self.btn_save_save)
        button_layout.addWidget(self.btn_update_items)

        main_layout.addLayout(button_layout)

        self.file_label = QLabel("No file loaded")
        main_layout.addWidget(self.file_label)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.inventory_tab = InventoryTab()
        self.skills_tab = SkillsTab()
        self.stats_tab = StatsTab()
        self.appearance_tab = AppearanceTab()
        self.misc_tab = MiscTab()

        self.tabs.addTab(self.inventory_tab, "Inventory")
        self.tabs.addTab(self.skills_tab, "Skills")
        self.tabs.addTab(self.stats_tab, "Stats")
        self.tabs.addTab(self.appearance_tab, "Appearance")
        self.tabs.addTab(self.misc_tab, "Misc")

        self.btn_open_save.clicked.connect(self.open_save_file)
        self.btn_open_json.clicked.connect(self.open_json_file)
        self.btn_save_json.clicked.connect(self.save_json_file)
        self.btn_save_save.clicked.connect(self.save_save_file)
        self.btn_update_items.clicked.connect(self.update_item_database)

        self.check_item_database()

        msg = QMessageBox(self)
        msg.setWindowTitle("Information")
        msg.setText(INFO_TEXT)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        msg.exec()

    def check_item_database(self):
        if ITEM_DATABASE_PATH.exists():
            return

        QMessageBox.information(
            self,
            "Item Database",
            "The Valheim item database has not been created yet.\n\n"
            "The editor will now scan your Valheim installation "
            "to create it.\n\n"
            "It is needed to properly display item names in the inventory tab.\n\n"
            "This may take a moment."
        )

        self.update_item_database()

    def update_item_database(self):
        valheim_dir = load_saved_valheim_path()

        # Use the saved path if it still points to a valid installation.
        if valheim_dir is not None:
            if not is_valid_valheim_installation(valheim_dir):
                valheim_dir = None

        # No valid saved path. Ask the user how to find Valheim.
        if valheim_dir is None:

            choice = QMessageBox.question(
                self,
                "Valheim Installation",
                "The editor needs to locate your Valheim installation.\n\n"
                "Would you like the editor to try finding it automatically?\n\n"
                "Choose Yes for automatic detection.\n"
                "Choose No to select the Valheim folder manually.",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if choice == QMessageBox.StandardButton.Yes:
                valheim_dir = find_valheim_installation()

                if valheim_dir is None:
                    QMessageBox.warning(
                        self,
                        "Valheim Not Found",
                        "The editor could not automatically find your "
                        "Valheim installation.\n\n"
                        "Please select the Valheim folder manually."
                    )

            # Automatic detection failed or manual selection chosen.
            if valheim_dir is None:
                selected_dir = QFileDialog.getExistingDirectory(
                    self,
                    "Select Valheim Installation Folder"
                )

                if not selected_dir:
                    return

                valheim_dir = Path(selected_dir)

            # Validate the path before saving it.
            if not is_valid_valheim_installation(valheim_dir):
                QMessageBox.critical(
                    self,
                    "Invalid Valheim Installation",
                    "The selected folder does not appear to be a valid "
                    "Valheim installation.\n\n"
                    "Please select the folder containing:\n"
                    "valheim_Data\\StreamingAssets\\SoftRef\\Bundles"
                )
                return

            save_valheim_path(valheim_dir)

        valheim_dir = Path(valheim_dir)

        self.btn_update_items.setEnabled(False)
        cancelled = False

        progress = QProgressDialog(
            "Loading Valheim bundles...",
            None,
            0,
            100,
            self
        )

        progress.setWindowTitle("Updating Item Database")
        progress.setWindowModality(
            Qt.WindowModality.ApplicationModal
        )
        progress.setMinimumDuration(0)
        progress.setCancelButton(
            QPushButton("Cancel")
        )
        progress.setAutoClose(False)
        progress.show()

        worker = ItemDatabaseWorker(valheim_dir)

        def update_progress(current, total, message):
            progress.setLabelText(message)

            if total > 0:
                progress.setValue(
                    int(current / total * 100)
                )

        def cancel_update():
            worker.cancel()
            progress.setLabelText(
                "Cancelling item database update..."
            )
            progress.setCancelButton(None)

        def update_finished(item_database):
            progress.close()

            if item_database is None:
                self.btn_update_items.setEnabled(True)
                return

            reload_item_database()

            QMessageBox.information(
                self,
                "Item Database Updated",
                "Valheim item database updated successfully.\n\n"
                f"Valheim installation:\n{valheim_dir}\n\n"
                f"Items found: {len(item_database)}"
            )

            self.btn_update_items.setEnabled(True)

            worker.deleteLater()

        def update_error(message):
            progress.close()

            QMessageBox.critical(
                self,
                "Item Database Error",
                "Could not update the Valheim item database:\n\n"
                f"{message}"
            )

            self.btn_update_items.setEnabled(True)

            worker.deleteLater()

        worker.progress.connect(update_progress)
        worker.finished.connect(update_finished)
        worker.error.connect(update_error)

        progress.canceled.connect(cancel_update)

        worker.start()
    
    def open_save_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Valheim Character Save", "", "Valheim Character (*.fch)"
        )
        if not filename:
            return

        try:
            # 1. Unpack container
            self.root_save = decompile_fch(filename)
            self.current_fch = filename

            # 2. Extract nested player hex bytes
            player_hex = self.root_save.get("player_data_hex")
            if player_hex:
                # 3. Unpack inner structures
                self.player_data = unpack_player_data_hex(player_hex)
                self.inventory_tab.load_data(self.player_data)
                self.skills_tab.load_data(self.player_data)
                self.stats_tab.load_data(self.player_data, self.root_save)
                self.appearance_tab.load_data(self.player_data)
                self.misc_tab.load_data(self.player_data, self.root_save)
                
                self.file_label.setText(f"Loaded Save: {os.path.basename(filename)} (Char: {self.root_save.get('character_name')})")
                QMessageBox.information(self, "Success", "Valheim Save decompiled and loaded successfully!")
            else:
                QMessageBox.warning(self, "Empty Save", "The save container was read, but it contains no player data.")

        except Exception as e:
            QMessageBox.critical(self, "Error loading save", f"Failed to parse file:\n{str(e)}")

    def open_json_file(self):
        # filename, _ = QFileDialog.getOpenFileName(
        #     self, "Open unpacked character data", "", "JSON Files (*.json)"
        # )
        # if not filename:
        #     return

        # try:
        #     with open(filename, "r", encoding="utf-8") as f:
        #         self.player_data = json.load(f)

        #     self.inventory_tab.load_data(self.player_data)
        #     self.file_label.setText(f"Loaded JSON: {os.path.basename(filename)}")
        #     QMessageBox.information(self, "Success", "Character JSON loaded successfully!")
        # except Exception as e:
        #     QMessageBox.critical(self, "Error", f"Failed to open JSON:\n{str(e)}")
        QMessageBox.information(self, "Feature WIP", "Opening JSON files is currently a work in progress and not yet implemented.")


    def save_json_file(self):
        # if not self.player_data:
        #     QMessageBox.warning(self, "Save Aborted", "No active character data loaded to write.")
        #     return

        # filename, _ = QFileDialog.getSaveFileName(
        #     self, "Save Unpacked Character Data", "playerdata_edited.json", "JSON Files (*.json)"
        # )
        # if not filename:
        #     return

        # try:
        #     # 1. Collect all changes from the active tabs
        #     self.inventory_tab.save_changes()
        #     self.skills_tab.save_changes()
        #     self.stats_tab.save_changes()
        #     self.appearance_tab.save_changes()
        #     self.misc_tab.save_changes()

        #     # 2. Write straight to JSON
        #     with open(filename, "w", encoding="utf-8") as f:
        #         json.dump(self.player_data, f, indent=4, ensure_ascii=False)
                
        #     QMessageBox.information(self, "Success", f"Data exported cleanly to:\n{filename}")
        # except Exception as e:
        #     QMessageBox.critical(self, "Error", f"Could not write JSON:\n{str(e)}")
        QMessageBox.information(self, "Feature WIP", "Saving to JSON files is currently a work in progress and not yet implemented.")

    def save_save_file(self):
        """Packs the active inner data, updates the fch container, and re-compiles the file."""
        if not self.root_save or not self.player_data:
            QMessageBox.warning(self, "No Save Loaded", "Please load a valid .fch save file first.")
            return

        try:
            # 1. collect all changes from the active tabs
            self.inventory_tab.save_changes() # ?
            self.skills_tab.save_changes()
            self.stats_tab.save_changes()
            self.appearance_tab.save_changes()
            self.misc_tab.save_changes()

            # 2. update
            char_name = self.root_save.get("character_name", "Viking").strip()
            
            # filename: lowercase name + .fch
            suggested_filename = f"{char_name.lower()}.fch"

            default_dir = os.path.dirname(self.current_fch) if getattr(self, 'current_fch', None) else ""
            default_save_path = os.path.join(default_dir, suggested_filename)

            # 3. open save dialog
            filename, _ = QFileDialog.getSaveFileName(
                self, 
                "Compile and Sign Valheim Save", 
                default_save_path, 
                "Valheim Character (*.fch)"
            )
            if not filename:
                return

            # 4. encode the player data back into hex and update the container
            updated_hex_payload = pack_player_data_hex(self.player_data)
            self.root_save["player_data_hex"] = updated_hex_payload

            # 5. temp file to hold the wrapper JSON for the compiler
            temp_wrapper_path = filename + ".tmp_wrapper.json"
            with open(temp_wrapper_path, "w", encoding="utf-8") as f:
                json.dump(self.root_save, f, indent=4, ensure_ascii=False)

            # compile and "sign" the .fch file (he said "sign" hahah, idiotic)
            compile_fch(temp_wrapper_path, filename)
            if os.path.exists(temp_wrapper_path):
                os.remove(temp_wrapper_path)

            QMessageBox.information(
                self, "Success", 
                f"Character save compiled, signed, and saved successfully!\n\nLocation:\n{filename}"
            )

            # QMessageBox.information(
            #     self, "Debug Info",
            #     f"Model Index: {self.player_data.get('model_index')}\n"
            #     f"Hair Style: {repr(self.player_data.get('hair'))}\n"
            #     f"Beard Style: {repr(self.player_data.get('beard'))}\n"
            #     f"Skin Color: {self.player_data.get('skin_color')}\n"
            #     f"Hair Color: {self.player_data.get('hair_color')}\n"
            #     f"Character Name: {self.root_save.get('character_name')}\n"
            # )
            
            self.current_fch = filename

        except Exception as e:
            if 'temp_wrapper_path' in locals() and os.path.exists(temp_wrapper_path):
                os.remove(temp_wrapper_path)
            QMessageBox.critical(self, "Compilation Error", f"Failed to repack and sign the .fch file:\n{str(e)}")
