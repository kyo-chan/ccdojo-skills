#!/usr/bin/env python3
"""元画像から再現用の素材を抽出するユーティリティ。

crop    : 指定領域を切り出す。--auto を付けると地色を避けて内側の境界を自動検出する
recolor : HSVで色相域を指定して別色に置換する（イラストのトーン変更用）
cutout  : 外周からのフラッドフィルで背景を透明化し、連結成分で対象だけ残す
"""
import argparse
import colorsys
from collections import deque

from PIL import Image, ImageDraw


def parse_box(s, w, h):
    """0〜1の比率 or 絶対px の4値を (x0,y0,x1,y1) に変換する"""
    v = [float(x) for x in s.split(',')]
    if max(v) <= 1.0:
        return (int(v[0] * w), int(v[1] * h), int(v[2] * w), int(v[3] * h))
    return tuple(int(x) for x in v)


def is_hue_in(px, lo, hi, min_sat, min_val):
    r, g, b = px[:3]
    hh, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return s > min_sat and v > min_val and lo <= hh * 360 <= hi


def cmd_crop(a):
    im = Image.open(a.src).convert('RGB')
    W, H = im.size
    box = parse_box(a.box, W, H)
    if a.auto:
        # 中央の行/列から外周の地色を走査し、地色でなくなる位置を境界とする
        reg = im.crop(box)
        w, h = reg.size
        p = reg.load()
        lo, hi = [float(x) for x in a.bg_hue.split(',')]

        def bg(px):
            return is_hue_in(px, lo, hi, a.bg_sat, 0.7)

        midx, midy = w // 2, h // 2
        left = next((x for x in range(w) if not bg(p[x, midy])), 0)
        right = next((x for x in range(w - 1, -1, -1) if not bg(p[x, midy])), w - 1)
        top = next((y for y in range(h) if not bg(p[midx, y])), 0)
        bot = next((y for y in range(h - 1, -1, -1) if not bg(p[midx, y])), h - 1)
        box = (box[0] + left + a.inset, box[1] + top + a.inset,
               box[0] + right - a.inset + 1, box[1] + bot - a.inset + 1)
    out = im.crop(box)
    if a.white_edge:
        d = ImageDraw.Draw(out)
        w, h = out.size
        e = a.white_edge
        for r in ([0, 0, w, e], [0, h - e, w, h], [0, 0, e, h], [w - e, 0, w, h]):
            d.rectangle(r, fill='white')
    out.save(a.dst)
    print(f'crop -> {a.dst} box={box} size={out.size}')


def cmd_recolor(a):
    im = Image.open(a.src).convert('RGBA')
    w, h = im.size
    p = im.load()
    lo, hi = [float(x) for x in a.from_hue.split(',')]
    n = 0
    for y in range(h):
        for x in range(w):
            r, g, b, al = p[x, y]
            hh, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if s > a.min_sat and lo <= hh * 360 <= hi:
                nr, ng, nb = colorsys.hsv_to_rgb(a.to_hue / 360, min(1.0, s * a.sat), v * a.val)
                p[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), al)
                n += 1
    im.save(a.dst)
    print(f'recolor -> {a.dst} 置換画素={n}')


def cmd_cutout(a):
    im = Image.open(a.src).convert('RGB')
    W, H = im.size
    crop = im.crop(parse_box(a.box, W, H)).convert('RGBA')
    w, h = crop.size
    p = crop.load()

    def is_bg(q):
        return q[0] > a.bg_level and q[1] > a.bg_level and q[2] > a.bg_level

    # 1) 外周に繋がる背景色のみ透明化（内側の白は残す）
    seen = [[False] * h for _ in range(w)]
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_bg(p[x, y]) and not seen[x][y]:
                seen[x][y] = True
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg(p[x, y]) and not seen[x][y]:
                seen[x][y] = True
                q.append((x, y))
    while q:
        x, y = q.popleft()
        p[x, y] = (0, 0, 0, 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[nx][ny] and is_bg(p[nx, ny]):
                seen[nx][ny] = True
                q.append((nx, ny))

    # 2) 連結成分に分け、最大成分（＝対象）だけを残す
    comp = [[-1] * h for _ in range(w)]
    comps = []
    for sx in range(w):
        for sy in range(h):
            if p[sx, sy][3] == 0 or comp[sx][sy] != -1:
                continue
            cid = len(comps)
            pix = []
            comp[sx][sy] = cid
            dq = deque([(sx, sy)])
            while dq:
                x, y = dq.popleft()
                pix.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and comp[nx][ny] == -1 and p[nx, ny][3] > 0:
                        comp[nx][ny] = cid
                        dq.append((nx, ny))
            comps.append(pix)
    comps.sort(key=len, reverse=True)
    keep = set(comps[0])
    # 最大成分（＝対象）の範囲内に完全に収まる小成分だけ残す（内側のハイライト等）。
    # 範囲外の成分（隣接する文字や別図形）は捨てる。
    mx0 = min(x for x, _ in comps[0]); mx1 = max(x for x, _ in comps[0])
    my0 = min(y for _, y in comps[0]); my1 = max(y for _, y in comps[0])
    for c in comps[1:]:
        if len(c) < a.keep_min:
            continue
        xs = [x for x, _ in c]; ys = [y for _, y in c]
        if min(xs) >= mx0 and max(xs) <= mx1 and min(ys) >= my0 and max(ys) <= my1:
            keep |= set(c)
    for x in range(w):
        for y in range(h):
            if p[x, y][3] > 0 and (x, y) not in keep:
                p[x, y] = (0, 0, 0, 0)
    crop = crop.crop(crop.getbbox())
    crop.save(a.dst)
    print(f'cutout -> {a.dst} size={crop.size} 成分数={len(comps)}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)

    c = sub.add_parser('crop')
    c.add_argument('src'); c.add_argument('dst')
    c.add_argument('--box', required=True, help='x0,y0,x1,y1（0〜1の比率 または px）')
    c.add_argument('--auto', action='store_true', help='地色を避けて内側境界を自動検出')
    c.add_argument('--bg-hue', default='30,70', help='地色の色相範囲（度）')
    c.add_argument('--bg-sat', type=float, default=0.12)
    c.add_argument('--inset', type=int, default=2)
    c.add_argument('--white-edge', type=int, default=0, help='外周nPXを白で塗る')
    c.set_defaults(func=cmd_crop)

    r = sub.add_parser('recolor')
    r.add_argument('src'); r.add_argument('dst')
    r.add_argument('--from-hue', required=True, help='置換元の色相範囲 例 25,70')
    r.add_argument('--to-hue', type=float, required=True, help='置換先の色相 例 142')
    r.add_argument('--min-sat', type=float, default=0.35, help='この彩度以下は保護（肌色/白を守る）')
    r.add_argument('--sat', type=float, default=0.85, help='彩度の倍率')
    r.add_argument('--val', type=float, default=0.79, help='明度の倍率')
    r.set_defaults(func=cmd_recolor)

    k = sub.add_parser('cutout')
    k.add_argument('src'); k.add_argument('dst')
    k.add_argument('--box', required=True)
    k.add_argument('--bg-level', type=int, default=236, help='この値超のRGBを背景とみなす')
    k.add_argument('--keep-min', type=int, default=200)
    k.set_defaults(func=cmd_cutout)

    a = ap.parse_args()
    a.func(a)


if __name__ == '__main__':
    main()
