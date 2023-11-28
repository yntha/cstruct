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

import cstruct
import enum


class ELF_CLASS(enum.IntEnum):
    ELFCLASSNONE = 0
    ELFCLASS32 = 1
    ELFCLASS64 = 2

    @classmethod
    def _missing_(cls, value):
        return cls.ELFCLASSNONE


class ELF_DATA(enum.IntEnum):
    ELFDATANONE = 0
    ELFDATA2LSB = 1
    ELFDATA2MSB = 2

    @classmethod
    def _missing_(cls, value):
        return cls.ELFDATANONE


class ELF_OSABI(enum.IntEnum):
    ELFOSABI_NONE = 0
    ELFOSABI_SYSV = 0
    ELFOSABI_HPUX = 1
    ELFOSABI_NETBSD = 2
    ELFOSABI_LINUX = 3
    ELFOSABI_SOLARIS = 6
    ELFOSABI_AIX = 7
    ELFOSABI_IRIX = 8
    ELFOSABI_FREEBSD = 9
    ELFOSABI_TRU64 = 10
    ELFOSABI_MODESTO = 11
    ELFOSABI_OPENBSD = 12
    ELFOSABI_ARM_AEABI = 64
    ELFOSABI_ARM = 97
    ELFOSABI_STANDALONE = 255

    @classmethod
    def _missing_(cls, value):
        return cls.ELFOSABI_NONE


class ELF_TYPE(enum.IntEnum):
    ET_NONE = 0
    ET_REL = 1
    ET_EXEC = 2
    ET_DYN = 3
    ET_CORE = 4
    ET_LOOS = 0xFE00
    ET_HIOS = 0xFEFF
    ET_LOPROC = 0xFF00
    ET_HIPROC = 0xFFFF

    @classmethod
    def _missing_(cls, value):
        return cls.ET_NONE


class ELF_MACHINE(enum.IntEnum):
    EM_NONE = 0
    EM_M32 = 1
    EM_SPARC = 2
    EM_386 = 3
    EM_68K = 4
    EM_88K = 5
    EM_860 = 7
    EM_MIPS = 8
    EM_S370 = 9
    EM_MIPS_RS3_LE = 10
    EM_PARISC = 15
    EM_VPP500 = 17
    EM_SPARC32PLUS = 18
    EM_960 = 19
    EM_PPC = 20
    EM_PPC64 = 21
    EM_S390 = 22
    EM_V800 = 36
    EM_FR20 = 37
    EM_RH32 = 38
    EM_RCE = 39
    EM_ARM = 40
    EM_FAKE_ALPHA = 41
    EM_SH = 42
    EM_SPARCV9 = 43
    EM_TRICORE = 44
    EM_ARC = 45
    EM_H8_300 = 46
    EM_H8_300H = 47
    EM_H8S = 48
    EM_H8_500 = 49
    EM_IA_64 = 50
    EM_MIPS_X = 51
    EM_COLDFIRE = 52
    EM_68HC12 = 53
    EM_MMA = 54
    EM_PCP = 55
    EM_NCPU = 56
    EM_NDR1 = 57
    EM_STARCORE = 58
    EM_ME16 = 59
    EM_ST100 = 60
    EM_TINYJ = 61
    EM_X86_64 = 62
    EM_PDSP = 63
    EM_PDP10 = 64
    EM_PDP11 = 65
    EM_FX66 = 66
    EM_ST9PLUS = 67
    EM_ST7 = 68
    EM_68HC16 = 69
    EM_68HC11 = 70
    EM_68HC08 = 71
    EM_68HC05 = 72
    EM_SVX = 73
    EM_ST19 = 74
    EM_VAX = 75
    EM_CRIS = 76
    EM_JAVELIN = 77
    EM_FIREPATH = 78
    EM_ZSP = 79
    EM_MMIX = 80
    EM_HUANY = 81
    EM_PRISM = 82
    EM_AVR = 83
    EM_FR30 = 84
    EM_D10V = 85
    EM_D30V = 86
    EM_V850 = 87
    EM_M32R = 88
    EM_MN10300 = 89
    EM_MN10200 = 90
    EM_PJ = 91
    EM_OPENRISC = 92
    EM_ARC_A5 = 93
    EM_XTENSA = 94
    EM_VIDEOCORE = 95
    EM_TMM_GPP = 96
    EM_NS32K = 97
    EM_TPC = 98
    EM_SNP1K = 99
    EM_ST200 = 100

    @classmethod
    def _missing_(cls, value):
        return cls.EM_NONE


class ELF_VERSION(enum.IntEnum):
    EV_NONE = 0
    EV_CURRENT = 1

    @classmethod
    def _missing_(cls, value):
        return cls.EV_NONE


@cstruct("4s5B7x")
class ELF_IDENT:
    magic: bytes
    class_: ELF_CLASS
    data: ELF_DATA
    version: ELF_VERSION
    osabi: ELF_OSABI
    abiversion: int


@cstruct("THHI3QI6H")
class ELFHeader:
    ident: ELF_IDENT
    type: ELF_TYPE
    machine: ELF_MACHINE
    version: ELF_VERSION
    entry: int
    phoff: int
    shoff: int
    flags: int
    ehsize: int
    phentsize: int
    phnum: int
    shentsize: int
    shnum: int
    shstrndx: int

    def on_read(self):
        assert self.ident.magic == b"\x7fELF"
        assert self.ident.version == ELF_VERSION.EV_CURRENT


with open("test.elf", "rb") as f:
    elf_header = ELFHeader(f)

    print(elf_header)
