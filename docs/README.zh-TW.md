[English](../README.md) | [简体中文](README.zh-CN.md) | **繁體中文** | [日本語](README.ja.md) | [한국어](README.ko.md)

<div align="center">
  <img src="../parker_label_app/assets/app-icon.png" width="144" alt="ParkerLabel 圖示">
  <h1>ParkerLabel</h1>
    <p><strong>完全使用 CPU 執行，無需 GPU。</strong></p>
  <p>一款輕量、精緻的 <strong>AI 輔助</strong>互動式標註工具，適用於物件偵測和實例分割。</p>
  <p>在 Apple M5 Pro 和 Intel Core i9-14900KF CPU 上，每次互動式遮罩解碼器推論耗時約 <strong>20 毫秒</strong>。</p>
  <p>
    <a href="https://github.com/Parker-Lyu/ParkerLabel/releases"><img src="https://img.shields.io/badge/Releases-GitHub-blue?style=flat-square" alt="GitHub 發布版本"></a>
    <a href="../builds/SOP.md"><img src="https://img.shields.io/badge/build%20target-macOS%20arm64-black?style=flat-square&amp;logo=apple" alt="macOS arm64 建置目標"></a>
    <a href="../builds/SOP.md"><img src="https://img.shields.io/badge/build%20target-Windows%20x64-0078D4?style=flat-square&amp;logo=windows" alt="Windows x64 建置目標"></a>
    <a href="../LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0--only-green?style=flat-square" alt="GPL-3.0-only 授權條款"></a>
  </p>
  <img src="../docs/images/parkerlabel-ui-demo.gif" width="960" alt="ParkerLabel 互動式標註示範">
</div>


## 🎬 專案介紹

<p align="center">
  <a href="https://www.youtube.com/watch?v=B1eu6EKgbUI"><img src="../docs/images/parkerlabel-video-youtube.jpg" width="43%" alt="在 YouTube 觀看 ParkerLabel 介紹"></a>&emsp;&emsp;
  <a href="https://www.bilibili.com/video/BV1omps6dEqP"><img src="../docs/images/parkerlabel-video-bilibili.jpg" width="43%" alt="在嗶哩嗶哩觀看 ParkerLabel 介紹"></a>
</p>

## 執行

### 使用可攜版

1. 從 [GitHub Releases](https://github.com/Parker-Lyu/ParkerLabel/releases) 或[百度網盤](https://pan.baidu.com/s/1mGc8w11JHbTnERI_yztVWA?pwd=md7r)（提取碼：`md7r`）下載適用於你所用平台的已發布應用程式套件。名稱為 `models-*` 的發布版本包含 ONNX 模型，並非應用程式套件。

1. 在 macOS 和 Windows 上，開啟程式前需要將解壓縮後的整個 ParkerLabel 資料夾移至可寫入的位置。

1. macOS 套件使用 ad-hoc 簽署，但未經 Apple 公證，因此首次啟動可能遭 macOS 阻擋。嘗試開啟應用程式一次後，進入**系統設定 → 隱私權與安全性**，向下捲動至安全性區段，選擇**強制打開（Open Anyway）**。

1. 在 Windows 上，首次啟動時 Microsoft Defender SmartScreen 可能顯示 **Windows 已保護您的電腦（Windows protected your PC）**。按一下**其他資訊（More info）**，再按一下**仍要執行（Run anyway）**。

<p align="center">
  <a href="../docs/images/portable-macos-open-1.png"><img src="../docs/images/portable-macos-open-1.png" width="35.2%" alt="macOS 首次啟動提示：按一下完成"></a>
  <a href="../docs/images/portable-macos-open-2.png"><img src="../docs/images/portable-macos-open-2.png" width="45%" alt="macOS 隱私權與安全性：按一下強制打開"></a><br>
  <a href="../docs/images/portable-windows-open-1.png"><img src="../docs/images/portable-windows-open-1.png" width="45%" alt="Windows SmartScreen：按一下其他資訊"></a>
  <a href="../docs/images/portable-windows-open-2.png"><img src="../docs/images/portable-windows-open-2.png" width="45%" alt="Windows SmartScreen：按一下仍要執行"></a>
</p>

僅憑這些警告無法判定 ParkerLabel 是惡意軟體。可攜版透過 GitHub Actions 建置；你可以查看[建置工作流程](../.github/workflows/release.yml)和[建置說明](../builds/SOP.md)。

### 從原始碼執行

若尚未安裝 Conda 發行版，請先安裝。建議使用 [Miniforge](https://github.com/conda-forge/miniforge)，其他 Conda 發行版也可以。從 [GitHub](https://github.com/Parker-Lyu/ParkerLabel) 或 [Gitee](https://gitee.com/Parker-Lyu/ParkerLabel) 複製專案：

```bash
git clone https://github.com/Parker-Lyu/ParkerLabel.git
```

或：

```bash
git clone https://gitee.com/Parker-Lyu/ParkerLabel.git
```

接著建立 Python 3.11 環境，安裝相依套件並啟動 ParkerLabel：

```bash
cd ParkerLabel
conda create -n parker-label -c conda-forge python=3.11 -y
conda activate parker-label
python -m pip install -r requirements.txt
python main.py
```

ParkerLabel 會自動驗證 ONNX 模型，並將缺少的模型下載至 `pretrain/`。

## 功能概覽

ParkerLabel 支援中文（简体）、中文（繁體）、English、日本語、한국어、Deutsch、Français、Italiano 和 Español。透過**設定 → 介面語言 / Language**切換介面語言，透過**設定 → 操作提示**控制情境提示。

透過**設定 → 快捷鍵設定…**檢視、修改、清除或還原快捷鍵。AI、手動和檢視模式的預設快捷鍵分別為 `Q`、`W` 和 `E`。在 AI 模式下，正負點擊引導 MobileSAM 為目前目標產生遮罩。影像工具列使用 `S` 切換疊加檢視中的 AI 提示點顯示，使用 `C` 切換品質檢查。儲存後的快捷鍵立即生效，並在下次啟動時保留。

### 類別設定

ParkerLabel 內建包含 80 個標準 COCO 物件偵測類別的唯讀設定。使用者可以建立空白類別設定，或複製任意現有設定（包括內建 COCO 設定）來建立新版本。已儲存的設定無法修改；後續修改需要將設定複製為另一個版本。使用者建立的設定儲存於所選的 `configs/categories/` 目錄中。

每份標註透過 UUID 和 SHA-256 摘要綁定至一個類別設定。若目前啟用的是其他設定，ParkerLabel 會提示切換至所需設定。若該設定無法取得、未通過完整性驗證，或使用者拒絕切換，標註將以唯讀方式開啟。

可攜式設定（包括啟動時選擇的類別設定）儲存於 `configs/settings.ini`。應用程式日誌為 `configs/app.log`；每次啟動時清空，執行期間最多保留兩個各 1 MB 的日誌檔案。

### 標註檔案

每張原始影像對應三個儲存在相同目錄的檔案：

- `.npy` 儲存可重複使用的影像嵌入。
- `.json` 儲存每個實例的類別、邊界框、面積，以及原始影像解析度下的未壓縮 COCO RLE。
- `.mask.png` 儲存原始影像解析度下的平面化彩色預覽。實例重疊時，後面的實例顯示在上層。實例遮罩以 JSON 中的資料為準。

每張影像的 JSON 使用 COCO 標註欄位，但並非完整的 COCO 資料集檔案。匯出完整 COCO 資料集需要在一個資料集 JSON 中包含頂層 `images`、`annotations` 和 `categories` 陣列。

#### JSON 欄位

- `format` 識別本地標註格式，目前為 `parker-label-instance-v2`。
- `category_config_uuid` 識別與標註綁定的確切類別設定。
- `category_config_sha256` 記錄該類別設定的摘要，用於偵測非預期的變更。
- `image` 記錄影像的 `id`、檔名、寬度和高度。
- `annotations` 為每個實例儲存一筆記錄。
- `id` 是影像檔案內的實例識別碼。
- `image_id` 將實例連結至影像記錄。
- `category_id` 參照綁定的類別設定中的一個類別。
- `category_name` 保留可讀的類別名稱。
- `color_id` 控制顯示和預覽色彩。
- `bbox` 以原始影像像素為單位儲存 `[x, y, width, height]`。
- `area` 儲存原始影像解析度下的實例像素面積。
- `iscrowd` 遵循 COCO 的群體旗標慣例。
- `segmentation` 將獨立的實例遮罩儲存為未壓縮 COCO RLE。

## 重新產生 ONNX 模型

**相依套件：**依照[適用於你所用平台的 PyTorch 安裝說明](https://pytorch.org/get-started/locally/)安裝 `torch` 和 `torchvision`，再執行 `python -m pip install timm onnx onnxruntime==1.29.0`。已驗證版本：torch 2.13.0、torchvision 0.28.0、timm 1.0.19、onnx 1.22.0 和 onnxruntime 1.29.0。

**檢查點：**建立 `pretrain/`，再下載官方 [MobileSAM `mobile_sam.pt`](https://github.com/ChaoningZhang/MobileSAM/blob/master/weights/mobile_sam.pt) 至 `pretrain/mobile_sam.pt`。兩個匯出命令只需要這一份權重，無需單獨的 TinyViT 或 SAM 檢查點。

**匯出：**在儲存庫根目錄執行：

```bash
python -m mobile_sam.export_mobilesam_encoder --checkpoint pretrain/mobile_sam.pt --output pretrain/encoder.onnx
python -m mobile_sam.export_mobilesam_decoder --checkpoint pretrain/mobile_sam.pt --model-type vit_t --output pretrain/decoder.onnx
```

這些命令用於開發時重新產生 ONNX 模型。ParkerLabel 啟動時會根據 `model-bundle.json` 檢查模型的大小和 SHA-256 雜湊，並以已發布模型替換不相符的檔案。自訂匯出需要相符的模型清單。執行應用程式不需要 `mobile_sam.pt` 或匯出相依套件。`pretrain/` 中的模型檔案不納入 Git。

## 授權條款

ParkerLabel 的原創程式碼（包括 `mobile_sam/export_mobilesam_encoder.py`）採用 [GPL-3.0-only](../LICENSE) 授權條款。

`mobile_sam/` 中的第三方程式碼保留各自的授權條款：[MobileSAM](https://github.com/ChaoningZhang/MobileSAM) 和 [Segment Anything](https://github.com/facebookresearch/segment-anything) 使用 Apache License 2.0，TinyViT 程式碼包含 Microsoft 的 MIT 授權聲明。授權全文與署名資訊見 [`mobile_sam/LICENSE`](../mobile_sam/LICENSE)、[`mobile_sam/TINYVIT_LICENSE`](../mobile_sam/TINYVIT_LICENSE) 和 [`mobile_sam/THIRD_PARTY.md`](../mobile_sam/THIRD_PARTY.md)。

GUI 使用的 PyQt5 和 Qt 遵循各自的授權條款。最終發行套件的具體聲明、對應原始碼取得說明和 Qt 替換說明維護於 [`third_party_licenses/`](../third_party_licenses/)。模型來源與匯出溯源記錄見 [`docs/model-provenance.md`](../docs/model-provenance.md)，發布稽核流程見 [`docs/release-licenses.md`](../docs/release-licenses.md)。

## 致謝

ParkerLabel 的 AI 輔助分割工作流程建立於以下專案的成果之上：

- [MobileSAM](https://github.com/ChaoningZhang/MobileSAM)：專為高效率推論設計的輕量級 Segment Anything 模型。
- [Segment Anything](https://github.com/facebookresearch/segment-anything)：由 Meta AI 開發的原始分割模型與框架。

感謝這兩個專案的作者和貢獻者公開分享他們的成果。
