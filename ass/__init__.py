from . import document

try:
    from . import renderer
except Exception as e:
    import warnings
    warnings.warn("Could not load renderer: " + str(e))

__all__ = ["document", "renderer", "parse"]

parse = document.Document.parse_file
