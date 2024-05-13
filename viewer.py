#!/usr/bin/env python

from pathlib import Path

import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from typing import List, Tuple

import duckdb as db
import polars as pl

from cachetools import cached


@cached(cache={})
def run_sql(query: str) -> List[dict]:
    return db.sql(query).pl().to_dicts()


class Query(qc.QObject):

    # Signals for internal use only
    fields_changed = qc.Signal()
    filters_changed = qc.Signal()
    order_by_changed = qc.Signal()
    limit_changed = qc.Signal()
    offset_changed = qc.Signal()
    file_changed = qc.Signal()

    # Signals for external use
    query_changed = qc.Signal()

    def __init__(self) -> None:
        super().__init__()

        self.init_state()

        self.fields_changed.connect(self.update)
        self.filters_changed.connect(self.update)
        self.order_by_changed.connect(self.update)
        self.limit_changed.connect(self.update)
        self.offset_changed.connect(self.update)
        self.file_changed.connect(self.update)

    def init_state(self):
        self.fields = []
        self.filters = []
        self.order_by = []
        self.limit = 10
        self.offset = 0
        self.file = None

        self.current_page = 1
        self.page_count = 1

        self.data = []
        self.header = []

    def add_field(self, field: str):
        self.fields.append(f'"{field}"')
        self.fields_changed.emit()

        return self

    def remove_field(self, field: str):
        if field in self.fields:
            self.fields.remove(field)
            self.fields_changed.emit()

        return self

    def move_field(self, field: str, pos: int):
        if field in self.fields:
            self.fields.remove(field)
            self.fields.insert(pos, field)
            self.fields_changed.emit()

    def get_fields(self) -> List[str]:
        return self.fields

    def set_fields(self, fields: List[str]):
        self.fields = fields
        self.fields_changed.emit()

        return self

    def get_file(self) -> Path:
        return self.file

    def set_file(self, file: Path):
        self.init_state()
        self.file = file
        self.file_changed.emit()

        return self

    def add_filter(self, f):
        self.filters.append(f)
        self.filters_changed.emit()

        return self

    def remove_filter(self, f):
        self.filters.remove(f)
        self.filters_changed.emit()

        return self

    def get_filters(self) -> List[str]:
        return self.filters

    def set_filters(self, filters: List[str]):
        self.filters = filters
        self.filters_changed.emit()

        return self

    def get_order_by(self) -> List[Tuple[str, str]]:
        return self.order_by

    def set_order_by(self, order_by: List[Tuple[str, str]]):
        self.order_by = order_by
        self.order_by_changed.emit()

        return self

    def get_limit(self) -> int:
        return self.limit

    def set_limit(self, limit):
        self.limit = limit
        self.limit_changed.emit()

        return self

    def get_offset(self) -> int:
        return self.offset

    def set_offset(self, offset):
        self.offset = offset
        self.offset_changed.emit()
        return self

    def set_page(self, page):
        self.current_page = page
        self.set_offset((page - 1) * self.limit)

        return self

    def get_page(self):
        return self.current_page

    def previous_page(self):
        if self.current_page > 1:
            self.set_page(self.current_page - 1)

        return self

    def next_page(self):
        if self.current_page < self.page_count:
            self.set_page(self.current_page + 1)

        return self

    def first_page(self):
        self.set_page(1)

        return self

    def last_page(self):
        self.set_page(self.page_count)

        return self

    def get_page_count(self):
        return self.page_count

    def get_data(self):
        return self.data

    def get_header(self):
        return self.header

    def select_query(self):
        fields = ", ".join(self.fields) or "*"
        filters = " AND ".join(self.filters)
        order_by = ", ".join(
            [f"{field} {direction}" for field, direction in self.order_by]
        )

        if filters:
            filters = f"WHERE {filters}"
        if order_by:
            order_by = f"ORDER BY {order_by}"
        return f"SELECT {fields} FROM '{self.file}' {filters} {order_by} LIMIT {self.limit} OFFSET {self.offset}"

    def count_query(self):
        filters = " AND ".join(self.filters)
        if filters:
            filters = f" WHERE {filters} "
        return f"SELECT COUNT(*) AS count_star FROM '{self.file}'{filters}"

    def update(self):
        self.blockSignals(True)
        dict_data = run_sql(self.select_query())
        if dict_data:
            self.header = list(dict_data[0].keys())
            self.data = [list(row.values()) for row in dict_data]
        else:
            self.header = []
            self.data = []
        self.row_count = run_sql(self.count_query())[0]["count_star"]
        self.page_count = self.row_count // self.limit
        if self.row_count % self.limit > 0:
            self.page_count = self.page_count + 1
        if self.current_page > self.page_count:
            self.set_page(self.page_count)
        self.blockSignals(False)
        self.query_changed.emit()


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


class StringListChooser(qw.QDialog):

    def __init__(self, items: List[str], parent=None):
        super().__init__(parent)

        self.items = items
        self.widget = SearchableList(items)

        self.ok_cancel = qw.QDialogButtonBox()
        self.ok_cancel.setStandardButtons(
            qw.QDialogButtonBox.StandardButton.Ok
            | qw.QDialogButtonBox.StandardButton.Cancel
        )

        layout = qw.QVBoxLayout()
        layout.addWidget(self.widget)
        layout.addWidget(self.ok_cancel)

        self.setLayout(layout)

        self.ok_cancel.accepted.connect(self.accept)
        self.ok_cancel.rejected.connect(self.reject)

    def get_selected(self) -> List[str]:
        return self.widget.get_selected()


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
        if not self.query.file:
            qw.QMessageBox.warning(
                self, "No file selected", "Please select a file first"
            )
            return
        available_fields = pl.scan_parquet(self.query.file).columns
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


class QueryTableModel(qc.QAbstractTableModel):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query
        self.query_string = query.select_query()

        self.query.query_changed.connect(self.update)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.query.get_data())

    def columnCount(self, parent):
        if parent.isValid():
            return 0
        if self.query.get_data():
            return len(self.query.get_data()[0])
        return 0

    def data(self, index, role):
        if role == qc.Qt.ItemDataRole.DisplayRole:
            if index.row() < 0 or index.row() >= len(self.query.get_data()):
                return None
            if index.column() < 0 or index.column() >= len(self.query.get_data()[0]):
                return None
            return self.query.get_data()[index.row()][index.column()]

    def headerData(self, section, orientation, role):
        if section >= len(self.query.get_header()):
            return None
        if role == qc.Qt.ItemDataRole.DisplayRole:
            if orientation == qc.Qt.Orientation.Horizontal:
                return self.query.get_header()[section]

    def update(self):
        self.beginResetModel()
        self.endResetModel()


class PageSelector(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__()
        self.rows_label = qw.QLabel("Rows per page")
        self.rows_lineedit = qw.QLineEdit()
        self.rows_lineedit.setText("10")
        self.rows_lineedit.setValidator(qg.QIntValidator(1, 100))
        self.rows_lineedit.textChanged.connect(self.set_rows_per_page)

        self.spacer = qw.QSpacerItem(
            40, 20, qw.QSizePolicy.Policy.Expanding, qw.QSizePolicy.Policy.Minimum
        )
        self.first_page_button = qw.QPushButton("<<")
        self.first_page_button.clicked.connect(self.goto_first_page)
        self.prev_button = qw.QPushButton("<")
        self.prev_button.clicked.connect(self.goto_previous_page)
        self.page_label = qw.QLabel("Page")
        self.page_lineedit = qw.QLineEdit()
        self.page_lineedit.setFixedWidth(50)
        self.page_lineedit.setText("1")
        self.page_lineedit.setValidator(qg.QIntValidator(1, 1))
        self.page_lineedit.textChanged.connect(self.set_page)
        self.page_count_label = qw.QLabel("out of (unknown)")
        self.next_button = qw.QPushButton(">")
        self.next_button.clicked.connect(self.goto_next_page)
        self.last_page_button = qw.QPushButton(">>")
        self.last_page_button.clicked.connect(self.goto_last_page)

        self.query = query

        self.query.query_changed.connect(self.update_page_selector)

        self.query_string = query.count_query()

        self.setup_layout()

    def setup_layout(self):
        layout = qw.QHBoxLayout()
        layout.addWidget(self.rows_label)
        layout.addWidget(self.rows_lineedit)
        layout.addItem(self.spacer)
        layout.addWidget(self.first_page_button)
        layout.addWidget(self.prev_button)
        layout.addWidget(self.page_label)
        layout.addWidget(self.page_lineedit)
        layout.addWidget(self.page_count_label)
        layout.addWidget(self.next_button)
        layout.addWidget(self.last_page_button)
        self.setLayout(layout)

    def goto_first_page(self):
        self.query.first_page()

    def goto_previous_page(self):
        self.query.previous_page()

    def goto_next_page(self):
        self.query.next_page()

    def goto_last_page(self):
        self.query.last_page()

    def update_page_selector(self):
        # Block signals to avoid infinite loops
        self.page_lineedit.blockSignals(True)
        self.rows_lineedit.blockSignals(True)

        print("Updating page selector")

        self.rows_lineedit.setText(str(self.query.get_limit()))
        self.page_lineedit.setText(str(self.query.get_page()))

        self.page_lineedit.setValidator(
            qg.QIntValidator(1, self.query.get_page_count())
        )
        self.page_count_label.setText(f"out of {self.query.get_page_count()}")

        self.page_lineedit.blockSignals(False)
        self.rows_lineedit.blockSignals(False)

    def set_page(self, page):
        self.query.set_page(int(page) if page else 1)

    def set_rows_per_page(self, rows_per_page):
        self.query.set_limit(int(rows_per_page or 10))


class QueryTableWidget(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self.query = query
        self.model = QueryTableModel(query)

        self.table_view = qw.QTableView()
        self.table_view.setSelectionBehavior(
            qw.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_view.setSelectionMode(
            qw.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table_view.horizontalHeader().setStretchLastSection(
            True
        )  # Set last column to expand
        self.table_view.setModel(self.model)

        self.page_selector = PageSelector(query)

        layout = qw.QVBoxLayout()
        layout.addWidget(self.table_view)
        layout.addWidget(self.page_selector)

        self.setLayout(layout)


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
