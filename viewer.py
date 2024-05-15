#!/usr/bin/env python


import json
from pathlib import Path

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from fields.fields_widget import FieldsWidget
from query import Query
from table.query_table_widget import QueryTableWidget


class MainWindow(qw.QMainWindow):

    def __init__(self):
        super().__init__()

        self.query = Query()

        self.fields_widget = FieldsWidget(self.query)
        self.query_table_widget = QueryTableWidget(self.query)

        # Add table view on the left, separated by a splitter from the fields widget
        self.splitter = qw.QSplitter()
        self.splitter.addWidget(self.fields_widget)
        self.splitter.addWidget(self.query_table_widget)

        self.setCentralWidget(self.splitter)

        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")
        self.open_action = self.file_menu.addAction("Open")
        self.open_action.triggered.connect(self.open_file)

        self.load_previous_session()

    def load_previous_session(self):
        prefs = self.get_user_prefs()
        if "query" not in prefs:
            return
        self.query.from_dict(prefs["query"])

    def open_file(self):
        last_open_files = self.get_user_prefs().get("last_files", None)
        if not last_open_files:
            d = Path().home()
        else:
            d = Path(last_open_files[0]).parent
        files, _ = qw.QFileDialog.getOpenFileNames(
            self,
            "Open Parquet file",
            dir=str(d),
            filter="Parquet files (*.parquet)",
        )
        if files:
            self.save_user_prefs({"last_files": files})
            self.query.set_files([Path(f) for f in files])

    def closeEvent(self, event: qg.QCloseEvent):
        self.save_user_prefs({"query": self.query.to_dict()})
        event.accept()

    def save_user_prefs(self, prefs: dict):

        user_prefs = Path(
            qc.QStandardPaths().writableLocation(
                qc.QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        user_prefs.mkdir(parents=True, exist_ok=True)
        old_prefs = {}
        if (user_prefs / "config.json").exists():
            with open(user_prefs / "config.json", "r") as f:
                old_prefs = json.load(f)

        old_prefs.update(prefs)

        with open(user_prefs / "config.json", "w") as f:
            json.dump(old_prefs, f)

    def get_user_prefs(self):
        user_prefs = Path(
            qc.QStandardPaths().writableLocation(
                qc.QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        prefs = {}
        if (user_prefs / "config.json").exists():
            with open(user_prefs / "config.json", "r") as f:
                prefs = json.load(f)
        return prefs


if __name__ == "__main__":
    app = qw.QApplication([])

    app.setOrganizationName("CharlesMB")
    app.setApplicationName("ParquetViewer")

    window = MainWindow()
    window.show()

    app.exec()
