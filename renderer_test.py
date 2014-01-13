#!/usr/bin/env python

from PIL import Image
import ass
from datetime import timedelta
import sys

with open("test.ass") as f:
    doc = ass.parse(f)

SIZE = (1280, 720)

ctx = ass.renderer.Context()

r = ctx.make_renderer()
r.set_fonts(fontconfig_config="/usr/local/etc/fonts/fonts.conf")
r.set_all_sizes(SIZE)

sys.stdout.write("loading document... ")
sys.stdout.flush()
t = ctx.document_to_track(doc)
print("ok! {} styles, {} events".format(len(t.styles), len(t.events)))

im_out = Image.new("RGB", SIZE, 0xed9564)
im_data = im_out.load()

for img in r.render_frame(t, timedelta(0)):
    r, g, b, a = img.rgba

    for y in range(img.h):
        for x in range(img.w):
            a_src = img[x, y] * (256 - a) // 256
            r_dst, g_dst, b_dst = im_data[x + img.dst_x, y + img.dst_y]
            r_out = ((r * a_src) + (r_dst * (256 - a_src))) // 256
            g_out = ((g * a_src) + (g_dst * (256 - a_src))) // 256
            b_out = ((b * a_src) + (b_dst * (256 - a_src))) // 256
            im_data[x + img.dst_x, y + img.dst_y] = (r_out, g_out, b_out)

im_out.show()

im_out.save("test.png")
