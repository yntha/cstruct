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
import sys

from ._classwrap import ClassWrapper


def cstruct(data_format: str, byte_order: str = "little"):
    def decorate(cls):
        struct_format = data_format
        base_class = cls.__base__

        if base_class is not object and hasattr(base_class, "primitive_format"):
            struct_format = base_class.primitive_format + data_format

        return ClassWrapper.wrap(cls, struct_format, byte_order)

    return decorate


class _callable_cstruct(sys.modules[__name__].__class__):
    def __call__(self, *args, **kwargs):
        return cstruct(*args, **kwargs)


sys.modules[__name__].__class__ = _callable_cstruct
