#!/usr/bin/env python3
"""再現版と元画像の差分を測り、上下に分割した比較画像を書き出す。"""
import sys

from PIL import Image, ImageChops


def main():
    if len(sys.argv) < 3:
        print('usage: compare.py 再現版.png 元画像.png [出力prefix]')
        sys.exit(1)
    new_p, org_p = sys.argv[1], sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else 'cmp'

    a = Image.open(new_p).convert('RGB')
    b = Image.open(org_p).convert('RGB').resize(a.size)

    d = ImageChops.difference(a, b)
    hist = d.convert('L').histogram()
    diff_px = sum(hist[40:])
    print(f'差分画素: {diff_px} / {a.size[0]*a.size[1]} ({diff_px/(a.size[0]*a.size[1])*100:.2f}%)')

    # 目視用：上半分・下半分を元版と並べて書き出す
    W, H = a.size
    for name, y0, y1 in (('top', 0, int(H * 0.42)), ('bottom', int(H * 0.84), H)):
        pair = Image.new('RGB', (W, (y1 - y0) * 2), 'white')
        pair.paste(b.crop((0, y0, W, y1)), (0, 0))
        pair.paste(a.crop((0, y0, W, y1)), (0, y1 - y0))
        pair.save(f'{prefix}_{name}.png')
        print(f'比較画像（上=元 / 下=再現）: {prefix}_{name}.png')


if __name__ == '__main__':
    main()
