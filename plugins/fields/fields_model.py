from typing import List

import PySide6.QtCore as qc

from query import Query


# A model that operates on the fields of a query
class FieldsModel(qc.QAbstractListModel):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

        self.query.query_changed.connect(self.update)

    def data(self, index: qc.QModelIndex, role: qc.Qt.ItemDataRole):
        if role == qc.Qt.ItemDataRole.DisplayRole:
            return self.query.get_fields()[index.row()]

    def add_field(self, field: str):
        self.query.add_field(field)
        self.dataChanged.emit(
            self.index(0),
            self.index(len(self.query.fields) - 1),
            [qc.Qt.ItemDataRole.DisplayRole],
        )

    def remove_field(self, field: str):
        if field in self.query.fields:
            self.query.remove_field(field)
            self.dataChanged.emit(self.index(0), self.index(len(self.query.fields) - 1))

    def get_fields(self) -> List[str]:
        return self.query.get_fields()

    def update(self):
        self.beginResetModel()
        self.endResetModel()

    def set_fields(self, fields: List[str]):
        self.beginResetModel()
        self.query.set_fields(fields)
        self.endResetModel()

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.query.fields if self.query.fields else [])

    def flags(self, index: qc.QModelIndex):
        if index.isValid():
            return qc.Qt.ItemFlag.ItemIsEnabled | qc.Qt.ItemFlag.ItemIsSelectable
        return qc.Qt.ItemFlag()

    def move_up(self, index: qc.QModelIndex):
        if index.row() > 0:
            self.query.move_field(index.data(), index.row() - 1)
            self.dataChanged.emit(index, index)

    def move_down(self, index: qc.QModelIndex):
        if index.row() < len(self.query.fields) - 1:
            self.query.move_field(index.data(), index.row() + 1)
            self.dataChanged.emit(index, index)
