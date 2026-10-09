[English](../README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | **日本語** | [한국어](README.ko.md)

<div align="center">
  <img src="../parker_label_app/assets/app-icon.png" width="144" alt="ParkerLabel アイコン">
  <h1>ParkerLabel</h1>
    <p><strong>CPU のみで動作し、GPU は不要です。</strong></p>
  <p>物体検出とインスタンスセグメンテーションのための、軽量で洗練された <strong>AI 支援</strong>対話型アノテーションツールです。</p>
  <p>Apple M5 Pro と Intel Core i9-14900KF の CPU では、対話型マスクデコーダーの推論 1 回にかかる時間は約 <strong>20 ミリ秒</strong>です。</p>
  <p>
    <a href="https://github.com/Parker-Lyu/ParkerLabel/releases"><img src="https://img.shields.io/badge/Releases-GitHub-blue?style=flat-square" alt="GitHub リリース"></a>
    <a href="../builds/SOP.md"><img src="https://img.shields.io/badge/build%20target-macOS%20arm64-black?style=flat-square&amp;logo=apple" alt="macOS arm64 ビルド対象"></a>
    <a href="../builds/SOP.md"><img src="https://img.shields.io/badge/build%20target-Windows%20x64-0078D4?style=flat-square&amp;logo=windows" alt="Windows x64 ビルド対象"></a>
    <a href="../LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0--only-green?style=flat-square" alt="GPL-3.0-only ライセンス"></a>
  </p>
  <img src="../docs/images/parkerlabel-ui-demo.gif" width="960" alt="ParkerLabel の対話型アノテーションデモ">
</div>


## 🎬 プロジェクト紹介

<p align="center">
  <a href="https://www.youtube.com/watch?v=B1eu6EKgbUI"><img src="../docs/images/parkerlabel-video-youtube.jpg" width="43%" alt="YouTube で ParkerLabel の紹介を見る"></a>&emsp;&emsp;
  <a href="https://www.bilibili.com/video/BV1omps6dEqP"><img src="../docs/images/parkerlabel-video-bilibili.jpg" width="43%" alt="Bilibili で ParkerLabel の紹介を見る"></a>
</p>

## 実行方法

### ポータブル版を使う

1. [GitHub Releases](https://github.com/Parker-Lyu/ParkerLabel/releases) または [Baidu Netdisk](https://pan.baidu.com/s/1mGc8w11JHbTnERI_yztVWA?pwd=md7r)（取得コード：`md7r`）から、お使いのプラットフォーム向けに公開されているアプリケーションパッケージをダウンロードします。`models-*` という名前のリリースには ONNX モデルが含まれており、アプリケーションパッケージではありません。

1. macOS と Windows では、起動する前に、展開した ParkerLabel フォルダー全体を書き込み可能な場所に移動してください。

1. macOS パッケージには ad-hoc 署名が付いていますが、Apple の公証は受けていないため、初回起動時に macOS によってブロックされる場合があります。一度アプリの起動を試みた後、**システム設定 → プライバシーとセキュリティ**を開き、セキュリティの項目までスクロールして、**このまま開く（Open Anyway）**を選択します。

1. Windows では、初回起動時に Microsoft Defender SmartScreen が **Windows によって PC が保護されました（Windows protected your PC）**と表示する場合があります。**詳細情報（More info）**をクリックし、続けて**実行（Run anyway）**をクリックします。

<p align="center">
  <a href="../docs/images/portable-macos-open-1.png"><img src="../docs/images/portable-macos-open-1.png" width="35.2%" alt="macOS の初回起動時の警告：完了をクリック"></a>
  <a href="../docs/images/portable-macos-open-2.png"><img src="../docs/images/portable-macos-open-2.png" width="45%" alt="macOS のプライバシーとセキュリティ：このまま開くをクリック"></a><br>
  <a href="../docs/images/portable-windows-open-1.png"><img src="../docs/images/portable-windows-open-1.png" width="45%" alt="Windows SmartScreen：詳細情報をクリック"></a>
  <a href="../docs/images/portable-windows-open-2.png"><img src="../docs/images/portable-windows-open-2.png" width="45%" alt="Windows SmartScreen：実行をクリック"></a>
</p>

これらの警告だけで ParkerLabel が悪意のあるソフトウェアだとは判断できません。ポータブル版は GitHub Actions でビルドされています。[ビルドワークフロー](../.github/workflows/release.yml)と[ビルド手順](../builds/SOP.md)を確認できます。

### ソースコードから実行する

Conda ディストリビューションが未インストールの場合は、先にインストールしてください。[Miniforge](https://github.com/conda-forge/miniforge) を推奨しますが、他の Conda ディストリビューションも利用できます。[GitHub](https://github.com/Parker-Lyu/ParkerLabel) または [Gitee](https://gitee.com/Parker-Lyu/ParkerLabel) からプロジェクトをクローンします。

```bash
git clone https://github.com/Parker-Lyu/ParkerLabel.git
```

または：

```bash
git clone https://gitee.com/Parker-Lyu/ParkerLabel.git
```

次に Python 3.11 環境を作成し、依存パッケージをインストールして ParkerLabel を起動します。

```bash
cd ParkerLabel
conda create -n parker-label -c conda-forge python=3.11 -y
conda activate parker-label
python -m pip install -r requirements.txt
python main.py
```

ParkerLabel は ONNX モデルを自動で検証し、不足しているモデルを `pretrain/` にダウンロードします。

## 機能概要

ParkerLabel は、中文（简体）、中文（繁體）、English、日本語、한국어、Deutsch、Français、Italiano、Español に対応しています。**設定 → 表示言語**でインターフェースの言語を変更し、**設定 → 操作ヒント**で操作に応じたヒントの表示を切り替えられます。

**設定 → ショートカット設定…**でキー割り当ての確認、変更、解除、初期設定への復元ができます。AI、手動、確認モードの既定のショートカットは、それぞれ `Q`、`W`、`E` です。AI モードでは、正負のクリックによって MobileSAM に指示し、現在の対象のマスクを生成します。画像ツールバーでは、`S` でオーバーレイ表示の AI プロンプト点の表示を切り替え、`C` で品質チェックを切り替えます。保存したキー割り当てはすぐに反映され、次回起動時にも維持されます。

### カテゴリ設定

ParkerLabel には、COCO の標準的な物体検出カテゴリ 80 個を含む読み取り専用の設定が付属しています。空のカテゴリ設定を作成するか、既存の設定（内蔵の COCO 設定を含む）をコピーして新しいバージョンを作成できます。保存済みの設定は変更できません。さらに変更する場合は、設定を別のバージョンとしてコピーします。ユーザーが作成した設定は、選択した `configs/categories/` ディレクトリに保存されます。

各アノテーションは、UUID と SHA-256 ダイジェストによってカテゴリ設定に紐付けられます。他の設定が有効になっている場合、ParkerLabel は必要な設定への切り替えを案内します。その設定が利用できない場合、整合性チェックに失敗した場合、または切り替えを拒否した場合、アノテーションは読み取り専用で開かれます。

起動時のカテゴリ選択を含むポータブル設定は、`configs/settings.ini` に保存されます。アプリケーションログは `configs/app.log` です。起動するたびに消去され、実行中は各 1 MB のログファイルを最大 2 個保持します。

### アノテーションファイル

元画像ごとに、同じディレクトリに次の 3 つのファイルを保存します。

- `.npy` は、再利用可能な画像埋め込みを保存します。
- `.json` は、各インスタンスのカテゴリ、バウンディングボックス、面積、および元画像の解像度での非圧縮 COCO RLE を保存します。
- `.mask.png` は、元画像の解像度でカラーの合成プレビューを保存します。インスタンスが重なる場合、後のインスタンスが上に表示されます。インスタンスマスクの正本は JSON 内のデータです。

画像ごとの JSON は COCO アノテーションのフィールドを使用しますが、完全な COCO データセットファイルではありません。完全な COCO データセットをエクスポートするには、1 つのデータセット JSON にトップレベルの `images`、`annotations`、`categories` 配列が必要です。

#### JSON フィールド

- `format` はローカルのアノテーション形式を識別します。現在の値は `parker-label-instance-v2` です。
- `category_config_uuid` は、アノテーションに紐付いた特定のカテゴリ設定を識別します。
- `category_config_sha256` は、意図しない変更を検出するため、カテゴリ設定のダイジェストを記録します。
- `image` は画像の `id`、ファイル名、幅、高さを記録します。
- `annotations` は、インスタンスごとに 1 件のレコードを格納します。
- `id` は、画像ファイル内のインスタンス識別子です。
- `image_id` は、インスタンスを画像レコードに関連付けます。
- `category_id` は、紐付いたカテゴリ設定内のカテゴリを参照します。
- `category_name` は、読みやすいカテゴリ名を保持します。
- `color_id` は、表示とプレビューの色を制御します。
- `bbox` は、元画像のピクセル単位で `[x, y, width, height]` を保存します。
- `area` は、元画像の解像度でのインスタンスのピクセル面積を保存します。
- `iscrowd` は、COCO の群衆フラグの規則に従います。
- `segmentation` は、独立したインスタンスマスクを非圧縮 COCO RLE として保存します。

## ONNX モデルの再生成

**依存パッケージ：**[お使いのプラットフォーム向けの PyTorch インストール手順](https://pytorch.org/get-started/locally/)に従って `torch` と `torchvision` をインストールし、`python -m pip install timm onnx onnxruntime==1.29.0` を実行します。検証済みのバージョン：torch 2.13.0、torchvision 0.28.0、timm 1.0.19、onnx 1.22.0、onnxruntime 1.29.0。

**チェックポイント：**`pretrain/` を作成し、公式の [MobileSAM `mobile_sam.pt`](https://github.com/ChaoningZhang/MobileSAM/blob/master/weights/mobile_sam.pt) を `pretrain/mobile_sam.pt` にダウンロードします。両方のエクスポートで必要な重みはこの 1 ファイルだけです。TinyViT や SAM の別のチェックポイントは不要です。

**エクスポート：**リポジトリのルートで次のコマンドを実行します。

```bash
python -m mobile_sam.export_mobilesam_encoder --checkpoint pretrain/mobile_sam.pt --output pretrain/encoder.onnx
python -m mobile_sam.export_mobilesam_decoder --checkpoint pretrain/mobile_sam.pt --model-type vit_t --output pretrain/decoder.onnx
```

これらのコマンドは、開発用の ONNX モデルを再生成します。起動時に ParkerLabel は `model-bundle.json` に照らしてモデルのサイズと SHA-256 ハッシュを確認し、一致しないファイルを公開済みのモデルに置き換えます。独自にエクスポートしたモデルには、それに一致するモデルマニフェストが必要です。実行時に `mobile_sam.pt` やエクスポート用の依存パッケージは不要です。`pretrain/` 内のモデルファイルは Git の管理対象外です。

## ライセンス

`mobile_sam/export_mobilesam_encoder.py` を含む ParkerLabel の独自コードは、[GPL-3.0-only](../LICENSE) の下で提供されています。

`mobile_sam/` 内のサードパーティコードには、それぞれのライセンスが適用されます。[MobileSAM](https://github.com/ChaoningZhang/MobileSAM) と [Segment Anything](https://github.com/facebookresearch/segment-anything) は Apache License 2.0 を使用し、TinyViT のコードには Microsoft の MIT ライセンス表記が含まれています。ライセンス全文と帰属情報は、[`mobile_sam/LICENSE`](../mobile_sam/LICENSE)、[`mobile_sam/TINYVIT_LICENSE`](../mobile_sam/TINYVIT_LICENSE)、[`mobile_sam/THIRD_PARTY.md`](../mobile_sam/THIRD_PARTY.md) を参照してください。

GUI で使用する PyQt5 と Qt には、それぞれのライセンスが適用されます。最終配布パッケージの具体的な通知、対応するソースコードの取得手順、および Qt の置き換え手順は [`third_party_licenses/`](../third_party_licenses/) にまとめられています。モデルのソースとエクスポートの来歴は [`docs/model-provenance.md`](../docs/model-provenance.md)、リリースの監査手順は [`docs/release-licenses.md`](../docs/release-licenses.md) に記載されています。

## 謝辞

ParkerLabel の AI 支援セグメンテーションのワークフローは、次のプロジェクトの成果に基づいています。

- [MobileSAM](https://github.com/ChaoningZhang/MobileSAM)：計算資源を効率よく利用して推論するために設計された、軽量な Segment Anything モデル。
- [Segment Anything](https://github.com/facebookresearch/segment-anything)：Meta AI が開発した、元となるセグメンテーションモデルとフレームワーク。

両プロジェクトの成果を公開してくださった著者と貢献者の皆様に感謝します。
