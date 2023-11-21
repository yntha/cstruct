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


import struct
import sys
import dataclasses
import enum
import io
import typing

from dataclasses import dataclass


# check if pyleb128 is installed to add support for the LEB128 format
try:
    import pyleb128

    from pyleb128 import uleb128, sleb128, leb128
except ImportError:
    pass

ULEB128_FORMAT_CH = "U"
ULEB128P1_FORMAT_CH = chr(ord(ULEB128_FORMAT_CH) + 1)
SLEB128_FORMAT_CH = "S"


def _has_leb128():
    return "pyleb128" in sys.modules


class InvalidFormat(Exception):
    pass


@dataclass(frozen=True)
class _MetadataItem:
    format: str
    size: int

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return f"{self.format} ({self.size} bytes)"


class _StructMetadata:
    def add_item(self, name: str, metadata_item: _MetadataItem):
        setattr(self, name, metadata_item)

    def __getitem__(self, item):
        return (
            getattr(self, item)
            if isinstance(item, str)
            else [*self.__dict__.values()][item]
        )

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return "\n".join([f"{key}: {value}" for key, value in self.__dict__.items()])


def _collect_metadata(class_obj: dataclass) -> _StructMetadata:
    metadata = _StructMetadata()

    for field in dataclasses.fields(class_obj):
        # the parameters passed to the dataclass constructor individually
        # contain supplementary information about the field such as its
        # format and size.
        field_object = getattr(class_obj, field.name)

        if field_object is None:
            continue

        field_value = field_object[0]
        field_format = field_object[1]
        field_size = field_object[2]

        metadata.add_item(field.name, _MetadataItem(field_format, field_size))

        if isinstance(field_value, list):
            value_list = []

            for item in field_value:
                value_list.append(item[0])

            setattr(class_obj, field.name, value_list)
        elif issubclass(field.type, enum.Enum):
            setattr(class_obj, field.name, field.type(field_value))
        else:
            setattr(class_obj, field.name, field_value)

    return metadata


def _read_cstruct(cls, stream, offset: int = -1):
    return _CStructLexer.parse_struct(cls, stream, offset)


def cstruct(data_format: str, byte_order: str = "little"):
    def decorate(cls):
        struct_format = data_format
        base_class = cls.__base__

        if base_class is not object and hasattr(base_class, "primitive_format"):
            struct_format = base_class.primitive_format + data_format

        old_class = cls
        newclass_bases = []

        for base in old_class.__bases__:
            if hasattr(base, "source_class"):
                newclass_bases.append(base.source_class)
            else:
                newclass_bases.append(base)

        cls_dict = dict(cls.__dict__)
        cls_dict.pop("__dict__", None)

        old_class = type(cls.__name__, tuple(newclass_bases), cls_dict)
        setattr(old_class, "__annotations__", cls.__annotations__)
        old_class = dataclass(old_class)

        class newclass(old_class):
            source_class = old_class
            primitive_format = struct_format
            data_byte_order = byte_order

            def __post_init__(self):
                dataclass_values = [i[0] for i in dataclasses.asdict(self).values()]

                setattr(self, "meta", _collect_metadata(self))

                # this probably isn't the most elegant way to do this
                setattr(
                    self.__class__,
                    "__getitem__",
                    lambda zelf, item: dataclass_values[item],
                )
                setattr(self.__class__, "__repr__", lambda zelf: repr(self.meta))
                setattr(self.__class__, "__str__", lambda zelf: str(self.meta))

            def __new__(_cls, stream, offset: int = -1):
                self = super().__new__(_cls)

                _cls.__init__(
                    self, None, **(_read_cstruct(_cls, stream, offset=offset))
                )

                return self

        newclass = dataclass(newclass)
        newclass_init = newclass.__init__

        def _init(self, stream, *args, **kwargs):
            if stream is not None:
                return

            newclass_init(self, *args, **kwargs)

        newclass.__init__ = _init

        return newclass

    return decorate


class _CStructLexer:
    class _Token:
        def __init__(self, repeat_count: int, format_ch: str, is_vararr: bool = False):
            self.repeat_count = repeat_count
            self.format_ch = format_ch
            self.vararr = is_vararr

            self.struct_format = f"{self.repeat_count}{self.format_ch}"

        def is_leb128(self) -> bool:
            if not _has_leb128():
                raise InvalidFormat(
                    "The LEB128 format is not supported. "
                    "Please install the pyleb128 package to add support for it."
                )

            return self.format_ch in (
                ULEB128_FORMAT_CH,
                ULEB128P1_FORMAT_CH,
                SLEB128_FORMAT_CH,
            )

    def __init__(self, data_format: str, data_byte_order: str, stream):
        self.data_format = data_format
        self.byte_order = "<" if data_byte_order == "little" else ">"
        self.stream = stream

        self.pos = 0
        self.values = []

        self.parse()

    def parse(self):
        while self._has_tokens():
            token = self._next_token()

            if token.vararr:
                if token.repeat_count == 0:
                    self.values.append([None, token.format_ch, 0])

                    continue

                vararr_values = []
                sum_size = 0

                for _ in range(token.repeat_count):
                    if token.is_leb128():
                        leb_data = self._read_leb128(token)

                        value = leb_data[0]
                        item_size = leb_data[2]
                    else:
                        item_size = struct.calcsize(token.format_ch)
                        value = struct.unpack(
                            self.byte_order + token.format_ch,
                            self.stream.read(item_size),
                        )[0]

                    sum_size += item_size

                    vararr_values.append(
                        [
                            value,
                            token.format_ch,
                            item_size,
                        ]
                    )

                self.values.append([vararr_values, token.struct_format, sum_size])

                continue

            if token.is_leb128():
                self.values.append(self._read_leb128(token))

                continue

            self.values.append(
                [
                    struct.unpack(
                        self.byte_order + token.struct_format,
                        self.stream.read(struct.calcsize(token.struct_format)),
                    )[0],
                    token.format_ch,
                    struct.calcsize(token.struct_format),
                ]
            )

    @classmethod
    def parse_struct(cls, struct_class, stream, offset: int = -1):
        stream_pos = stream.tell()

        if offset > -1:
            stream.seek(offset, 0)  # SEEK_SET

        values = cls(
            struct_class.primitive_format, struct_class.data_byte_order, stream
        ).values

        stream.seek(stream_pos, 0)  # SEEK_SET

        try:
            dataclass_fields = [f.name for f in dataclasses.fields(struct_class)]

            return dict(zip(dataclass_fields, values))
        except TypeError:
            raise InvalidFormat("The data format does not match the struct.")

    def _next_literal(self) -> str:
        literal = self.data_format[self.pos]
        self.pos += 1

        return literal

    def _has_tokens(self) -> bool:
        return self.pos < len(self.data_format)

    def _next_token(self) -> _Token:
        token = self._next_literal()

        if token == "(":
            if self.pos == 1:
                raise InvalidFormat(
                    "The data format must start with a struct format character. "
                    "See https://docs.python.org/3/library/struct.html?highlight=struct#format-characters"
                    " for more information."
                )

            digit_buffer = ""

            while (token := self._next_literal()) != ")":
                digit_buffer += token

            vararr_format = self._next_literal()

            data_index = int(digit_buffer)
            data_value = self.values[data_index][0]

            if vararr_format == "s":
                # return as a non-variable array
                return self._Token(data_value, vararr_format)

            return self._Token(data_value, vararr_format, True)

        if token.isdigit():
            digit_buffer = token

            while (token := self._next_literal()).isdigit():
                digit_buffer += token

            # the last read literal is the format character
            return self._Token(int(digit_buffer), token)

        return self._Token(1, token)

    def _read_leb128(self, token: _Token) -> list[leb128, str, int]:
        if token.format_ch == ULEB128_FORMAT_CH:
            leb_size = uleb128.peek_size(self.stream)

            if leb_size == 0:
                return [uleb128(0), ULEB128_FORMAT_CH, 0]

            return [uleb128.decode_stream(self.stream), token.format_ch, leb_size]
        elif token.format_ch == ULEB128P1_FORMAT_CH:
            leb_size = uleb128.peek_size(self.stream)

            if leb_size == 0:
                return [uleb128(0, p1=True), ULEB128P1_FORMAT_CH, 0]

            return [
                uleb128.decode_stream(self.stream, p1=True),
                token.format_ch,
                leb_size,
            ]
        elif token.format_ch == SLEB128_FORMAT_CH:
            leb_size = sleb128.peek_size(self.stream)

            if leb_size == 0:
                return [sleb128(0), SLEB128_FORMAT_CH, 0]

            return [sleb128.decode_stream(self.stream), token.format_ch, leb_size]


class _callable_cstruct(sys.modules[__name__].__class__):
    def __call__(self, *args, **kwargs):
        return cstruct(*args, **kwargs)


sys.modules[__name__].__class__ = _callable_cstruct
