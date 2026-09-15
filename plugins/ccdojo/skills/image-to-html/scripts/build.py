#!/usr/bin/env python3
"""テンプレートHTMLの画像プレースホルダを base64 で埋め込み、単一HTMLを書き出す。

テンプレート側には {{IMG:ファイル名}} の形でプレースホルダを書いておく。
  例) <img src="{{IMG:char.png}}">
--full を付けると、プレビュー縮小を解除した実寸検証用HTMLも書き出す。
"""
import argparse
import base64
import pathlib
import re


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('template', help='テンプレートHTML')
    ap.add_argument('output', help='出力HTML')
    ap.add_argument('--assets-dir', default='.', help='画像の置き場所')
    ap.add_argument('--full', help='実寸検証用HTMLの出力先')
    ap.add_argument('--paper', default='594mm 841mm', help='実寸サイズ 例 "594mm 841mm"')
    ap.add_argument('--preview-size', default='178.2mm 252.3mm', help='プレビュー用ラッパーのサイズ')
    a = ap.parse_args()

    base = pathlib.Path(a.assets_dir)
    t = pathlib.Path(a.template).read_text()

    def embed(m):
        p = base / m.group(1)
        mime = 'image/png' if p.suffix.lower() == '.png' else 'image/jpeg'
        return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()

    out = re.sub(r'\{\{IMG:([^}]+)\}\}', embed, t)
    pathlib.Path(a.output).write_text(out)
    print(f'built {a.output} ({len(out)//1024} KB)')

    if a.full:
        pw, ph = a.paper.split()
        vw, vh = a.preview_size.split()
        full = (out.replace(f'width:{vw}; height:{vh};', f'width:{pw}; height:{ph};')
                   .replace('transform:scale(0.3);', 'transform:none;'))
        full = re.sub(r'padding:\d+mm 0;', 'padding:0;', full)
        pathlib.Path(a.full).write_text(full)
        print(f'built {a.full}（実寸検証用）')


if __name__ == '__main__':
    main()
