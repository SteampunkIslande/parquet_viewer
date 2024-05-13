from typing import List
import PySide6.QtCore as qc
import PySide6.QtGui as qg
import PySide6.QtWidgets as qw

from PySide6.QtCore import Qt

import duckdb as db
import polars as pl

import functools


class WindowState(qc.QObject):
    singleton = None

    selected_fields_changed = qc.Signal(list)  # SELECT
    file_path_changed = qc.Signal(str)  # FROM
    filters_changed = qc.Signal(list)  # WHERE
    page_changed = qc.Signal(int)  # OFFSET
    rows_per_page_changed = qc.Signal(int)  # LIMIT

    def __init__(self):
        super().__init__()
        self.selected_fields = ["Chrom", "Position", "N.Ref", "N.Alt"]
        self.page = 1
        self.rows_per_page = 10
        self.filters = []
        self.file_path = None

    def update_selected_fields(self, fields):
        if self.sender():
            self.sender().blockSignals(True)

        # Add fields that are still in the new list, and those that were not in the old list
        self.selected_fields = [f for f in self.selected_fields if f in fields] + [
            f for f in fields if f not in self.selected_fields
        ]
        self.selected_fields_changed.emit(fields)

        if self.sender():
            self.sender().blockSignals(False)

    def update_filters(self, filters):
        if self.sender():
            self.sender().blockSignals(True)

        self.filters = filters
        self.filters_changed.emit(filters)

        if self.sender():
            self.sender().blockSignals(False)

    def update_file_path(self, file_path):
        if self.sender():
            self.sender().blockSignals(True)

        self.file_path = file_path
        self.file_path_changed.emit(file_path)

        if self.sender():
            self.sender().blockSignals(False)

    def update_page(self, page):
        if self.sender():
            self.sender().blockSignals(True)

        self.page = page
        self.page_changed.emit(page)

        if self.sender():
            self.sender().blockSignals(False)

    def update_rows_per_page(self, rows_per_page):
        if self.sender():
            self.sender().blockSignals(True)

        self.rows_per_page = rows_per_page
        self.rows_per_page_changed.emit(rows_per_page)

        if self.sender():
            self.sender().blockSignals(False)

    @staticmethod
    def get_singleton():
        if WindowState.singleton is None:
            WindowState.singleton = WindowState()
        return WindowState.singleton


class FieldsModel(qc.QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields = []
        self.selected_fields = []

    def flags(self, index: qc.QModelIndex):
        return (
            super().flags(index)
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEditable
        )

    def rowCount(self, parent=qc.QModelIndex()):
        return len(self.fields)

    def data(self, index: qc.QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if index.row() < 0 or index.row() >= len(self.fields):
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self.fields[index.row()]
        if role == Qt.ItemDataRole.CheckStateRole:
            return (
                Qt.CheckState.Checked
                if self.selected_fields[index.row()]
                else Qt.CheckState.Unchecked
            )

    def setData(self, index: qc.QModelIndex, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.CheckStateRole:
            self.selected_fields[index.row()] = not (
                Qt.CheckState(value) == Qt.CheckState.Unchecked
            )
            self.dataChanged.emit(index, index)
            return True
        return False

    def load_data(self, fields):
        self.beginResetModel()
        self.fields = fields
        self.selected_fields = [False for _ in fields]
        self.endResetModel()

    def set_selected_fields(self, selected_fields):
        self.beginResetModel()
        self.selected_fields = [f in selected_fields for f in self.fields]
        self.endResetModel()


class FieldsWidget(qw.QWidget):

    selected_fields_changed = qc.Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setup_layout()

    def setup_layout(self):
        layout = qw.QVBoxLayout()

        self.fields_view = qw.QListView()
        self.fields_model = FieldsModel()
        self.proxy_model = qc.QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.fields_model)
        self.proxy_model.dataChanged.connect(self.on_selected_fields_changed)
        self.fields_view.setModel(self.proxy_model)

        self.search_field = qw.QLineEdit()
        self.search_field.setPlaceholderText("Search fields")
        self.search_field.textChanged.connect(self.proxy_model.setFilterFixedString)

        layout.addWidget(self.fields_view)
        layout.addWidget(self.search_field)

        self.setLayout(layout)

    def on_selected_fields_changed(self):
        selected_fields = [
            f
            for f, s in zip(self.fields_model.fields, self.fields_model.selected_fields)
            if s
        ]
        self.selected_fields_changed.emit(selected_fields)


class FiltersModel(qc.QAbstractListModel):

    filters_changed = qc.Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters = []

    def index(self, row, column=0, parent=qc.QModelIndex()):
        return self.createIndex(row, column)

    def rowCount(self, parent=qc.QModelIndex()):
        return len(self.filters)

    def data(self, index: qc.QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if index.row() < 0 or index.row() >= len(self.filters):
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self.filters[index.row()]

    def removeRow(self, row, parent=qc.QModelIndex()):
        if self.filters:
            self.filters.pop(row)
            self.dataChanged.emit(self.index(row), self.index(row + 1))

    def add_filter(self, filter):
        self.filters.append(filter)
        self.dataChanged.emit(
            self.index(len(self.filters) - 1), self.index(len(self.filters))
        )
        self.filters_changed.emit(self.filters)


class FiltersWidget(qw.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.filters_view = qw.QListView()
        self.filters_model = FiltersModel()
        self.filters_view.setModel(self.filters_model)

        # Add 'remove filter' action in context menu
        self.filters_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.filters_view.customContextMenuRequested.connect(self.show_context_menu)

        # Add a title label 'Filters'
        self.title_label = qw.QLabel("Filters")

        self.setup_layout()

    def setup_layout(self):
        layout = qw.QVBoxLayout()

        layout.addWidget(self.title_label)
        layout.addWidget(self.filters_view)

        self.setLayout(layout)

    def add_filter(self, filter):
        self.filters_model.add_filter(filter)

    def remove_filter(self, index: qc.QModelIndex):
        self.filters_model.removeRow(index.row())

    def show_context_menu(self, pos):
        index = self.filters_view.indexAt(pos)
        if index.isValid():
            menu = qw.QMenu()
            remove_action = menu.addAction("Remove filter")
            action = menu.exec(self.filters_view.mapToGlobal(pos))
            if action == remove_action:
                self.filters_model.removeRow(index.row())


class ItemDelegate(qw.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def initStyleOption(self, option: qw.QStyleOptionViewItem, index: qc.QModelIndex):
        super().initStyleOption(option, index)
        option.text = str(index.data(Qt.ItemDataRole.DisplayRole))
        if index.data(Qt.ItemDataRole.UserRole) is not None:
            option.font = index.data(Qt.ItemDataRole.UserRole).get("font", option.font)
            option.palette = index.data(Qt.ItemDataRole.UserRole).get(
                "palette", option.palette
            )


class VariantsModel(qc.QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._header = []

        self.sorted_columns = []

    def rowCount(self, parent=qc.QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=qc.QModelIndex()):
        return len(self._data[0]) if self._data else 0

    def data(self, index: qc.QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if index.row() < 0 or index.row() >= len(self._data):
            return None
        if index.column() < 0 or index.column() >= len(self._data[0]):
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            val = self._data[index.row()][index.column()]
            if isinstance(val, float):
                return f"{val:.3e}"
            if val is None:
                return "NULL"
            return str(val)
        # User role is used to return a dict containing style options
        if role == Qt.ItemDataRole.UserRole:
            style_options = {}
            if self._data[index.row()][index.column()] is None:
                font = qg.QFont(qw.QApplication.font())
                font.setItalic(True)
                style_options["font"] = font
            if self.data(index, Qt.ItemDataRole.DisplayRole) in self.sorted_columns:
                icon = qg.QIcon("sort.png")

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._header[section]
            else:
                return None

    def load_data(self, data: List[dict]):
        self.beginResetModel()
        if data:
            self._header = list(data[0].keys())
            self._data = [tuple(d.get(h, "") for h in self._header) for d in data]
        else:
            self._header = []
            self._data = []
        self.endResetModel()


class FiltersDialog(qw.QDialog):
    def __init__(self, field_name, parent=None):
        super().__init__(parent)
        # Add a label with field name
        self.field_label = qw.QLabel(field_name)
        # Add a line edit to enter the filter operator
        self.operator_cb = qw.QComboBox()
        self.operator_cb.addItems(
            ["=", ">", "<", ">=", "<=", "!=", "IN", "NOT IN", "IS", "IS NOT"]
        )
        # Add a line edit to enter the filter value
        self.value_lineedit = qw.QLineEdit()
        self.value_lineedit.setPlaceholderText(
            "Enter value to filter by. To refer to other column names, use double quotes."
        )

        self.field_name = field_name

        self.ok_button = qw.QPushButton("OK")
        self.cancel_button = qw.QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.setup_layout()
        # Add OK and Cancel buttons

    def setup_layout(self):
        layout = qw.QVBoxLayout()
        layout.addWidget(self.field_label)
        layout.addWidget(self.operator_cb)
        layout.addWidget(self.value_lineedit)
        ok_cancel_layout = qw.QHBoxLayout()
        ok_cancel_layout.addWidget(self.ok_button)
        ok_cancel_layout.addWidget(self.cancel_button)
        layout.addLayout(ok_cancel_layout)

        self.setLayout(layout)

    def get_filter(self):
        val = self.value_lineedit.text()
        if '"' not in val:
            val = f"'{val}'"
        return f""" "{self.field_name}" {self.operator_cb.currentText()} {val} """


class VariantWidget(qw.QWidget):

    fields_order_changed = qc.Signal(list)

    def __init__(self, filters_widget: FiltersWidget = None, parent=None):
        super().__init__(parent)

        self.table_view = qw.QTableView()
        self.table_model = VariantsModel()
        self.table_view.setModel(self.table_model)
        self.table_view.setItemDelegate(ItemDelegate())

        self.table_view.horizontalHeader().setSectionResizeMode(
            qw.QHeaderView.ResizeMode.Interactive
        )
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionsMovable(True)
        self.table_view.horizontalHeader().sectionMoved.connect(self.on_header_moved)
        # Add a context menu to the table view header (to add filtering and sorting options)
        self.table_view.horizontalHeader().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.table_view.horizontalHeader().customContextMenuRequested.connect(
            self.header_view_context_menu
        )

        # Add title label 'Variants view'
        self.title_label = qw.QLabel("Variants view")

        # Add page selector
        self.page_selector = PageSelector()

        self.filters_widget = filters_widget

        self.setup_layout()

    def header_view_context_menu(self, pos):
        menu = qw.QMenu()
        field_name = (
            self.table_view.horizontalHeader()
            .model()
            .headerData(
                self.table_view.horizontalHeader().logicalIndexAt(pos.x()),
                Qt.Orientation.Horizontal,
            )
        )
        self.filter_action = menu.addAction(
            f"Filter {field_name}",
            functools.partial(self.add_filter, field_name),
        )
        self.sort_action = menu.addAction(
            f"Order by {field_name}", functools.partial(self.add_sort, field_name)
        )
        menu.exec(self.table_view.horizontalHeader().mapToGlobal(pos))

    def add_filter(self, field_name):
        dlg = FiltersDialog(field_name)
        if not self.filters_widget:
            return
        if dlg.exec() == qw.QDialog.DialogCode.Accepted:
            self.filters_widget.add_filter(dlg.get_filter())

    def add_sort(self, field_name):
        field_name = (
            self.table_view.horizontalHeader()
            .model()
            .headerData(
                self.table_view.horizontalHeader().logicalIndexAt(
                    self.table_view.horizontalHeader()
                    .mapFromGlobal(qg.QCursor.pos())
                    .x()
                ),
                Qt.Orientation.Horizontal,
            )
        )

    def setup_layout(self):
        self.main_layout = qw.QVBoxLayout()
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addWidget(self.table_view)
        self.main_layout.addWidget(self.page_selector)
        self.setLayout(self.main_layout)

    def on_header_moved(self):
        fields = [
            self.table_view.horizontalHeader()
            .model()
            .headerData(i, Qt.Orientation.Horizontal)
            for i in map(
                lambda x: self.table_view.horizontalHeader().logicalIndex(x),
                range(self.table_view.horizontalHeader().model().columnCount()),
            )
        ]
        self.fields_order_changed.emit(fields)


class PageSelector(qw.QWidget):

    # page_changed emits the new page number (1-indexed)
    page_changed = qc.Signal(int)
    rows_per_page_changed = qc.Signal(int)

    def __init__(self):
        super().__init__()
        self.rows_label = qw.QLabel("Rows per page")
        self.rows_lineedit = qw.QLineEdit()
        self.rows_lineedit.setText("10")
        self.rows_lineedit.setValidator(qg.QIntValidator(1, 100))
        self.rows_lineedit.textChanged.connect(
            lambda x: self.rows_per_page_changed.emit(int(x))
        )
        self.rows_per_page_changed.connect(self.set_rows_per_page)
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

        self.initial_state()

        self.setup_layout()

    def initial_state(self):
        self.current_page = 1
        self.page_count = 1
        self.rows_count = 0
        self.rows_per_page = 10

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
        self.current_page = 1
        self.page_lineedit.setText(str(self.current_page))
        self.page_changed.emit(self.current_page)

    def goto_previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.page_lineedit.setText(str(self.current_page))
            self.page_changed.emit(self.current_page)

    def goto_next_page(self):
        if self.current_page < self.page_count:
            self.current_page += 1
            self.page_lineedit.setText(str(self.current_page))
            self.page_changed.emit(self.current_page)

    def goto_last_page(self):
        self.current_page = self.page_count
        self.page_lineedit.setText(str(self.current_page))
        self.page_changed.emit(self.current_page)

    def on_total_rows_changed(self, total_rows):
        self.page_count = total_rows // self.rows_per_page
        if total_rows % self.rows_per_page:
            self.page_count += 1
        self.rows_count = total_rows
        self.page_count_label.setText(f"out of {self.page_count}")
        self.page_lineedit.setValidator(qg.QIntValidator(1, self.page_count))

    def set_page(self, page):
        self.current_page = int(page)
        self.page_changed.emit(self.current_page)

    def set_rows_per_page(self, rows_per_page):
        self.rows_per_page = rows_per_page
        self.rows_lineedit.setText(str(rows_per_page))


class MainWindow(qw.QMainWindow):
    def __init__(self):
        super().__init__()

        # Create widgets
        self.filters_view = FiltersWidget()
        self.fields_view = FieldsWidget()
        self.variant_view = VariantWidget()
        self.variant_view.filters_widget = self.filters_view

        self.setWindowTitle("My App")
        self.setup_layout()
        self.add_actions()

        self.window_state = WindowState.get_singleton()
        self.fields_view.fields_model.selected_fields = (
            self.window_state.selected_fields
        )

        # Connect signals between widgets and window state
        self.fields_view.selected_fields_changed.connect(
            self.window_state.update_selected_fields
        )
        self.variant_view.fields_order_changed.connect(
            self.window_state.update_selected_fields
        )
        self.filters_view.filters_model.filters_changed.connect(
            self.window_state.update_filters
        )
        self.variant_view.page_selector.page_changed.connect(
            self.window_state.update_page
        )
        self.variant_view.page_selector.rows_per_page_changed.connect(
            self.window_state.update_rows_per_page
        )

        self.window_state.selected_fields_changed.connect(self.load_data)
        self.window_state.filters_changed.connect(self.load_data)
        self.window_state.file_path_changed.connect(self.load_data)
        self.window_state.page_changed.connect(self.load_data)
        self.window_state.rows_per_page_changed.connect(self.load_data)

    def add_actions(self):
        # Create actions
        self.open_action = qg.QAction("Open", self)
        self.exit_action = qg.QAction("Exit", self)

        # Add actions to menu
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.exit_action)

        # Connect actions to slots
        self.open_action.triggered.connect(self.open_file)
        self.exit_action.triggered.connect(self.close)

    def open_file(self):
        file_path, _ = qw.QFileDialog.getOpenFileName(
            self, "Open file", "", "Parquet files (*.parquet)"
        )
        if file_path:
            self.window_state.update_file_path(file_path)
            self.load_data()

    def setup_layout(self):

        # Create layout
        layout = qw.QHBoxLayout()
        splitter = qw.QSplitter()

        splitter.addWidget(self.filters_view)
        splitter.addWidget(self.variant_view)
        splitter.addWidget(self.fields_view)

        layout.addWidget(splitter)

        # Set layout to main window
        central_widget = qw.QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def load_data(self):

        column_names = pl.scan_parquet(self.window_state.file_path).columns
        self.fields_view.fields_model.load_data(column_names)
        self.fields_view.fields_model.set_selected_fields(
            self.window_state.selected_fields
        )

        self.table = query_data(
            self.window_state.selected_fields,
            self.window_state.file_path,
            self.window_state.filters,
            self.window_state.rows_per_page,
            (self.window_state.page - 1) * self.window_state.rows_per_page,
        )
        self.variant_view.table_model.load_data(self.table)
        self.variant_view.page_selector.on_total_rows_changed(
            count_rows(
                self.window_state.file_path,
                self.window_state.filters,
            )
        )


def query_data(selected_fields, file_path, filters, limit, offset):
    q = "SELECT "
    if selected_fields:
        q += ", ".join(map(lambda x: '"' + x + '"', selected_fields))
    else:
        q += "*"
    q += f" FROM '{file_path}'"
    if filters:
        q += f" WHERE {' AND '.join(filters)} "
    q += f" LIMIT {limit} OFFSET {offset}"
    print(q)

    return db.sql(q).pl().to_dicts()


def count_rows(file_path, filters):
    q = "SELECT COUNT(*) as row_count"
    q += f" FROM '{file_path}'"
    if filters:
        q += f" WHERE {' AND '.join(filters)} "

    print(q)
    return db.sql(q).pl().to_dicts()[0]["row_count"]


if __name__ == "__main__":
    app = qw.QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
