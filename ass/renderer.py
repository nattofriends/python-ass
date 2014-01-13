import ctypes
import ctypes.util

from io import StringIO

_libass = ctypes.cdll.LoadLibrary(ctypes.util.find_library("ass"))

_libass.ass_library_init.restype = ctypes.c_void_p

_libass.ass_library_done.argtypes = [ctypes.c_void_p]

_libass.ass_renderer_init.argtypes = [ctypes.c_void_p]
_libass.ass_renderer_init.restype = ctypes.c_void_p

_libass.ass_renderer_done.argtypes = [ctypes.c_void_p]

_libass.ass_free_track.argtypes = [ctypes.c_void_p]

_libass.ass_set_style_overrides.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_char_p)
]
_libass.ass_set_fonts.argtypes = [
    ctypes.c_void_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int
]
_libass.ass_fonts_update.argtypes = [ctypes.c_void_p]


class ImageSequence(object):
    def __init__(self, renderer, head_ptr):
        self.renderer = renderer
        self.head_ptr = head_ptr

    def __iter__(self):
        cur = self.head_ptr
        while cur:
            yield cur.contents
            cur = cur.contents.next_ptr


class Image(ctypes.Structure):
    TYPE_CHARACTER = 0
    TYPE_OUTLINE = 1
    TYPE_SHADOW = 2


Image._fields_ = [
    ("w", ctypes.c_int),
    ("h", ctypes.c_int),
    ("stride", ctypes.c_int),
    ("bitmap", ctypes.POINTER(ctypes.c_char)),
    ("color", ctypes.c_uint32),
    ("dst_x", ctypes.c_int),
    ("dst_y", ctypes.c_int),
    ("next_ptr", ctypes.POINTER(Image)),
    ("type", ctypes.c_int)
]

_libass.ass_render_frame.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_longlong,
    ctypes.POINTER(ctypes.c_int)
]
_libass.ass_render_frame.restype = ctypes.POINTER(Image)

_libass.ass_read_memory.argtypes = [
    ctypes.c_void_p,
    ctypes.c_char_p,
    ctypes.c_size_t,
    ctypes.c_char_p
]
_libass.ass_read_memory.restype = ctypes.c_void_p


def _make_libass_setter(name, types):
    fun = _libass[name]
    fun.argtypes = [ctypes.c_void_p] + types

    def setter(self, v):
        if len(types) == 1:
            fun(self._ptr, v)
        else:
            fun(self._ptr, *v)
        self._internal_fields[name] = v

    return setter


def _make_libass_property(name, types):
    def getter(self):
        return self._internal_fields.get(name)

    return property(getter, _make_libass_setter(name, types))


class Context(object):
    def __init__(self):
        self._ptr = _libass.ass_library_init()
        self._internal_fields = {}

        self._style_overrides_buffers = []

        if not self._ptr:
            raise RuntimeError("could not initialize libass")

        self.extract_fonts = False
        self.style_overrides = []

    def __del__(self):
        if self._ptr:
            _libass.ass_library_done(self._ptr)

    fonts_dir = _make_libass_property("ass_set_fonts_dir", [ctypes.c_char_p])
    extract_fonts = _make_libass_property("ass_set_extract_fonts", [ctypes.c_int])

    @property
    def style_overrides(self):
        return [buf.value for buf in self._style_overrides_buffers]

    @style_overrides.setter
    def style_overrides(self, xs):
        self._style_overrides_buffers = [ctypes.create_string_buffer(x)
                                         for x in xs ]

        if self._style_overrides_buffers:
            ptr = (ctypes.c_char_p * len(self._style_overrides_buffers))(*[
                ctypes.addressof(buf)
                for buf in self._style_overrides_buffers
            ])
        else:
            ptr = ctypes.POINTER(ctypes.c_char_p)()

        _libass.ass_set_style_overrides(
            self._ptr,
            ptr)

    def make_renderer(self):
        """ Make a renderer instance for rendering tracks. """
        return Renderer(self)

    def parse_to_track(self, data, codepage="UTF-8"):
        """ Parse ASS data to a track. """
        ptr = _libass.ass_read_memory(self._ptr, data, len(data),
                                      codepage.encode("utf-8"))
        return Track(self, ptr)

    def document_to_track(self, doc):
        """ Convert an ASS document to a track. """
        f = StringIO()
        doc.dump_file(f)
        return self.parse_to_track(f.getvalue().encode("utf-8"))


class Renderer(object):
    SHAPING_SIMPLE = 0
    SHAPING_COMPLEX = 1

    HINTING_NONE = 0
    HINTING_LIGHT = 1
    HINTING_NORMAL = 2
    HINTING_NATIVE = 3

    def __init__(self, ctx):
        self._ctx = ctx

        self._fonts_set = False
        self._ptr = _libass.ass_renderer_init(ctx._ptr)
        self._internal_fields = {}

        if not self._ptr:
            raise RuntimeError("could not initialize renderer")

        self.frame_size = (640, 480)
        self.storage_size = (640, 480)
        self.margins = (0, 0, 0, 0)
        self.use_margins = True
        self.font_scale = 1
        self.line_spacing = 0
        self.pixel_aspect = 1.0

    def __del__(self):
        if self._ptr:
            _libass.ass_renderer_done(self._ptr)

    frame_size = _make_libass_property("ass_set_frame_size", [
        ctypes.c_int,
        ctypes.c_int
    ])
    storage_size = _make_libass_property("ass_set_storage_size", [
        ctypes.c_int,
        ctypes.c_int
    ])
    shaper = _make_libass_property("ass_set_shaper", [
        ctypes.c_int
    ])
    margins = _make_libass_property("ass_set_margins", [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int
    ])
    use_margins = _make_libass_property("ass_set_use_margins", [
        ctypes.c_int
    ])
    pixel_aspect = _make_libass_property("ass_set_pixel_aspect", [
        ctypes.c_double
    ])
    aspect_ratio = _make_libass_property("ass_set_aspect_ratio", [
        ctypes.c_double,
        ctypes.c_double
    ])
    font_scale = _make_libass_property("ass_set_font_scale", [
        ctypes.c_double
    ])
    hinting = _make_libass_property("ass_set_hinting", [
        ctypes.c_int
    ])
    line_spacing = _make_libass_property("ass_set_line_spacing", [
        ctypes.c_double
    ])
    line_position = _make_libass_property("ass_set_line_position", [
        ctypes.c_double
    ])

    def set_fonts(self, default_font=None, default_family=None,
                  fontconfig_config=None, update_fontconfig=None):
        fc = fontconfig_config is not None

        if update_fontconfig is None:
            update_fontconfig = fontconfig_config is not None

        if default_font is not None:
            default_font = default_font.encode("utf-8")

        if default_family is not None:
            default_family = default_family.encode("utf-8")

        _libass.ass_set_fonts(self._ptr, default_font, default_family,
                              fc, fontconfig_config.encode("utf-8") or "",
                              update_fontconfig)
        self._fonts_set = True

    def update_fonts(self):
        if not self._fonts_set:
            raise RuntimeError("set_fonts before updating them")
        _libass.ass_fonts_update(self._ptr)

    set_cache_limits = _make_libass_setter("ass_set_cache_limits", [
        ctypes.c_int,
        ctypes.c_int
    ])

    def render_frame(self, track, now):
        if not self._fonts_set:
            raise RuntimeError("set_fonts before rendering")
        ms = int(now.total_seconds() * 1000 + now.microseconds // 1000)
        head = _libass.ass_render_frame(self._ptr, track._ptr, ms,
                                        ctypes.POINTER(ctypes.c_int)())
        return ImageSequence(self, head)

    def set_all_sizes(self, size):
        self.frame_size = size
        self.storage_size = size
        self.pixel_aspect = 1.0


class Track(object):
    def __init__(self, ctx, ptr):
        self._ctx = ctx
        self._ptr = ptr

        if not self._ptr:
            raise ValueError("could not parse ASS track")

    def __del__(self):
        if self._ptr:
            _libass.ass_free_track(self._ptr)
