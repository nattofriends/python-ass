#!/usr/bin/env python

from PIL import Image
import ass
from datetime import timedelta

im_out = Image.new("RGB", (1280, 720))

ctx = ass.renderer.Context()
r = ctx.make_renderer()
r.set_fonts(fontconfig_config="/usr/local/etc/fonts/fonts.conf")
r.set_all_sizes(im_out.size)

with open("test.ass") as f:
    doc = ass.parse(f)

t = ctx.document_to_track(doc)

im_data = im_out.load()

for img in r.render_frame(t, timedelta(0)):
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
            r_in, g_in, b_in = im_data[x + img.dst_x, y + img.dst_y]
            a_in = ord(img.bitmap[sp + x])

            r_out = min(255, r_in + (r * a_in // 256))
            g_out = min(255, g_in + (g * a_in // 256))
            b_out = min(255, b_in + (b * a_in // 256))

            im_data[x + img.dst_x, y + img.dst_y] = (r_out, g_out, b_out)

        sp += img.stride


im_out.show()
