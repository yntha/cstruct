# cstruct
Read primitive data from a binary stream using a C-like struct format.

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
y = test.read(x)

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
```python
import cstruct


# 4s   - next 4 bytes as a byte string
# I    - next unsigned int
# (1)b - next x number of signed byte values, where x is the repeat count specified
#        by the 2nd(0-indexed) value. if the repeat count is 0, then this will be
#        None, else it will be a list of signed byte values.
# 8s   - next x(1) number of bytes as a byte string
# I    - next unsigned int
# I    - next unsigned int
# i    - next signed int
# i    - next signed int
@cstruct("4sI(1)b(1)sIIii", "little")
class x:
    a: bytes
    b: int
    z: list
    c: bytes
    d: int
    e: int
    f: int
    g: int


import io

s = io.BytesIO(
    bytes.fromhex(
        "28 46 1c e8    08 00 00 00   c2 cc ee ff aa bb cc 11   9f7e683cdd20189e  c1 54 92 4a 44 ab 25 be 05 46 eb ff 2c d8 c4 c5"
    )
)
parsed = x.read(s)
print(parsed.__dict__)
# output:
# {'a': b'(F\x1c\xe8', 'b': 8, 'z': [-62, -52, -18, -1, -86, -69, -52, 17], 'c': b'\x9f~h<\xdd \x18\x9e', 'd': 1251103937, 'e': 3190139716, 'f': -1358331, 'g': -976955348}

# you can see the size and the string format of the fields, too:
print(parsed.meta.c.size)  # 8
print(parsed.meta.["c"].format)  # 's'
print(parsed.meta[0])  # 'I (4 bytes)'

# cstruct classes are also sequences:
print(parsed[0])  # b'(F\x1c\xe8'
```

For all the standard struct format characters, see https://docs.python.org/3/library/struct.html?highlight=struct#format-characters.

### To-Do List
* Make cstruct classes immutable
* Eventually make them mutable with the introduction of the cstruct serializer(python dataclass -> binary data)
