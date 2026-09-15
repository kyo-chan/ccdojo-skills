# ccdojo-skills

[ccdojo](https://ccdojo.com)（Claude Code 学習ポータル）が読者に配る、Claude Code のプラグインです。
中身は文章のファイルと、画像・HTML 変換用の小さなスクリプト（Python / Illustrator 用 JSX）だけで、フックは入っていません。

## 入れ方

Claude Code の中で、2行打ちます。

```
/plugin marketplace add kyo-chan/ccdojo-skills
/plugin install ccdojo@ccdojo-skills
```

範囲を聞かれたら User scope を選びます。
手順の解説は [ccdojo の記事](https://ccdojo.com/docs/install-a-skill)にあります。

## 入っているもの

| 種類 | 名前 | 何をするか |
|---|---|---|
| スキル | `/ccdojo:team-setup` | 業務を聞き取って、Claude Code 上にチーム一式を作る（部門ごとのフォルダと CLAUDE.md まで） |
| スキル | `/ccdojo:team-builder` | あるチームを呼んで、同じ資料を同時に見てもらい、結果をまとめる |
| スキル | `/ccdojo:writing` | 読者に出す日本語の検品基準。英語臭5点・一文検品3点・タイトルの約束。書く前と書いたあとに通す |
| スキル | `/ccdojo:writing-review` | 書き終えた文章を、上の基準で1ルール1エージェントに並列に読ませ、違反箇所をルール別に報告する（直しはしない） |
| スキル | `/ccdojo:image-to-html` | ポスター・チラシ・バナーの画像を、素材抽出と実測座標で HTML/CSS に忠実に再現する。色替えにも対応 |
| スキル | `/ccdojo:html-to-illustrator` | HTML で作ったポスターを、テキスト編集可能な Illustrator の .ai に変換する（macOS + Chrome + Illustrator が必要） |
| 役割 | `ccdojo:proofreader`（校閲役） | 誤字脱字・表記ゆれ・数字の食い違い |
| 役割 | `ccdojo:first-reader`（初見の読み手役） | 前提なしで読んで、分からないところ |
| 役割 | `ccdojo:risk-checker`（慎重役） | 言い切り・約束・個人情報の危うさ |
| 役割 | `ccdojo:decision-maker`（決裁者役） | 判断に要る情報が揃っているか |
| 役割 | `ccdojo:style-rule-checker` | `writing-review` が1ルールにつき1体ずつ起動する校閲役。単独では使わない |

役割はどれも読む道具（Read / Grep / Glob）しか持っていないので、ファイルを書き換えられません。

`image-to-html` と `html-to-illustrator` は Python 3（Pillow / numpy）と Google Chrome を使います。
`html-to-illustrator` はさらに Adobe Illustrator が入った macOS でだけ動きます。
どちらも手順とつまずきどころを SKILL.md に書いてあるので、環境がなくても読み物として使えます。

## 外し方

```
/plugin uninstall ccdojo@ccdojo-skills
```

## 更新の出し方（管理者向け）

1. `plugins/ccdojo/` の中身を直す
2. `.claude-plugin/marketplace.json` と `plugins/ccdojo/.claude-plugin/plugin.json` の `version` を上げる（上げないと読者に届かない）
3. `claude plugin validate plugins/ccdojo` を通す
4. GitHub の `main` に push する

読者側は `/plugin marketplace update ccdojo-skills` で取り込めます。

## ライセンス

MIT。team-builder は [Everything Claude Code](https://github.com/affaan-m/everything-claude-code)（MIT）由来です。詳細は `LICENSE`。
