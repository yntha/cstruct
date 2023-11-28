# cstruct
Read primitive data into a dataclass using struct format strings.

### Note
LEB128 is supported by cstruct, but you must install my [pyleb128](https://github.com/yntha/pyleb128) package to enable support:
```python
import cstruct


@cstruct("II(0)c(0)U")
class test:
    a: int
    b: int
    c: list
    d: list


x = io.BytesIO(bytes.fromhex("02000000 00000000 01 00 ffff03 feff03"))
y = test(x)

print(y.d[0].encoded)  # b'\xff\xff\x03'
print(y.d[0].size)  # 3
print(y.__dict__)
# output:
# {'a': 2, 'b': 0, 'c': [b'\x01', b'\x00'], 'd': [65535, 65534]}
```
To use leb128 in a cstruct class, add one of the following keys to the format string:
* `U` - unsigned leb128
* `S` - signed leb128
* `V` - unsigned leb128 + 1

You must also specify the field type as either `leb128`(generic), `uleb128`(unsigned), or `sleb128`(signed), unless you use a container type of course.

### Installing
```
 python -m pip install -U git+https://github.com/yntha/cstruct.git
```

### Example Usage
For all the standard struct format characters, see https://docs.python.org/3/library/struct.html?highlight=struct#format-characters.

#### Basic Usage
```python
import cstruct
import io

# can also be imported as `from cstruct import cstruct` to avoid analyzer issues.

@cstruct("IIb")
class EXClass:
    a: int
    b: int
    c: int

datastream = io.BytesIO(bytes.fromhex("01000000 02000000 03"))
parsed = EXClass(datastream)

print(parsed.a)  # 1
print(parsed.b)  # 2
print(parsed.c)  # 3

print(parsed[0])  # 1
print(parsed[1])  # 2
print(parsed[2])  # 3

print(parsed.meta[0])  # 'I (4 bytes)'
print(parsed.meta[1])  # 'I (4 bytes)'
print(parsed.meta[2])  # 'b (1 byte)'

print(parsed.meta.a.size)  # 4
print(parsed.meta.b.format)  # 'I'

print(parsed.length)  # 9
```

#### Using Variable Length Fields
```python
from cstruct import cstruct
import io

@cstruct("II(0)b")
class EXClass:
    a: int
    b: int
    c: list

datastream = io.BytesIO(bytes.fromhex("03000000 02000000 03 04 05"))
parsed = EXClass(datastream)

print(parsed.a)  # 3
print(parsed.b)  # 2
print(parsed.c)  # [3, 4, 5]
```
Variable length fields have the following syntax: `(index)type`. Index refers to the index of the member that specifies the length of the variable length field. If length is 0, then the field will be None. If length is greater than 0, then the field will be a list of the specified type.

***Note:*** *If the type of the vararr is 's', then the result will be a byte string, not a list.*

#### Enums As Fields
Enums are supported as fields, and the value of the field will result in a member of the enum:
```python
import cstruct
import enum
import io

class ExEnum(enum.IntEnum):
    a = 1
    b = 2
    c = 3

@cstruct("IH(1)b")
class EXClass:
    a: int
    b: int
    c: ExEnum

datastream = io.BytesIO(bytes.fromhex("01000000 0300 03 01 02"))
parsed = EXClass(datastream)

print(parsed.a)  # 1
print(parsed.b)  # 2
print(parsed.c)  # [<ExEnum.c: 3>, <ExEnum.a: 1>, <ExEnum.b: 2>]
```

#### Post Processing
You can define an `on_read` function to do post processing on the data after it has been read:
```python
import cstruct
import io
import dataclasses

@cstruct("I8s")
class EXClass:
    a: int
    b: bytes
    c dataclasses.InitVar[int]

    def on_read(self, c: int):
        print("b is", self.b)
        
        self.c = b[0]

datastream = io.BytesIO(bytes.fromhex("01000000 0102030405060708"))
parsed = EXClass(datastream)

print(parsed.a)  # 1
print(parsed.b)  # b'\x01\x02\x03\x04\x05\x06\x07\x08'
print(parsed.c)  # 1
```

#### Inheritance
You can extend cstruct classes through inheritance:
```python
import cstruct
import io

@cstruct("I")
class EXClass:
    a: int

@cstruct("B")
class EXClass2(EXClass):
    b: int

datastream = io.BytesIO(bytes.fromhex("01000000 02"))
parsed = EXClass2(datastream)

print(parsed.a)  # 1
print(parsed.b)  # 2

print(parsed.length)  # 5
```
Note that the `on_read` function isn't inherited between classes.

#### Using CStruct Classes As Fields
You can use cstruct classes as fields in other cstruct classes:
```python
import cstruct
import io

@cstruct("I")
class EXClass:
    a: int

@cstruct("B")
class EXClass2:
    b: int

@cstruct("TT")
class EXClass3:
    c: EXClass
    d: EXClass2

datastream = io.BytesIO(bytes.fromhex("01000000 02"))
parsed = EXClass3(datastream)

print(parsed.c.a)  # 1
print(parsed.d.b)  # 2

print(parsed.meta.c)  # T[EXClass(I)] (4 bytes)
```

### Real World Example
Parsing an ELF File header:
See [elf_header.py](examples/elf_header.py).

### To-Do List
* Make cstruct classes immutable
* Eventually make them mutable with the introduction of the cstruct serializer(python dataclass -> binary data)
* Add support for bit fields 
* ~~Rewrite this readme to include clear examples and real world scenarios.~~
