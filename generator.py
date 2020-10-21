from PIL import Image, ImageDraw, ImageFont


def fancyhex(num):
    return "0x" + hex(num)[2:].upper()    


def draw_glyph(glyph):
    img = Image.new("1", (8, 8), (1))
    fnt = ImageFont.truetype("8x8 Wide Mono Bold.ttf", 16)
    cursor = ImageDraw.Draw(img)
    cursor.text((0, -2), glyph, font=fnt, fill=(0))

    def extract(start_y):
        data = 0
        for i in range(32):
            x = (i % 8)
            y = start_y + (i // 8)
            pixel = img.getpixel((x, y))
            if pixel > 0:
                data |= (1 << i)
        return fancyhex(data)

    return extract(4), extract(0)


def atlas(charset):
    charset = [i for i in sorted(set(charset)) if ord(i) >= 32 and ord(i) <= 126]
    glyphs = [n for pair in map(draw_glyph, charset) for n in pair]
    return {c:charset.index(c) for c in charset}, glyphs


def pack(strings):
    charset = sorted(set("".join(strings)))
    charmap, glyphs = atlas(charset)

    def packpoints(points):
        a, b, c, d = points
        return fancyhex(a | (b << 8) | (c << 16) | (d << 24))

    def packstr(string):
        points = [charmap.get(c) for c in string if c in charmap]
        while len(points) % 4 != 0:
            points.append(0xFF)
        return list(map(packpoints, (points[i:i+4] for i in range(0, len(points), 4))))
        
    return list(map(packstr, strings)), glyphs


def make_define(key, data):
    if len(data):
        return f"#define STR_{key} int[{len(data)}]({', '.join(data)})"
    else:
        return f"#define STR_{key} -1"


print_template = """
vec4 Print(vec2 fragCoord, ivec2 LowerLeft, int[STRLEN] Line)
{
    ivec2 Pixel = ivec2(floor(fragCoord)) - LowerLeft;
    int CharIndex = Pixel.x / 8;
    int GlyphIndex = UnpackChar(Line[abs(CharIndex / 4) % STRLEN], CharIndex % 4);
    return PrintInner(ivec2(PIXEL_WIDTH, 8), Pixel, GlyphIndex);
}
""".strip()


null_print = """
vec4 Print(vec2 fragCoord, ivec2 LowerLeft, int Line)
{
    return vec4(0.0);
}
""".strip()


def generate_glsl(strings):
    packed, glyphs = pack(strings.values())
    defines = [make_define(*p) for p in zip(strings.keys(), packed)]
    sizes = sorted(set([len(p) for p in packed]))
    prints = []
    for size in sizes:
        if size > 0:
            partial = print_template.replace("STRLEN", str(size))
            prints.append(partial.replace("PIXEL_WIDTH", str(size * 4 * 8)))
        else:
            prints.append(null_print)
    glyph_count = len(glyphs)//2
    glyphsdef = f"#define GLYPH_COUNT {glyph_count }\n"
    glyphsdef += f"const int GLYPHS[{glyph_count*2}] = int[{glyph_count*2}]({', '.join(glyphs)});\n\n"
    return glyphsdef + "\n".join(defines + prints)




strings = {str(i):line for (i, line) in enumerate(open("demo_text.txt", "r").readlines())}


print(generate_glsl(strings))