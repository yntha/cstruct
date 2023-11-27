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
import dataclasses

from ._exc import InvalidFormat

# check if pyleb128 is installed to add support for the LEB128 format
try:
    import pyleb128

    # noinspection PyUnresolvedReferences
    from pyleb128 import uleb128, sleb128, leb128

    has_leb128 = True
except ImportError:
    has_leb128 = False


ULEB128_FORMAT_CH = "U"
ULEB128P1_FORMAT_CH = chr(ord(ULEB128_FORMAT_CH) + 1)
SLEB128_FORMAT_CH = "S"

TYPEDEF_FORMAT_CH = "T"


class CStructLexer:
    class _Token:
        def __init__(self, repeat_count: int, format_ch: str, is_vararr: bool = False):
            self.repeat_count = repeat_count
            self.format_ch = format_ch
            self.vararr = is_vararr

            self.struct_format = f"{self.repeat_count}{self.format_ch}"

        def is_leb128(self) -> bool:
            if not has_leb128:
                raise InvalidFormat(
                    "The LEB128 format is not supported. "
                    "Please install the pyleb128 package to add support for it."
                )

            return self.format_ch in (
                ULEB128_FORMAT_CH,
                ULEB128P1_FORMAT_CH,
                SLEB128_FORMAT_CH,
            )

        def is_typedef(self) -> bool:
            return self.format_ch == TYPEDEF_FORMAT_CH

    def __init__(
        self, struct_class: type, data_format: str, data_byte_order: str, stream
    ):
        self.data_format = data_format
        self.byte_order = "<" if data_byte_order == "little" else ">"
        self.stream = stream
        self.struct_class = struct_class

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
                    format_ch = token.format_ch

                    if token.is_leb128():
                        leb_data = self._read_leb128(token)

                        value = leb_data[0]
                        item_size = leb_data[2]
                        format_ch = leb_data[1]
                    elif token.is_typedef() and self.check_typedef():
                        typedef = self.get_typdef_type()
                        typedef_initialized = typedef(self.stream)

                        value = typedef_initialized

                        # noinspection PyUnresolvedReferences
                        format_ch = typedef.primitive_format
                        item_size = typedef_initialized.length
                    else:
                        item_size = struct.calcsize(format_ch)
                        value = struct.unpack(
                            self.byte_order + format_ch,
                            self.stream.read(item_size),
                        )[0]

                    sum_size += item_size

                    vararr_values.append(
                        [
                            value,
                            format_ch,
                            item_size,
                        ]
                    )

                self.values.append([vararr_values, token.struct_format, sum_size])

                continue

            if token.is_typedef():
                if not self.check_typedef():
                    raise InvalidFormat("Invalid type specified for the typedef.")

                typedef = self.get_typdef_type()
                typedef_initialized = typedef(self.stream)

                # noinspection PyUnresolvedReferences
                self.values.append(
                    [
                        typedef_initialized,
                        typedef.primitive_format,
                        typedef_initialized.length,
                    ]
                )

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

    def check_typedef(self):
        typedef_type = self.get_typdef_type()

        return repr(typedef_type).startswith("<class 'cstruct.classwrapper.")

    # noinspection PyDataclass
    def get_typdef_type(self) -> type:
        return dataclasses.fields(self.struct_class)[self.pos - 1].type

    @classmethod
    def parse_struct(cls, struct_class, stream, offset: int = -1):
        stream_pos = stream.tell()

        if offset > -1:
            stream.seek(offset, 0)  # SEEK_SET

        values = cls(
            struct_class,
            struct_class.primitive_format,
            struct_class.data_byte_order,
            stream,
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
