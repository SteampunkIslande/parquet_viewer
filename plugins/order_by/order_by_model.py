import PySide6.QtCore as qc

from query import Query


class OrderByModel(qc.QAbstractListModel):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

        self.query.order_by_changed.connect(self.update)

    def data(self, index: qc.QModelIndex, role: qc.Qt.ItemDataRole):
        if role == qc.Qt.ItemDataRole.DisplayRole:
            return self.query.get_order_by()[index.row()]

    def add_order_by(self, field: str):
        old_order_by = self.query.get_order_by()

    def update(self):
        self.beginResetModel()
        self.endResetModel()
