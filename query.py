#!/usr/bin/env python

from pathlib import Path
from typing import Any, List, Tuple, Union

import duckdb as db
import PySide6.QtCore as qc
from cachetools import cached


@cached(cache={})
def run_sql(query: str, conn: db.DuckDBPyConnection = None) -> Union[List[dict], None]:
    if not conn:
        return None
    res = conn.sql(query)
    if res:
        return res.pl().to_dicts()


# class FilterType(Enum):
#     AND = "AND"
#     OR = "OR"
#     LEAF = "LEAF"


# class Filter:
#     def __init__(
#         self,
#         filter_type: FilterType = FilterType.LEAF,
#         operation="",
#         parent: "Filter" = None,
#     ):
#         self.filter_type = filter_type
#         self.children: List[Filter] = []
#         self.operation = operation
#         self.parent = parent

#     def __str__(self) -> str:
#         if self.filter_type == FilterType.AND:
#             res = " AND ".join(str(c) for c in self.children)
#         elif self.filter_type == FilterType.OR:
#             res = " OR ".join(str(c) for c in self.children)
#         elif self.filter_type == FilterType.LEAF:
#             res = self.operation

#         if self.parent:
#             return f"({res})"
#         return res

#     def to_dict(self):
#         return {
#             "filter_type": self.filter_type.value,
#             "children": [c.to_dict() for c in self.children],
#             "operation": self.operation,
#         }

#     def from_dict(self, d: dict):
#         self.filter_type = FilterType(d["filter_type"])
#         self.children = [Filter().from_dict(c) for c in d["children"]]
#         self.operation = d["operation"]
#         return self

#     def add_child(self, child):
#         self.children.append(child, self)
#         return self


class Query(qc.QObject):

    # Signals for internal use only
    fields_changed = qc.Signal()
    filters_changed = qc.Signal()
    order_by_changed = qc.Signal()
    limit_changed = qc.Signal()
    offset_changed = qc.Signal()
    from_changed = qc.Signal()

    # Signals for external use
    query_changed = qc.Signal()

    def __init__(self, conn: db.DuckDBPyConnection = None) -> None:
        super().__init__()

        self.init_state()

        self.fields_changed.connect(self.update)
        self.filters_changed.connect(self.update)
        self.order_by_changed.connect(self.update)
        self.limit_changed.connect(self.update)
        self.offset_changed.connect(self.update)
        self.from_changed.connect(self.update)

        self.conn = conn

    def init_state(self):
        self.fields = []
        self.filter = ""
        self.order_by = []
        self.limit = 10
        self.offset = 0
        self.from_clause = None

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

    def get_from_clause(self) -> Path:
        return self.from_clause

    def set_from_clause(self, from_clause: str):
        self.init_state()
        self.from_clause = from_clause
        self.from_changed.emit()

        return self

    def get_filter(self) -> str:
        return self.filter

    def set_filter(self, filter: str):
        self.filter = filter
        self.filters_changed.emit()

        return self

    def get_order_by(self) -> List[Tuple[str, str]]:
        return self.order_by

    def set_order_by(self, order_by: List[Tuple[str, str]]):
        self.order_by = order_by
        self.order_by_changed.emit()

        return self

    def set_connection(self, conn: db.DuckDBPyConnection):
        self.conn = conn
        self.update()

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

    def mute(self):
        self.blockSignals(True)
        return self

    def unmute(self):
        self.blockSignals(False)
        return self

    def create_table_from_files(
        self,
        table_name: str,
        fields: List[str],
        filters: str,
        files: List[str],
        order_by: List[Tuple[str, str]],
    ):
        fields = ", ".join(fields)
        order_by = ", ".join([f"{field} {direction}" for field, direction in order_by])
        files = "[" + ",".join(f"'{f}'" for f in files) + "]"

        user_name = Path().home().name

        if filters:
            filters = f"WHERE {filters}"
        if order_by:
            order_by = f"ORDER BY {order_by}"
        run_sql(
            f"""CREATE TABLE {table_name} AS SELECT {fields} FROM read_parquet({files},union_by_name=True,filename=True) {filters} {order_by}"""
        )
        run_sql(
            f"INSERT INTO validations VALUES ({table_name}, 'pending', {user_name}, current_timestamp, uuid())"
        )

    def update_row(self, field: str, value: Any, row: str):
        if self.from_clause in self.list_tables():
            run_sql(
                f"UPDATE {self.from_clause} SET {field} = {value} WHERE uuid = {row}"
            )

    def list_tables(self):
        return [v["name"] for v in run_sql("SHOW TABLES", self.conn)]

    def select_query(self):

        if not self.from_clause:
            return ""

        if not self.fields:
            self.fields = db.sql(f"SELECT * FROM {self.from_clause} LIMIT 1").columns[
                :8
            ]

        fields = ", ".join(map(lambda s: f'"{s}"', self.fields))

        filters = self.filter
        order_by = ", ".join(
            [f"{field} {direction}" for field, direction in self.order_by]
        )

        if filters:
            filters = f"WHERE {filters}"
        if order_by:
            order_by = f"ORDER BY {order_by}"
        return f"""SELECT string_split(parse_filename(filename,true),'.')[1] AS run_name,{fields} FROM {self.from_clause} {filters} {order_by} LIMIT {self.limit} OFFSET {self.offset}"""

    def count_query(self):
        if not self.from_clause:
            return ""

        filters = self.filter

        if filters:
            filters = f" WHERE {filters} "
        return f"""SELECT COUNT(*) AS count_star FROM {self.from_clause} {filters}"""

    def update(self):
        self.blockSignals(True)
        if not self.from_clause or all([not f.exists() for f in self.from_clause]):
            self.header = []
            self.data = []
            self.blockSignals(False)
            self.query_changed.emit()
            return
        dict_data = run_sql(self.select_query(), self.conn)
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
        self.row_count = run_sql(self.count_query(), self.conn)[0]["count_star"]
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
            "filters": self.filter,
            "order_by": self.order_by,
            "limit": self.limit,
            "offset": self.offset,
            "from_clause": self.from_clause,
        }

    def from_dict(self, d: dict):
        self.fields = d.get("fields", [])
        self.filter = d.get("filters", [])
        self.order_by = d.get("order_by", [])
        self.limit = d.get("limit", 10)
        self.offset = d.get("offset", 0)
        self.from_clause = d.get("from_clause", None)
        self.update()
        return self
