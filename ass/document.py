from datetime import timedelta
import itertools


class Color(object):
    """ Represents a color in the ASS format.
    """
    def __init__(self, r, g, b, a=0):
        """ Made up of red, green, blue and alpha components (in that order!).
        """
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def to_int(self):
        return self.a + (self.b << 8) + (self.g << 16) + (self.r << 24)

    def to_ass(self):
        """ Convert this color to a Visual Basic (ASS) color code.
        """
        return "&H{a:02X}{b:02X}{g:02X}{r:02X}".format(**self.__dict__)

    @classmethod
    def from_ass(cls, v):
        """ Convert a Visual Basic (ASS) color code into an ``Color``.
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
        return "{name}(r=0x{r:02x}, g=0x{g:02x}, b=0x{b:02x}, a=0x{a:02x})".format(
            name=self.__class__.__name__,
            r=self.r,
            g=self.g,
            b=self.b,
            a=self.a
        )

Color.WHITE = Color(255, 255, 255)
Color.RED = Color(255, 0, 0)
Color.BLACK = Color(0, 0, 0)


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
        return obj.fields.get(self.name, self.default)

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


class _WithFieldMeta(type):
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


class Tag(object):
    """ A tag in ASS, e.g. {\\b1}. Multiple can be used like {\\b1\\i1}. """
    def __init__(self, name, params):
        self.name = name
        self.param = params

    def dump(self):
        if not self.params:
            params = ""
        elif len(self.params) == 1:
            params = params[0]
        else:
            params = "(" + \
                     ",".join(_Field.dump(param) for param in self.params) + \
                     ")"

        return "\\{name}{params}".format(name=self.name, params=params)


    @classmethod
    def parse(cls, part):
        raise NotImplementedError


@add_metaclass(_WithFieldMeta)
class Document(object):
    """ An ASS document. """
    SCRIPT_INFO_HEADER = "[Script Info]"
    STYLE_SSA_HEADER = "[V4 Styles]"
    STYLE_ASS_HEADER = "[V4+ Styles]"
    EVENTS_HEADER = "[Events]"

    FORMAT_TYPE = "Format"

    VERSION_ASS = "v4.00+"
    VERSION_SSA = "v4.00"

    script_type = _Field("ScriptType", str, default=VERSION_ASS)
    play_res_x = _Field("PlayResX", int, default=640)
    play_res_y = _Field("PlayResY", int, default=480)
    wrap_style = _Field("WrapStyle", int, default=0)
    scaled_border_and_shadow = _Field("ScaledBorderAndShadow", str,
                                      default="yes")

    def __init__(self):
        """ Create an empty ASS document.
        """
        self.fields = {}

        self.styles = []
        self.styles_field_order = Style.DEFAULT_FIELD_ORDER

        self.events = []
        self.events_field_order = _Event.DEFAULT_FIELD_ORDER

    @classmethod
    def parse_file(cls, f):
        """ Parse an ASS document from a file object.
        """
        doc = cls()

        lines = ((i, line)
                 for i, line in ((i, line.rstrip("\r\n"))
                                 for i, line in enumerate(f))
                 if line and line[0] != ";")

        # [Script Info]
        for i, line in lines:
            if i == 0 and line[:3] == "\xef\xbb\xbf":
                line = line[3:]

            if i == 0 and line[0] == u"\ufeff":
                line = line.strip(u"\ufeff")

            if line.lower() == Document.SCRIPT_INFO_HEADER.lower():
                break

            raise ValueError("expected script info header")

        # field_name: field
        for i, line in lines:
            if (doc.script_type.lower() == doc.VERSION_ASS.lower() and
                line.lower() == Document.STYLE_ASS_HEADER.lower()) or \
               (doc.script_type.lower() == doc.VERSION_SSA.lower() and
                line.lower() == Document.STYLE_SSA_HEADER.lower()):
               break

            field_name, field = line.split(":", 1)
            field = field.lstrip()

            if field_name in Document._field_mappings:
                field = Document._field_mappings[field_name].parse(field)

            doc.fields[field_name] = field

        # [V4 Styles]
        i, line = next(lines)

        type_name, line = line.split(":", 1)
        line = line.lstrip()

        # Format: ...
        if type_name.lower() != Document.FORMAT_TYPE.lower():
            raise ValueError("expected format line in styles")

        field_order = [x.strip() for x in line.split(",")]
        doc.styles_field_order = field_order

        # Style: ...
        for i, line in lines:
            if line.lower() == Document.EVENTS_HEADER.lower():
                break

            type_name, line = line.split(":", 1)
            line = line.lstrip()

            if type_name.lower() != Style.TYPE.lower():
                raise ValueError("expected style line in styles")

            doc.styles.append(Style.parse(line, field_order))

        # [Events]
        i, line = next(lines)

        type_name, line = line.split(":", 1)
        line = line.lstrip()

        # Format: ...
        if type_name.lower() != Document.FORMAT_TYPE.lower():
            raise ValueError("expected format line in events")

        field_order = [x.strip() for x in line.split(",")]
        doc.events_field_order = field_order

        # Dialogue: ...
        # Comment: ...
        # etc.
        for i, line in lines:
            type_name, line = line.split(":", 1)
            line = line.lstrip()

            doc.events.append(({
                "Dialogue": Dialogue,
                "Comment":  Comment,
                "Picture":  Picture,
                "Sound":    Sound,
                "Movie":    Movie,
                "Command":  Command
            })[type_name].parse(line, field_order))

        return doc

    def dump_file(self, f):
        """ Dump this ASS document to a file object.
        """
        f.write(Document.SCRIPT_INFO_HEADER + "\n")
        for k in itertools.chain((field for field in self.DEFAULT_FIELD_ORDER
                                  if field in self.fields),
                                 (field for field in self.fields
                                  if field not in self._field_mappings)):
            f.write(k + ": " + _Field.dump(self.fields[k]) + "\n")
        f.write("\n")

        f.write(Document.STYLE_ASS_HEADER + "\n")
        f.write(Document.FORMAT_TYPE +  ": " +
                ", ".join(self.styles_field_order) + "\n")
        for style in self.styles:
            f.write(style.dump_with_type(self.styles_field_order) + "\n")
        f.write("\n")

        f.write(Document.EVENTS_HEADER + "\n")
        f.write(Document.FORMAT_TYPE +  ": " +
                ", ".join(self.events_field_order) + "\n")
        for event in self.events:
            f.write(event.dump_with_type(self.events_field_order) + "\n")
        f.write("\n")


@add_metaclass(_WithFieldMeta)
class _Line(object):
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
            if field_name in cls._field_mappings:
                field = cls._field_mappings[field_name].parse(field)
            fields[field_name] = field

        return cls(**fields)


class Style(_Line):
    """ A style line in ASS.
    """
    TYPE = "Style"

    name = _Field("Name", str, default="Default")
    fontname = _Field("Fontname", str, default="Arial")
    fontsize = _Field("Fontsize", float, default=20)
    primary_color = _Field("PrimaryColour", Color, default=Color.WHITE)
    secondary_color = _Field("SecondaryColour", Color, default=Color.RED)
    outline_color = _Field("OutlineColour", Color, default=Color.BLACK)
    back_color = _Field("BackColour", Color, default=Color.BLACK)
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
    margin_l = _Field("MarginL", int, default=10)
    margin_r = _Field("MarginR", int, default=10)
    margin_v = _Field("MarginV", int, default=10)
    encoding = _Field("Encoding", int, default=1)


class _Event(_Line):
    layer = _Field("Layer", int, default=0)
    start = _Field("Start", timedelta, default=timedelta(0))
    end = _Field("End", timedelta, default=timedelta(0))
    style = _Field("Style", str, default="Default")
    name = _Field("Name", str, default="")
    margin_l = _Field("MarginL", int, default=0)
    margin_r = _Field("MarginR", int, default=0)
    margin_v = _Field("MarginV", int, default=0)
    effect = _Field("Effect", str, default="")
    text = _Field("Text", str, default="")


class Dialogue(_Event):
    """ A dialog event.
    """
    TYPE = "Dialogue"

    def parse(self):
        parts = []

        current = []

        backslash = False

        it = iter(self.text)

        for c in it:
            if backslash:
                if c == "{":
                    current.append(c)
                else:
                    current.append("\\" + c)
                backslash = False
            elif c == "{":
                if current:
                    parts.append("".join(current))

                current = []

                tag_part = []

                for c2 in it:
                    if c2 == "}":
                        break
                    tag_part.append(c2)

                parts.append(Tag.parse("".join(tag_part)))
            elif c == "\\":
                backslash = True
            else:
                current.append(c)

        if backslash:
            current.append("\\")

        if current:
            parts.append("".join(current))

        return parts

    def strip_tags(self, keep_drawing_commands=False):
        text_parts = []

        it = iter(self.parse())

        for part in it:
            if isinstance(part, Tag):
                # if we encounter a \p1 tag, skip everything until we get to
                # \p0
                if not keep_drawing_commands and part.name == "p" and \
                   part.params == [1]:
                    for part2 in it:
                        if isinstance(part2, Tag) and part2.name == "p" and \
                           part2.params == [0]:
                           break
            else:
                text_parts.append(part)

        return "".join(text_parts)

    def unparse(self, parts):
        self.text = "".join(n.dump() if isinstance(n, Tag)
                            else n
                            for n in parts)


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
