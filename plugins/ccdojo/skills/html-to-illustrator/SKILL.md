---
name: html-to-illustrator
description: HTMLで作ったポスター・チラシ・図版を、Adobe Illustratorで編集できる .ai データに変換する（macOS）。テキストが編集可能なまま、かつ文字ごとにバラけず塊単位のテキストフレームになるように変換する。「HTMLをaiデータにして」「Illustratorで開けるデータに変換」「入稿用のaiを作って」「HTMLからベクターデータを書き出して」といった依頼で使う。
---

# HTML を Illustrator データ（.ai）に変換する

## 前提

- macOS + Google Chrome + Adobe Illustrator がインストール済みであること
- HTMLで使っている日本語フォントが**ローカルにインストール済み**であること（これが最重要。後述）

## 手順

### 1. 変換用HTMLを作る（`scripts/prepare_html.py`）

元のHTMLをそのまま変換してはいけない。次の3点を必ず処理する。

| 処理 | 理由 |
|---|---|
| **Webフォント読み込みを外し、ローカルフォント参照にする** | Chromeは Webフォント（Google Fonts等）を **Type 3 フォント**で埋め込む。Type 3 のPDFはIllustratorで開くとテキストが編集不可能なパスになる。ローカル参照なら **CID TrueType** で埋め込まれ、テキストとして生きる |
| **`box-shadow` を削除** | PDF化時に低解像度のラスター画像になる |
| **`linear-gradient` を単色に置換** | 同上。グラデーションが必要ならIllustrator側で付け直す |

```bash
python3 scripts/prepare_html.py 元.html ai_source.html
```

フォントがローカルにあるかの確認：

```bash
system_profiler SPFontsDataType | grep -i "Noto Sans JP"
```

無ければ、ローカルにあるフォント（ヒラギノ等）に差し替えてから変換する。差し替え後は**必ずレンダリング差分を取る**（字幅が変わってレイアウトが崩れることがある）。

### 2. PDFに書き出す

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --no-sandbox \
  --no-pdf-header-footer --virtual-time-budget=9000 \
  --print-to-pdf="/絶対パス/out.pdf" "file:///絶対パス/ai_source.html"
```

HTML側に `@page{ size:594mm 841mm; margin:0 }` があれば、その用紙サイズで出る。確認：

```bash
pdffonts out.pdf | head -3     # CID TrueType なら成功。Type 3 なら手順1に戻る
python3 -c "import re;d=open('out.pdf','rb').read();print(re.findall(rb'/MediaBox\s*\[([^\]]+)\]',d)[:1])"
```

### 3. Illustratorで .ai に変換 ＋ テキストを塊に結合

```bash
osascript -e 'with timeout of 540 seconds
tell application "Adobe Illustrator"
  do javascript file "/絶対パス/scripts/html_pdf_to_ai.jsx"
end timeout'
```

JSXの入出力パスは、スクリプト冒頭の `SRC` / `DST` を書き換えて指定する。

このスクリプトは次を行う：

1. PDFを開く
2. **文字ごとに分割されたテキストフレームを、行・スタイル単位で結合**する
3. 結合時に字送りを補正する（下記）
4. `.ai` として保存（PDF互換オプション有効）

### 4. 検証

```bash
pdftoppm -png -r 48 -singlefile out.ai check          # .ai はPDF互換なのでそのまま描画できる
python3 -c "
from PIL import Image, ImageChops; import numpy as np
a=Image.open('元のレンダリング.png').convert('RGB'); b=Image.open('check.png').convert('RGB')
d=np.asarray(ImageChops.difference(a,b.resize(a.size))).sum(axis=2)
print(f'{(d>30).sum()/d.size*100:.2f}%')"
```

差分3〜5%程度なら実用範囲（結合による字送りの微差）。10%を超えるならログのw/target値を確認する。

## テキスト結合の要点

ChromeのPDFは1文字ずつ別々の描画命令を出すため、素直に開くと**文字数分のテキストフレーム**になる。結合しただけでは字間が崩れるので、次の3つを補正する。

1. **`letter-spacing` の復元** — CSSの字詰め情報はPDFに残らない。フォントサイズから元のCSS値を逆引きし、トラッキング（1/1000 em）として与える。JSX冒頭の `LS` テーブルに `[サイズmm, トラッキング]` を並べる
2. **約物（、。）の詰め対策** — Illustratorは約物を自動で半角に詰める。該当文字だけトラッキングを個別加算し、`autoKernType = NOAUTOKERN` / `tsume = 0` にする
3. **残差の幅補正** — 3文字以上は均等トラッキング、2文字は水平比率（`horizontalScale`）で吸収する。2文字にトラッキングを入れると隙間が1箇所に集中して不自然になる

## つまずきどころ（実際に踏んだもの）

| 症状 | 原因 | 対処 |
|---|---|---|
| `saveAs` が Error 1200 / 2110 で失敗する | **保存先パスに日本語が含まれている** | 英語パスに保存してから `mv` でリネームする |
| Illustratorが10分以上応答しなくなる | 全テキストフレーム（数百個）に段落属性を設定した | 属性設定は**新規に作る結合フレームだけ**に限定する |
| AppleScriptが `-1712` / `-609` で落ちる | `do javascript` の既定タイムアウト（120秒） | `with timeout of 540 seconds` で囲む |
| 字間がバラバラになる | 幅を元に合わせる反復トラッキング補正をかけた | letter-spacing復元と約物補正を先に行い、残差だけを1回で補正する |
| テキストが編集できないパスになる | Webフォント使用によるType 3埋め込み | 手順1（ローカルフォント参照）に戻る |

## 印刷入稿する場合

生成した `.ai` はRGB・塗り足しなし。入稿前にIllustrator上で以下が必要：

- 塗り足し3mm（アートボードを広げるのではなく、背景要素を外側へ伸ばす）
- トンボの追加
- CMYK変換（鮮やかな緑やオレンジは沈むので、変換後に色を確認する）
- フォントのアウトライン化（入稿先の要求次第）

## 運用ルール

**HTMLを正本とする。** 文言やレイアウトの変更はHTML側で行い、`.ai` を書き出し直す。`.ai` を直接編集するとHTMLとの差分が管理できなくなる。
