import polars as pl
import PySide6.QtCore as qc
import PySide6.QtWidgets as qw

from common_widgets.multiwidget_holder import MultiWidgetHolder
from common_widgets.searchable_list import SearchableList
from query import Query


class ValidationWidgetWelcomePage(qw.QWidget):

    new_validation = qc.Signal()
    continue_validation = qc.Signal()

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

        self.setup_layout()

    def setup_layout(self):
        layout = qw.QVBoxLayout()
        layout.addWidget(
            qw.QLabel(
                "Please choose a pending validation to continue or click 'Create new validation' button below."
            )
        )
        layout.addWidget(qw.QPushButton("Create new validation"))

        self.setLayout(layout)

    def new_validation(self):
        pass


class ValidationWidgetPageOne(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

        self.files_selection_widget = qw.QListView()
        self.files_selection_model = qc.QStringListModel()

        self.files_selection_widget.setModel(self.files_selection_model)

        self.open_files_button = qw.QPushButton("Open files")
        self.open_files_button.clicked.connect(self.open_files)

        self.chosen_files = []

        self.setup_layout()

    def open_files(self):
        new_files, _ = qw.QFileDialog.getOpenFileNames(
            self, "Open files", "", "Parquet files (*.parquet)"
        )
        self.chosen_files = [
            f for f in self.chosen_files if f not in new_files
        ] + new_files
        self.files_selection_model.setStringList(self.chosen_files)

    def get_chosen_files(self):
        return self.chosen_files

    def setup_layout(self):
        self._layout = qw.QVBoxLayout()
        self._layout.addWidget(qw.QLabel("Select files to validate"))
        self._layout.addWidget(self.files_selection_widget)
        self.setLayout(self._layout)


class ValidationWidgetPageTwo(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)
        self.query = query

        self.fields_selection_widget = SearchableList(
            pl.scan_parquet(self.query.files).columns
        )

        self.setup_layout()

    def get_selected_fields(self):
        return self.fields_selection_widget.get_selected()

    def setup_layout(self):
        layout = qw.QVBoxLayout()
        layout.addWidget(qw.QLabel("Select samples to validate"))
        self.setLayout(layout)


class ValidationWidget(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self.query = query

        self.multi_widget_holder = MultiWidgetHolder()
        self.multi_widget_holder.add_widget(
            ValidationWidgetWelcomePage(query), "welcome"
        )
        self.multi_widget_holder.add_widget(ValidationWidgetPageOne(query), "one")

        self.multi_widget_holder.set_current_widget("welcome")

        self.setup_layout()

    def setup_layout(self):

        self._layout = qw.QVBoxLayout()
        self._layout.addWidget(self.multi_widget_holder)
        self.setLayout(self._layout)
