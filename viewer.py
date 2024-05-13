#!/usr/bin/env python


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

    def open_file(self):
        file, _ = qw.QFileDialog.getOpenFileName(
            self, "Open Parquet file", filter="Parquet files (*.parquet)"
        )
        if file:
            self.query.set_file(file)


if __name__ == "__main__":
    app = qw.QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
