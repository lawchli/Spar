# Spar

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform: Android](https://img.shields.io/badge/platform-Android-3DDC84?logo=android&logoColor=white)](#動作条件)
[![Status: prototype](https://img.shields.io/badge/status-prototype-orange.svg)](#todo)

[English](README.md) | [简体中文](README.zh-CN.md) | **日本語**

Spar は、5 極イヤホンジャックを備えた Android スマートフォン向けのステレオ・ライン入力アダプターです。シンセサイザーやユーロラックなどのステレオ・ライン信号を、USB オーディオインターフェースを使わず端末内蔵のオーディオコーデックで録音できます。録音中もヘッドホン出力でモニターできます。

標準的な 4 極（CTIA/OMTP）ジャックにはマイク入力が 1 系統しかないため、既存のライン入力アダプターはモノラルに限られます。5 極ジャックには 2 つ目のマイク接点があり、Spar は左右のチャンネルをこの 2 系統の入力にそれぞれ接続します。

**開発・テスト環境：** Sony Xperia XZ1 Compact、LineageOS 23.2（Android 16）、root 化済み。

## 特長

- イヤホンジャック経由のステレオ・ライン入力、USB オーディオインターフェース不要
- 低遅延モニター：入力信号を端末のオーディオコーデック内部でヘッドホンに返すため、Android やアプリを経由しない
- 抵抗 4 本だけのパッシブ入力回路。Spar 基板のほか、ブレッドボードでも組める

## 性能

ブレッドボードの試作品と Korg NTS-1 による実測値：

| 項目 | 値 |
|---|---|
| チャンネル | 2（ステレオ）、ヘッドホンモニターと同時使用可 |
| 左右分離 | 40 dB 以上 |
| S/N 比 | 約 65 dB |
| ADC ゲイン | 12（範囲 0–20、1 段 1.5 dB） |
| NTS-1 最大音量時のピーク | 約 −13 dBFS |
| 入力回路（各チャンネル） | 直列 10 kΩ、対グラウンド 2.2 kΩ |

完成基板の測定結果（THD+N、ダイナミックレンジ、周波数特性）は [`measurements`](../../tree/measurements) ブランチで公開予定です。

## 動作条件

- 5 極イヤホンジャックを備え、オーディオコーデックがステレオ（binaural）録音パスを持つ Android スマートフォン
- root 権限（ミキサー設定と録音ツールに必要）
- 基板を自作する場合ははんだ付け用の工具

## リポジトリ構成

プロジェクトの各パートはそれぞれのブランチで開発し、`main` にはリリース済みのスナップショットを置いています。

| ブランチ | 内容 |
|---|---|
| [`software`](../../tree/software) | スマートフォン側のツール、スクリプト、設定手順 |
| [`pcb`](../../tree/pcb) | 基板：回路図、レイアウト、製造データ、BOM |
| [`enclosure`](../../tree/enclosure) | 3D プリントケース |
| [`measurements`](../../tree/measurements) | 完成品の測定結果 |

## TODO

- [ ] PCB Rev D の製造と組み立て
- [ ] Rev D 用ケース
- [ ] 完成品の測定（THD+N、ダイナミックレンジ、周波数特性）
- [ ] 完成基板でハウリングしない安全なモニターゲインの確認
- [ ] スマートフォン側のワンステップ設定（Magisk モジュール：起動時サービス、ミキサー設定、録音操作）
- [ ] 他の 5 極ジャック搭載端末でのテスト

## ライセンス

[MIT](LICENSE) © LawChli。サードパーティのコードはそれぞれのライセンスに従います（TinyALSA：BSD-3-Clause）。
