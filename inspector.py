import PySide6.QtWidgets as qw

from plugins.validation.validation_widget import ValidationWidget
from query import Query


class Inspector(qw.QWidget):

    def __init__(self, query: Query, parent=None):
        super().__init__(parent)

        self._layout = qw.QVBoxLayout()

        self.query = query

        self.main_widget = qw.QTabWidget()
        self._layout.addWidget(self.main_widget)

        self.tabs = {}

        self.setLayout(self._layout)

        self.setup()

    def setup(self):

        self.validation_widget = ValidationWidget(self.query)
        self.main_widget.addTab(self.validation_widget, "Validation")
