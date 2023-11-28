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
import enum
import typing

from dataclasses import dataclass


@dataclass(frozen=True)
class MetadataItem:
    format: str
    size: int
    orig_value: typing.Any

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        value_str = f"{self.orig_value}"

        if repr(self.orig_value.__class__).startswith("<class 'cstruct.classwrapper."):
            value_str = "\n" + str(self.orig_value)
            value_str += "\n" + "-" * max(
                map(lambda s: len(s) - 1, value_str.split("\n"))
            )

        if isinstance(self.orig_value, enum.Enum):
            value_str = repr(self.orig_value)

        return f"{self.format} ({self.size} bytes) = {value_str}"


class StructMetadata:
    def add_item(self, name: str, metadata_item: MetadataItem):
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


# noinspection PyUnresolvedReferences
def collect_metadata(class_obj: dataclass) -> StructMetadata:
    metadata = StructMetadata()

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

        if repr(field.type).startswith("<class 'cstruct.classwrapper."):
            lexer = getattr(field.type, "_lexer")

            # noinspection PyProtectedMember
            orig_name = field.type._source_class.__name__
            field_size += lexer.pad_bytes
            field_format = f"T[{orig_name}({field.type.primitive_format})]"

        if isinstance(field_value, list):
            value_list = []

            for item in field_value:
                if issubclass(field.type, enum.Enum):
                    value_list.append(field.type(item[0]))

                    continue

                value_list.append(item[0])

            setattr(class_obj, field.name, value_list)
        elif issubclass(field.type, enum.Enum):
            setattr(class_obj, field.name, field.type(field_value))
        else:
            setattr(class_obj, field.name, field_value)

        metadata.add_item(
            field.name,
            MetadataItem(field_format, field_size, getattr(class_obj, field.name)),
        )

    return metadata
