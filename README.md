# python-ass

A library for parsing and manipulating Advanced SubStation Alpha subtitle
files.

## Example

**test.ass**

    [Script Info]
    ScriptType: v4.00+

    [V4+ Styles]
    Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

    [Events]
    Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,hello!

You can parse the file (duh):

    >>> import ass
    >>> with open("test.ass", "r") as f:
    ...     doc = ass.Document.parse_file(f)
    ...

Now you can access some of its styles:

    >>> doc.styles
    [<ass.Style object at ...>]
    >>> doc.styles[0].fontname
    'Arial'
    >>> doc.styles[0].primary_color  # "color", not "colour"
    Color(r=0xff, g=0xff, b=0xff, a=0x00)

And its event lines:

    >>> doc.events
    [<ass.Dialogue object at ...>]
    >>> doc.events[0].text
    'hello!'

You can dump them back out into ASS format, too:

    >>> doc.events[0].dump()
    '0,0:00:00.00,0:00:05.00,Default,,0,0,0,,hello!'

Or maybe the whole file:

    >>> with open("out.ass", "w") as f:
    ...     doc.dump_file(f)
    ...
