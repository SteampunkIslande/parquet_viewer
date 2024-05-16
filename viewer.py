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

        self.load_previous_session()

    def load_previous_session(self):
        prefs = self.get_user_prefs()
        if "query" not in prefs:
            return
        self.query.from_dict(prefs["query"])

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
