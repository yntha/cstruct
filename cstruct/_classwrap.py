# --------------------------------------------------------------------------------------
#  Copyright(C) 2023 yntha                                                             -
#                                                                                      -
#  This program is free software: you can redistribute it and/or modify it under       -
#  the terms of the GNU General Public License as published by the Free Software       -
#  Foundation, either version 3 of the License, or (at your option) any later          -
#  version.                                                                            -
#                                                                                      -
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY     -
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A     -
#  PARTICULAR PURPOSE. See the GNU General Public License for more details.            -
#                                                                                      -
#  You should have received a copy of the GNU General Public License along with        -
#  this program. If not, see <http://www.gnu.org/licenses/>.                           -
# --------------------------------------------------------------------------------------
import dataclasses

from dataclasses import dataclass
from ._metadata import collect_metadata
from ._lexer import CStructLexer


class ClassWrapper:
    @classmethod
    def wrap(cls, struct_class: type, struct_format: str, byte_order: str) -> type:
        return _make_newclass(struct_class, struct_format, byte_order)


def _gen_superclass(cls: type) -> type:
    superclass_bases = []

    for base in cls.__bases__:
        if hasattr(base, "_source_class"):
            # noinspection PyProtectedMember
            superclass_bases.append(base._source_class)
        else:
            superclass_bases.append(base)

    # we must remove the old dict because it is improperly copied to
    # the new class with `type`. See
    # https://jira.mongodb.org/browse/MOTOR-460 for more information.
    cls_dict = dict(cls.__dict__)
    cls_dict.pop("__dict__", None)

    superclass = type(cls.__name__, tuple(superclass_bases), cls_dict)

    # copy over the old class annotations
    setattr(superclass, "__annotations__", cls.__annotations__)
    # noinspection PyTypeChecker
    superclass = dataclass(superclass)

    print(superclass.__dataclass_fields__)

    return superclass


def _make_newclass(src_cls: type, struct_format: str, byte_order: str) -> type:
    @dataclass
    class newclass(_gen_superclass(src_cls)):
        _source_class = src_cls
        primitive_format = struct_format
        data_byte_order = byte_order

        # noinspection PyArgumentList
        def __new__(cls, stream, offset: int = -1):
            self = super().__new__(cls)

            cls.__init__(
                self, None, **(CStructLexer.parse_struct(cls, stream, offset=offset))
            )

            return self

        def __getitem__(self, item):
            dataclass_values = [i[0] for i in dataclasses.asdict(self).values()]

            return dataclass_values[item]

        def __repr__(self):
            return repr(self.meta)

        def __str__(self):
            return str(self.meta)

        def __post_init__(self, *args, **kwargs):
            self.meta = collect_metadata(self)

            on_read_cb = src_cls.__dict__.get("on_read", None)

            if on_read_cb is not None:
                on_read_cb(self, *args)

        @property
        def length(self):
            return sum([member.size for member in self.meta])

    # back up the dataclass init function for processing below
    newclass_init = newclass.__init__

    # collect all dataclasses.InitVar fields
    initvars = []

    # noinspection PyUnresolvedReferences
    for field in newclass.__dataclass_fields__.values():
        if field.default is not dataclasses.MISSING:
            continue

        if isinstance(field.type, dataclasses.InitVar):
            initvars.append(field.name)

    # avoid parameter errors by redefining the `__init__` function
    def _init(self, stream, *args, **kwargs):
        if stream is not None:
            return

        # add all InitVar fields to the kwargs
        for initvar in initvars:
            kwargs[initvar] = None

        # noinspection PyArgumentList
        newclass_init(self, *args, **kwargs)

    newclass.__init__ = _init

    return newclass
