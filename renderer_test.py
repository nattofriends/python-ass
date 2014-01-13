#!/usr/bin/env python

from PIL import Image
import ass
from datetime import timedelta

with open("foo.ass") as f:
    doc = ass.parse(f)

im_out = Image.new("RGB", (1920, 1080))

ctx = ass.renderer.Context()

r = ctx.make_renderer()
r.set_fonts(fontconfig_config="/usr/local/etc/fonts/fonts.conf")
r.set_all_sizes(im_out.size)

print("loading document...")
t = ctx.document_to_track(doc)
print("ok! {} styles, {} events".format(t.n_styles, t.n_events))

im_data = im_out.load()

for img in r.render_frame(t, timedelta(0, 58)):
    if img.w == 0 or img.h == 0:
        continue

    sp = 0

    color = img.color

    a = color & 0xff
    color >>= 8

    b = color & 0xff
    color >>= 8

    g = color & 0xff
    color >>= 8

    r = color & 0xff

    for y in range(img.h):
        for x in range(img.w):
            r_src, g_src, b_src = r / 256., g / 256., b / 256.
            a_src = ord(img.bitmap[sp + x]) / 256. * (1.0 - a / 256.)

            r_dst, g_dst, b_dst = im_data[x + img.dst_x, y + img.dst_y]
            r_dst /= 256.
            g_dst /= 256.
            b_dst /= 256.

            r_out = (r_src * a_src) + (r_dst * (1.0 - a_src))
            g_out = (g_src * a_src) + (g_dst * (1.0 - a_src))
            b_out = (b_src * a_src) + (b_dst * (1.0 - a_src))

            im_data[x + img.dst_x, y + img.dst_y] = (
                int(r_out * 256),
                int(g_out * 256),
                int(b_out * 256)
            )

        sp += img.stride

im_out.show()
