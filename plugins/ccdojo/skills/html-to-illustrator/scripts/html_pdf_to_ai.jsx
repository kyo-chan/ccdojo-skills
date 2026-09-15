/* HTML由来のPDFを開き、文字ごとに分割されたテキストを塊に結合して .ai として保存する。
 *
 * 使い方：下の SRC / DST / LS を書き換えてから実行する。
 *   osascript -e 'with timeout of 540 seconds
 *   tell application "Adobe Illustrator"
 *     do javascript file "/絶対パス/html_pdf_to_ai.jsx"
 *   end timeout'
 *
 * 注意：SRC / DST に日本語を含めると saveAs が Error 1200/2110 で失敗する。
 *       英語パスに保存し、シェル側で mv してリネームすること。
 */

// ===== 設定 ここから =====
var SRC = '/tmp/poster.pdf';       // 入力PDF（英語パス）
var DST = '/tmp/poster.ai';        // 出力AI（英語パス）

// CSSの font-size(mm) → letter-spacing(em × 1000)
// 元HTMLの letter-spacing を書き写す。未登録のサイズは 0 として扱われる。
var LS = [
  // [サイズmm, トラッキング]
  // [81, -35], [36, -85], [28, -20], [51, -20]
];
// ===== 設定 ここまで =====

var MM = 2.834645;   // mm → pt
app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;

function trackingFor(sizePt) {
  for (var i = 0; i < LS.length; i++) {
    if (Math.abs(sizePt - LS[i][0] * MM) < 1.2) return LS[i][1];
  }
  return 0;
}
function colorKey(c) {
  if (c && c.typename === 'RGBColor') return Math.round(c.red) + ',' + Math.round(c.green) + ',' + Math.round(c.blue);
  if (c && c.typename === 'GrayColor') return 'g' + Math.round(c.gray);
  return 'x';
}

while (app.documents.length > 0) { app.activeDocument.close(SaveOptions.DONOTSAVECHANGES); }
var doc = app.open(new File(SRC));

// 1) 既存テキストフレームの属性を収集
var items = [];
for (var i = 0; i < doc.textFrames.length; i++) {
  var tf = doc.textFrames[i];
  if (tf.contents === '') continue;
  var ca0 = tf.textRange.characterAttributes;
  items.push({ tf: tf, text: tf.contents, left: tf.left, top: tf.top, width: tf.width,
               size: ca0.size, font: ca0.textFont, color: ca0.fillColor, ckey: colorKey(ca0.fillColor) });
}
var before = items.length;

// 2) 行（top）・サイズ・色でグルーピング
var groups = {};
for (var i = 0; i < items.length; i++) {
  var it = items[i];
  var key = Math.round(it.top * 2) / 2 + '|' + Math.round(it.size * 2) / 2 + '|' + it.ckey;
  if (!groups[key]) groups[key] = [];
  groups[key].push(it);
}

var log = [], merged = 0;
for (var k in groups) {
  var g = groups[k];
  g.sort(function (a, b) { return a.left - b.left; });

  // 3) x順に走査し、別スタイルの要素を挟んだところで塊を分割する
  var blocks = [], cur = [g[0]];
  for (var i = 1; i < g.length; i++) {
    var prev = cur[cur.length - 1];
    if (g[i].left - (prev.left + prev.width) > g[i].size * 0.5) { blocks.push(cur); cur = [g[i]]; }
    else cur.push(g[i]);
  }
  blocks.push(cur);

  for (var b = 0; b < blocks.length; b++) {
    var blk = blocks[b];
    if (blk.length < 2) continue;

    var str = '';
    for (var i = 0; i < blk.length; i++) {
      if (i > 0 && (blk[i].left - (blk[i - 1].left + blk[i - 1].width)) > blk[i].size * 0.18) str += ' ';
      str += blk[i].text;
    }
    var lastIt = blk[blk.length - 1];
    var target = (lastIt.left + lastIt.width) - blk[0].left;   // 元の塊の実幅

    var nf = doc.textFrames.add();
    nf.contents = str;
    var ca = nf.textRange.characterAttributes;
    ca.textFont = blk[0].font;
    ca.size = blk[0].size;
    ca.fillColor = blk[0].color;
    try { ca.autoKernType = AutoKernType.NOAUTOKERN; } catch (e) {}
    try { ca.tsume = 0; } catch (e) {}
    ca.tracking = trackingFor(blk[0].size);          // CSSのletter-spacingを復元
    try {
      var pa = nf.paragraphs[0].paragraphAttributes;
      try { pa.mojiKumi = MojiKumiType.NOMOJIKUMI; } catch (e1) {}
      try { pa.mojiKumiName = 'なし'; } catch (e1) {}
    } catch (e) {}

    // 約物はIllustratorが半角に詰めるため、その分の送りを個別に戻す
    for (var ci = 0; ci < str.length; ci++) {
      var ch = str.charAt(ci);
      if (ch === '、' || ch === '。') {
        try { nf.characters[ci].characterAttributes.tracking = trackingFor(blk[0].size) + 500; } catch (e) {}
      }
    }
    nf.position = [blk[0].left, blk[0].top];

    // 4) 残った幅の誤差を吸収する
    if (str.length === 2) {
      // 2文字はトラッキングだと隙間が1箇所に集中するので、字幅で調整する
      var r2 = nf.width / target;
      if (r2 < 0.999 && r2 > 0.88) {
        try { ca.horizontalScale = Math.round(100 / r2); } catch (e) {}
        nf.position = [blk[0].left, blk[0].top];
      }
    } else if (str.length >= 3) {
      var ratio = nf.width / target;
      if (ratio < 0.97 || ratio > 1.03) {
        var add = ((target - nf.width) / str.length) / blk[0].size * 1000;
        try { ca.tracking = Math.round(ca.tracking + add); } catch (e) {}
        for (var ci2 = 0; ci2 < str.length; ci2++) {
          var c2 = str.charAt(ci2);
          if (c2 === '、' || c2 === '。') {
            try { nf.characters[ci2].characterAttributes.tracking = Math.round(trackingFor(blk[0].size) + add + 500); } catch (e) {}
          }
        }
        nf.position = [blk[0].left, blk[0].top];
      }
    }

    log.push(str.substring(0, 7) + ' size=' + Math.round(blk[0].size) +
             ' tr=' + ca.tracking + ' w/target=' + (nf.width / target).toFixed(3));
    for (var i = 0; i < blk.length; i++) blk[i].tf.remove();
    merged++;
  }
}

var opt = new IllustratorSaveOptions();
opt.pdfCompatible = true;
doc.saveAs(new File(DST), opt);

var res = 'before=' + before + ' merged=' + merged + ' after=' + doc.textFrames.length +
          ' path=' + doc.pathItems.length + ' raster=' + doc.rasterItems.length + '\n' + log.join('\n');
doc.close(SaveOptions.DONOTSAVECHANGES);
res;
