from pathlib import Path

import duckdb as db
import PySide6.QtCore as qc


class ValidationModel(qc.QAbstractTableModel):
    def __init__(self, db_path: str):
        super().__init__()
        self._data = []
        self._header = []
        if db_path:
            self.conn = db.connect(db_path)
            self.load()

    def load(self):
        self.beginResetModel()
        data = self.conn.sql("SELECT * FROM validations").pl().to_dicts()
        if not data:
            self._data = []
            self._header = []
            return

        self._data = [list(row.values()) for row in data]
        self._header = list(data[0].keys())
        self.endResetModel()

    def new_validation(self, name: str):
        self.beginInsertRows(qc.QModelIndex(), len(self._data), len(self._data))
        user_name = Path().home().name
        self.conn.sql(
            f"INSERT INTO validations VALUES ({user_name}, current_timestamp, {name}, 'pending')"
        )
        self.endInsertRows()

    def removeRow(self, row, parent: qc.QModelIndex = qc.QModelIndex()):
        self.beginRemoveRows(qc.QModelIndex(), row, row)
        self.conn.sql(f"DELETE FROM validations WHERE uuid = {self._data[row][-1]}")
        self.endRemoveRows()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._data[0]) if self._data else 0
