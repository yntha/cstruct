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

from dataclasses import dataclass


class InvalidFormat(Exception):
    pass


def _read_cstruct(cls, stream, offset: int = -1):
    return _CStructLexer.parse_struct(cls, stream, offset)

def cstruct(data_format: str, byte_order: str = "little"):
    def decorate(cls):
        format = data_format
        base_class = cls.__base__

        if base_class is not object and hasattr(base_class, "primitive_format"):
            format = base_class.primitive_format + data_format

        setattr(cls, "primitive_format", format)
        setattr(cls, "data_byte_order", byte_order)
        setattr(cls, "read", classmethod(_read_cstruct))

        return dataclass(cls)

    return decorate


class _CStructLexer:
    def __init__(self, data_format: str, data_byte_order: str, stream):
        self.data_format = data_format
        self.byte_order = "<" if data_byte_order == "little" else ">"
        self.stream = stream

        self.paren_open = False
        self.digit_buffer = ""
        self.format = ""
        self.values = []

        self.parse()

    def _expand(self, count: int, format_ch: str):
        expanded = ""
        size = struct.calcsize(format_ch)

        for _ in range(count):
            self.values.append(
                struct.unpack(self.byte_order + format_ch, self.stream.read(size))[0]
            )

            expanded += format_ch

        return expanded

    def parse(self):
        skip_flag = False

        for index, char in enumerate(self.data_format):
            if skip_flag:
                skip_flag = False

                continue

            if char == "(":
                self.paren_open = True

                continue
            elif char == ")":
                if len(self.digit_buffer) == 0:
                    raise InvalidFormat(
                        "An index number was expected within the parentheses."
                    )

                index_num = int(self.digit_buffer)

                try:
                    refd_value = self.values[index_num]
                except IndexError:
                    raise InvalidFormat("Index was out of range.")

                if not isinstance(refd_value, int):
                    raise InvalidFormat(
                        f"The repeat count at {index_num} must be an integer!"
                    )

                if refd_value == 0:
                    self.values.append(None)
                    self.digit_buffer = ""

                    skip_flag = True
                    self.paren_open = False

                    continue

                self.format += self._expand(refd_value, self.data_format[index + 1])
                self.digit_buffer = ""

                skip_flag = True
                self.paren_open = False

                continue

            if char.isdigit():
                self.digit_buffer += char

                continue
            elif self.digit_buffer != "":
                format_ch = self.data_format[index]
                number = int(self.digit_buffer)

                if format_ch == "s":
                    self.values.append(self.stream.read(number))
                    self.digit_buffer = ""

                    continue

                self.format += self._expand(number, format_ch)
                self.digit_buffer = ""

                continue

            self.values.append(
                struct.unpack(
                    self.byte_order + char, self.stream.read(struct.calcsize(char))
                )[0]
            )
            self.format += char

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
            return struct_class(*values)
        except TypeError:
            raise InvalidFormat("The data format does not match the struct.")