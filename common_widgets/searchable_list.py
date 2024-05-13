from typing import List

import PySide6.QtCore as qc
import PySide6.QtWidgets as qw


class SearchableList(qw.QWidget):

    def __init__(self, items: List[str], filter_type="fixed_string", parent=None):
        super().__init__(parent)

        self.items = items
        self.model = qc.QStringListModel(items)

        self.proxy_model = qc.QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.view = qw.QListView()
        self.view.setModel(self.proxy_model)

        self.view.setSelectionMode(qw.QAbstractItemView.SelectionMode.MultiSelection)

        self.filter_le = qw.QLineEdit()
        self.filter_le.setPlaceholderText("Filter list...")

        layout = qw.QVBoxLayout()
        layout.addWidget(self.filter_le)
        layout.addWidget(self.view)

        self.setLayout(layout)

        self.filter_le_callbacks = {
            "fixed_string": self.proxy_model.setFilterFixedString,
            "regexp": self.proxy_model.setFilterRegularExpression,
        }
        self.selected_filter_callback = self.filter_le_callbacks[filter_type]

        self.filter_le.textChanged.connect(self.on_filter_changed)

    def get_selected(self) -> str:
        selected = self.view.selectedIndexes()
        if selected:
            return [s.data(qc.Qt.ItemDataRole.DisplayRole) for s in selected]
        return []

    def set_filter_type(self, filter_type):
        if filter_type in self.filter_le_callbacks:
            self.selected_filter_callback = self.filter_le_callbacks[filter_type]

    def on_filter_changed(self):
        self.selected_filter_callback(self.filter_le.text())
