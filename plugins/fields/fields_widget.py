#!/usr/bin/env python

from typing import List

import polars as pl
import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from common_widgets.string_list_chooser import StringListChooser
from plugins.fields.fields_model import FieldsModel
from query import Query


class FieldsWidget(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self.view = qw.QListView()
        self.model = FieldsModel(query)
        self.view.setModel(self.model)

        self.view.setDragEnabled(True)
        self.view.setAcceptDrops(True)

        self.add_action = qg.QAction("Add", self)
        self.remove_action = qg.QAction("Remove", self)

        self.addAction(self.add_action)
        self.addAction(self.remove_action)

        self.add_action.triggered.connect(self.add_fields)
        self.remove_action.triggered.connect(self.remove_field)

        self.add_button = qw.QPushButton("Add")
        self.remove_button = qw.QPushButton("Remove")
        self.move_up_button = qw.QPushButton("Move up")
        self.move_down_button = qw.QPushButton("Move down")

        layout = qw.QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(self.add_button)
        layout.addWidget(self.remove_button)
        layout.addWidget(self.move_up_button)
        layout.addWidget(self.move_down_button)

        self.setLayout(layout)

        self.add_button.clicked.connect(self.add_fields)
        self.remove_button.clicked.connect(self.remove_field)
        self.move_up_button.clicked.connect(self.move_up)
        self.move_down_button.clicked.connect(self.move_down)

        self.query = query

    def add_fields(self):
        if not self.query.files:
            qw.QMessageBox.warning(
                self, "No file selected", "Please select a file first"
            )
            return
        available_fields = pl.scan_parquet(self.query.files).columns
        dialog = StringListChooser(available_fields, self)
        if dialog.exec() == qw.QDialog.DialogCode.Accepted:
            selected_fields = dialog.get_selected()
            for field in selected_fields:
                self.model.add_field(field)

    def remove_field(self):
        selected = self.view.selectedIndexes()
        if selected:
            # No need to sort, as we are removing fields by name
            for s in selected:
                self.model.remove_field(s.data(qc.Qt.ItemDataRole.DisplayRole))

    def get_fields(self) -> List[str]:
        return self.model.get_fields()

    def set_fields(self, fields: List[str]):
        self.model.set_fields(fields)

    def move_up(self):
        selected = self.view.selectedIndexes()
        if not selected[0].row() > 0:
            return
        if selected:
            self.model.move_up(selected[0])
            self.view.setCurrentIndex(self.view.model().index(selected[0].row() - 1))

    def move_down(self):
        selected = self.view.selectedIndexes()
        if not selected[0].row() < len(self.model.get_fields()) - 1:
            return
        if selected:
            self.model.move_down(selected[0])
            self.view.setCurrentIndex(self.view.model().index(selected[0].row() + 1))
