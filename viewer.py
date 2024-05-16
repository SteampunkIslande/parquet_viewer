#!/usr/bin/env python


from pathlib import Path

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from commons import load_user_prefs, save_user_prefs
from inspector import Inspector
from query import Query
from table.query_table_widget import QueryTableWidget


class MainWindow(qw.QMainWindow):

    def __init__(self):
        super().__init__()

        self.query = Query()

        self.query_table_widget = QueryTableWidget(self.query)
        self.inspector = Inspector(self.query)

        self.database = None

        self.main_widget = qw.QSplitter(qc.Qt.Orientation.Horizontal)
        self.main_widget.addWidget(self.inspector)
        self.main_widget.addWidget(self.query_table_widget)

        self.setCentralWidget(self.main_widget)

        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")
        self.open_action = self.file_menu.addAction("Open parquet file")
        self.new_action = self.file_menu.addAction("New analysis database")
        self.choose_database_action = self.file_menu.addAction("Open analysis database")

        self.open_action.triggered.connect(self.open_file)
        self.new_action.triggered.connect(self.open_database)
        self.choose_database_action.triggered.connect(self.open_database)

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

    def open_database(self):
        last_database = self.get_user_prefs().get("analysis_database", None)
        if not last_database:
            d = Path().home()
        else:
            d = Path(last_database).parent
        database, _ = qw.QFileDialog.getOpenFileName(
            self,
            "Open DuckDB database",
            dir=str(d),
            filter="DuckDB database files (*.db)",
        )
        if database:
            self.save_user_prefs({"analysis_database": database})
            self.database = database

    def new_database(self):
        last_database = self.get_user_prefs().get("analysis_database", None)
        if not last_database:
            d = Path().home()
        else:
            d = Path(last_database).parent
        database, _ = qw.QFileDialog.getSaveFileName(
            self,
            "Create DuckDB database",
            dir=str(d),
            filter="DuckDB database files (*.db)",
        )
        if database:
            self.save_user_prefs({"analysis_database": database})
            self.database = database

    def closeEvent(self, event: qg.QCloseEvent):
        self.save_user_prefs({"query": self.query.to_dict()})
        event.accept()

    def save_user_prefs(self, prefs: dict):
        save_user_prefs(prefs)

    def get_user_prefs(self):
        return load_user_prefs()


if __name__ == "__main__":
    app = qw.QApplication([])

    app.setOrganizationName("CharlesMB")
    app.setApplicationName("ParquetViewer")

    window = MainWindow()
    window.show()

    app.exec()
