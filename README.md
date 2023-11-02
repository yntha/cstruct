# cstruct
Read primitive data from a binary stream using a C-like struct format.

# Installing
```
 python -m pip install -U git+https://github.com/yntha/cstruct.git
```

### Example Usage
```py
# 4s   - next 4 bytes as a byte string
# I    - next unsigned int
# (1)b - next x number of signed byte values, where x is the repeat count specified
#        by the 2nd(0-indexed) value. if the repeat count is 0, then this will be
#        None.
# 8s   - next 8 bytes as a byte string
# I    - next unsigned int
# I    - next unsigned int
# i    - next signed int
# i    - next signed int
@cstruct("4sI(1)b8sIIii", "little")
class x:
    a: bytes
    b: int
    z: int
    c: bytes
    d: int
    e: int
    f: int
    g: int


import io

s = io.BytesIO(
    bytes.fromhex(
        "28 46 1c e8    01 00 00 00  c2    9f 7e 68 3c dd 20 18 9e c1 54 92 4a 44 ab 25 be 05 46 eb ff 2c d8 c4 c5"
    )
)
parsed = x.read(s)
print(parsed.__dict__)
# output:
# {'a': b'(F\x1c\xe8', 'b': 1, 'z': -67 , 'c': b'\x9f~h<\xdd \x18\x9e', 'd': 1251103937, 'e': 3190139716, 'f': -1358331, 'g': -976955348}
```

For all the standard struct format characters, see https://docs.python.org/3/library/struct.html?highlight=struct#format-characters.
