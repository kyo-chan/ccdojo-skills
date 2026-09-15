#!/usr/bin/env python3
"""HTMLをIllustrator変換用に整える。

- Webフォント読み込み（Google Fonts等）を除去 → ローカルフォント参照にしてType 3埋め込みを回避
- box-shadow を除去（PDF化でラスターになるため）
- linear-gradient を単色に置換（同上）
- プレビュー用の縮小表示を実寸に固定
"""
import argparse
import pathlib
import re


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--paper', default='594mm 841mm', help='実寸サイズ 例 "594mm 841mm"')
    ap.add_argument('--keep-shadow', action='store_true', help='box-shadowを残す')
    a = ap.parse_args()

    t = pathlib.Path(a.src).read_text()

    # 1) Webフォント読み込みを除去（ローカルにインストール済みの同名フォントが使われる）
    t = re.sub(r'<link[^>]*fonts\.(googleapis|gstatic)\.com[^>]*>', '', t)
    t = re.sub(r'<link rel="preconnect"[^>]*>', '', t)
    t = re.sub(r'@import\s+url\([^)]*fonts\.googleapis[^)]*\);', '', t)

    # 2) ラスター化される表現を除去
    if not a.keep_shadow:
        t = re.sub(r'box-shadow\s*:[^;}]+;', '', t)
    # linear-gradient(...) → 最初に現れた色（var()も可）で塗りつぶす
    def flatten(m):
        body = m.group(1)
        color = re.search(r'(var\(--[\w-]+\)|#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))', body)
        return color.group(1) if color else 'transparent'
    t = re.sub(r'linear-gradient\(([^;]*?)\)(?=\s*[;,}])', flatten, t)

    # 3) プレビュー縮小を解除して実寸に固定
    pw, ph = a.paper.split()
    t = re.sub(r'width:[\d.]+mm;\s*height:[\d.]+mm;(\s*margin:0 auto;)', f'width:{pw}; height:{ph};\\1', t, count=1)
    t = re.sub(r'transform:\s*scale\([\d.]+\);', 'transform:none;', t)
    t = re.sub(r'body\{([^}]*)padding:[\d.]+mm 0;', r'body{\1padding:0;', t)

    pathlib.Path(a.dst).write_text(t)
    print(f'prepared -> {a.dst}')
    print('※ pdffonts で CID TrueType になっているか確認すること（Type 3 なら失敗）')


if __name__ == '__main__':
    main()
