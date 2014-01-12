from datetime import timedelta
from collections import OrderedDict


class ASSColor(object):
    """ Represents a color in the ASS format.
    """
    def __init__(self, r, g, b, a=0):
        """ Made up of red, green, blue and alpha components (in that order!).
        """
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def to_ass(self):
        """ Convert this color to a Visual Basic (ASS) color code.
        """
        return "&H{a:02X}{b:02X}{g:02X}{r:02X}".format(**self.__dict__)

    @classmethod
    def from_ass(cls, v):
        """ Convert a Visual Basic (ASS) color code into an ``ASSColor``.
        """
        if not v.startswith("&H"):
            raise ValueError("color must start with &H")

        rest = int(v[2:], 16)

        # AABBGGRR
        r = rest & 0xFF
        rest >>= 8

        g = rest & 0xFF
        rest >>= 8

        b = rest & 0xFF
        rest >>= 8

        a = rest & 0xFF

        return cls(r, g, b, a)

    def __repr__(self):
        return "{name}(0x{r:02x}, 0x{g:02x}, 0x{b:02x}, 0x{a:02x})".format(
            name=self.__class__.__name__,
            r=self.r,
            g=self.g,
            b=self.b,
            a=self.a
        )

ASSColor.WHITE = ASSColor(255, 255, 255)
ASSColor.RED = ASSColor(255, 0, 0)
ASSColor.BLACK = ASSColor(0, 0, 0)


class ASSFile(object):
    SCRIPT_INFO_HEADER = "[Script Info]"
    STYLE_SSA_HEADER = "[V4 Styles]"
    STYLE_ASS_HEADER = "[V4+ Styles]"
    EVENTS_HEADER = "[Events]"

    FORMAT_TYPE = "Format"

    def __init__(self):
        """ Create an empty ASS file.
        """
        self.script_info = OrderedDict()

        self.styles = []
        self.styles_field_order = Style.DEFAULT_FIELD_ORDER

        self.events = []
        self.events_field_order = _Event.DEFAULT_FIELD_ORDER

    @classmethod
    def parse_file(cls, f):
        """ Parse an ASS file from a file object.
        """
        af = cls()

        lines = ((i, line)
                 for i, line in ((i, line.rstrip("\r\n"))
                                 for i, line in enumerate(f))
                 if line and line[0] != ";")

        # [Script Info]
        for i, line in lines:
            if i == 0 and line[:3] == "\xef\xbb\xbf":
                line = line[3:]

            if line.lower() == ASSFile.SCRIPT_INFO_HEADER.lower():
                break

            raise ValueError("expected script info header")

        # k: v
        for i, line in lines:
            if line.lower() == ASSFile.STYLE_ASS_HEADER.lower() or \
               line.lower() == ASSFile.STYLE_SSA_HEADER.lower():
               break

            k, v = line.split(":", 1)
            v = v.lstrip()

            af.script_info[k] = v

        # [V4 Styles]
        i, line = next(lines)

        type_name, line = line.split(":", 1)
        line = line.lstrip()

        # Format: ...
        if type_name.lower() != ASSFile.FORMAT_TYPE.lower():
            raise ValueError("expected format line in styles")

        field_order = [x.strip() for x in line.split(",")]
        af.styles_field_order = field_order

        # Style: ...
        for i, line in lines:
            if line.lower() == ASSFile.EVENTS_HEADER.lower():
                break

            type_name, line = line.split(":", 1)
            line = line.lstrip()

            if type_name.lower() != Style.TYPE.lower():
                raise ValueError("expected style line in styles")

            af.styles.append(Style.parse(line, field_order))

        # [Events]
        i, line = next(lines)

        type_name, line = line.split(":", 1)
        line = line.lstrip()

        # Format: ...
        if type_name.lower() != ASSFile.FORMAT_TYPE.lower():
            raise ValueError("expected format line in events")

        field_order = [x.strip() for x in line.split(",")]
        af.events_field_order = field_order

        # Dialogue: ...
        # Comment: ...
        # etc.
        for i, line in lines:
            type_name, line = line.split(":", 1)
            line = line.lstrip()

            af.events.append(({
                "Dialogue": Dialogue,
                "Comment":  Comment,
                "Picture":  Picture,
                "Sound":    Sound,
                "Movie":    Movie,
                "Command":  Command
            })[type_name].parse(line, field_order))

        return af

    def dump_file(self, f):
        """ Dump this ASS file to a file object.
        """
        f.write(ASSFile.SCRIPT_INFO_HEADER + "\n")
        for k, v in self.script_info.items():
            f.write(k + ": " + v + "\n")
        f.write("\n")

        f.write(ASSFile.STYLE_ASS_HEADER + "\n")
        f.write(ASSFile.FORMAT_TYPE +  ": " +
                ", ".join(self.styles_field_order) + "\n")
        for style in self.styles:
            f.write(style.dump_with_type(self.styles_field_order) + "\n")
        f.write("\n")

        f.write(ASSFile.EVENTS_HEADER + "\n")
        f.write(ASSFile.FORMAT_TYPE +  ": " +
                ", ".join(self.events_field_order) + "\n")
        for event in self.events:
            f.write(event.dump_with_type(self.events_field_order) + "\n")
        f.write("\n")


class _Field(object):
    _last_creation_order = -1

    def __init__(self, name, type, default=None):
        self.name = name
        self.type = type
        self.default = default

        _Field._last_creation_order += 1
        self._creation_order = self._last_creation_order

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        try:
            return obj.fields[self.name]
        except KeyError:
            return None

    def __set__(self, obj, v):
        obj.fields[self.name] = v

    @staticmethod
    def dump(v):
        if v is None:
            return ""

        if isinstance(v, bool):
            return str(-int(v))

        if isinstance(v, timedelta):
            return _Field.timedelta_to_ass(v)

        if isinstance(v, float):
            return "{0:g}".format(v)

        if hasattr(v, "to_ass"):
            return v.to_ass()

        return str(v)

    def parse(self, v):
        if self.type is None:
            return None

        if self.type is bool:
            return bool(-int(v))

        if self.type is timedelta:
            return _Field.timedelta_from_ass(v)

        if hasattr(self.type, "from_ass"):
            return self.type.from_ass(v)

        return self.type(v)

    @staticmethod
    def timedelta_to_ass(td):
        r = int(td.total_seconds())

        r, secs = divmod(r, 60)
        hours, mins = divmod(r, 60)

        return "{hours:.0f}:{mins:02.0f}:{secs:02.0f}.{csecs:02}".format(
            hours=hours,
            mins=mins,
            secs=secs,
            csecs=td.microseconds // 10000
        )

    @staticmethod
    def timedelta_from_ass(v):
        hours, mins, secs = v.split(":", 2)
        secs, csecs = secs.split(".", 2)

        r = int(hours) * 60 * 60 + int(mins) * 60 + int(secs) + \
            int(csecs) * 1e-2

        return timedelta(seconds=r)


class _ASSLineMeta(type):
    def __new__(cls, name, bases, dct):
        newcls = type.__new__(cls, name, bases, dct)

        field_defs = []
        for base in bases:
            if hasattr(base, "_field_defs"):
                field_defs.extend(base._field_defs)
        field_defs.extend(tuple(sorted((f
                                        for f in dct.values()
                                        if isinstance(f, _Field)),
                                key=lambda f: f._creation_order)))
        newcls._field_defs = tuple(field_defs)

        field_mappings = {}
        for base in bases:
            if hasattr(base, "_field_mappings"):
                field_mappings.update(base._field_mappings)
        field_mappings.update({f.name: f for f in field_defs})
        newcls._field_mappings = field_mappings

        newcls.DEFAULT_FIELD_ORDER = tuple(f.name for f in field_defs)
        return newcls


def add_metaclass(metaclass):
    """
    Decorate a class to replace it with a metaclass-constructed version.

    Usage:

    @add_metaclass(MyMeta)
    class MyClass(object):
        ...

    That code produces a class equivalent to

    class MyClass(object, metaclass=MyMeta):
        ...

    on Python 3 or

    class MyClass(object):
        __metaclass__ = MyMeta

    on Python 2

    Requires Python 2.6 or later (for class decoration). For use on Python
    2.5 and earlier, use the legacy syntax:

    class MyClass(object):
        ...
    MyClass = add_metaclass(MyClass)

    Taken from six.py.
    https://bitbucket.org/gutworth/six/src/default/six.py
    """
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        for slots_var in orig_vars.get('__slots__', ()):
            orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


@add_metaclass(_ASSLineMeta)
class _ASSLine(object):
    def __init__(self, *args, **kwargs):
        self.fields = {f.name: f.default for f in self._field_defs}

        for k, v in zip(self.DEFAULT_FIELD_ORDER, args):
            self.fields[k] = v

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                self.fields[k] = v

    def dump(self, field_order=None):
        """ Dump an ASS line into text format. Has an optional field order
        parameter in case you have some wonky format.
        """
        if field_order is None:
            field_order = self.DEFAULT_FIELD_ORDER

        return ",".join(_Field.dump(self.fields[field])
                        for field in field_order)

    def dump_with_type(self, field_order=None):
        """ Dump an ASS line into text format, with its type prepended. """
        return self.TYPE + ": " + self.dump(field_order)

    @classmethod
    def parse(cls, line, field_order=None):
        """ Parse an ASS line from text format. Has an optional field order
        parameter in case you have some wonky format.
        """
        if field_order is None:
            field_order = cls.DEFAULT_FIELD_ORDER

        parts = line.split(",", len(field_order) - 1)

        if len(parts) != len(field_order):
            raise ValueError("arity of line does not match arity of field order")

        fields = {}

        for field_name, field in zip(field_order, parts):
            fields[field_name] = cls._field_mappings[field_name].parse(field)

        return cls(**fields)


class Style(_ASSLine):
    """ A style line in ASS.
    """
    TYPE = "Style"

    name = _Field("Name", str, default="Default")
    fontname = _Field("Fontname", str, default="Arial")
    fontsize = _Field("Fontsize", int, default=20)
    primary_color = _Field("PrimaryColour", ASSColor, default=ASSColor.WHITE)
    secondary_color = _Field("SecondaryColour", ASSColor, default=ASSColor.RED)
    outline_color = _Field("OutlineColour", ASSColor, default=ASSColor.BLACK)
    back_color = _Field("BackColour", ASSColor, default=ASSColor.BLACK)
    bold = _Field("Bold", bool, default=False)
    italic = _Field("Italic", bool, default=False)
    underline = _Field("Underline", bool, default=False)
    strike_out = _Field("StrikeOut", bool, default=False)
    scale_x = _Field("ScaleX", float, default=100)
    scale_y = _Field("ScaleY", float, default=100)
    spacing = _Field("Spacing", float, default=0)
    angle = _Field("Angle", float, default=0)
    border_style = _Field("BorderStyle", int, default=1)
    outline = _Field("Outline", float, default=2)
    shadow = _Field("Shadow", float, default=2)
    alignment = _Field("Alignment", int, default=2)
    margin_l = _Field("MarginL", float, default=10)
    margin_r = _Field("MarginR", float, default=10)
    margin_v = _Field("MarginV", float, default=10)
    encoding = _Field("Encoding", int, default=1)


class _Event(_ASSLine):
    layer = _Field("Layer", int, default=0)
    start = _Field("Start", timedelta, default=timedelta(0))
    end = _Field("End", timedelta, default=timedelta(0))
    style = _Field("Style", str, default="Default")
    name = _Field("Name", str, default=None)
    margin_l = _Field("MarginL", float, default=0)
    margin_r = _Field("MarginR", float, default=0)
    margin_v = _Field("MarginV", float, default=0)
    effect = _Field("Effect", str, default=None)
    text = _Field("Text", str, default=None)


class Dialogue(_Event):
    """ A dialog event.
    """
    TYPE = "Dialogue"


class Comment(_Event):
    """ A comment event.
    """
    TYPE = "Comment"


class Picture(_Event):
    """ A picture event. Not widely supported.
    """
    TYPE = "Picture"


class Sound(_Event):
    """ A sound event. Not widely supported.
    """
    TYPE = "Sound"


class Movie(_Event):
    """ A movie event. Not widely supported.
    """
    TYPE = "Movie"


class Command(_Event):
    """ A command event. Not widely supported.
    """
    TYPE = "Command"
