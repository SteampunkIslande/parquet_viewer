#!/usr/bin/env python

from pathlib import Path
from typing import List, Tuple

import duckdb as db
import polars as pl
import PySide6.QtCore as qc
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
        self.files = None

        self.current_page = 1
        self.page_count = 1

        self.data = []
        self.header = []

    def add_field(self, field: str):
        self.fields.append(field)
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

    def set_files(self, files: List[Path]):
        self.init_state()
        self.files = files
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

        if not self.files:
            return ""

        if not self.fields:
            self.fields = pl.scan_parquet(self.files[0]).columns[:5]

        fields = ", ".join(map(lambda s: f'"{s}"', self.fields))

        filters = " AND ".join(self.filters)
        order_by = ", ".join(
            [f"{field} {direction}" for field, direction in self.order_by]
        )

        files = "[" + ",".join(f"'{f}'" for f in self.files) + "]"

        if filters:
            filters = f"WHERE {filters}"
        if order_by:
            order_by = f"ORDER BY {order_by}"
        return f"""SELECT string_split(parse_filename(filename,true),'.')[1] AS run_name,{fields} FROM read_parquet({files},union_by_name=True,filename=True) {filters} {order_by} LIMIT {self.limit} OFFSET {self.offset}"""

    def count_query(self):
        if not self.files:
            return ""

        filters = " AND ".join(self.filters)
        files = "[" + ",".join(f"'{f}'" for f in self.files) + "]"

        if filters:
            filters = f" WHERE {filters} "
        return f"""SELECT COUNT(*) AS count_star FROM read_parquet({files},union_by_name=True,filename=True) {filters}"""

    def update(self):
        self.blockSignals(True)
        if not self.files or all([not f.exists() for f in self.files]):
            self.header = []
            self.data = []
            self.blockSignals(False)
            self.query_changed.emit()
            return
        dict_data = run_sql(self.select_query())
        if dict_data:
            self.header = list(dict_data[0].keys())
            self.data = [list(row.values()) for row in dict_data]
        else:
            self.header = []
            self.data = []
            self.row_count = 0
            self.page_count = 1
            self.set_page(1)
            self.blockSignals(False)
            self.query_changed.emit()
            return
        self.row_count = run_sql(self.count_query())[0]["count_star"]
        self.page_count = self.row_count // self.limit
        if self.row_count % self.limit > 0:
            self.page_count = self.page_count + 1
        if self.current_page > self.page_count:
            self.set_page(self.page_count)
            self.update()  # TODO: Fix edge case
        self.blockSignals(False)
        self.query_changed.emit()

    def to_dict(self):
        return {
            "fields": self.fields,
            "filters": self.filters,
            "order_by": self.order_by,
            "limit": self.limit,
            "offset": self.offset,
            "file": [str(f) for f in self.files] if self.files else [],
        }

    def from_dict(self, d: dict):
        self.fields = d.get("fields", [])
        self.filters = d.get("filters", [])
        self.order_by = d.get("order_by", [])
        self.limit = d.get("limit", 10)
        self.offset = d.get("offset", 0)
        self.files = [Path(f) for f in d.get("file", [])]
        self.update()
        return self
