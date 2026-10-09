[English](../README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | **한국어**

<div align="center">
  <img src="../parker_label_app/assets/app-icon.png" width="144" alt="ParkerLabel 아이콘">
  <h1>ParkerLabel</h1>
    <p><strong>CPU만으로 실행되며 GPU가 필요하지 않습니다.</strong></p>
  <p>객체 탐지와 인스턴스 분할을 위한 가볍고 세련된 <strong>AI 지원</strong>대화형 주석 도구입니다.</p>
  <p>Apple M5 Pro 및 Intel Core i9-14900KF CPU에서 대화형 마스크 디코더의 추론 시간은 회당 약 <strong>20밀리초</strong>입니다.</p>
  <p>
    <a href="https://github.com/Parker-Lyu/ParkerLabel/releases"><img src="https://img.shields.io/badge/Releases-GitHub-blue?style=flat-square" alt="GitHub 릴리스"></a>
    <a href="../builds/SOP.md"><img src="https://img.shields.io/badge/build%20target-macOS%20arm64-black?style=flat-square&amp;logo=apple" alt="macOS arm64 빌드 대상"></a>
    <a href="../builds/SOP.md"><img src="https://img.shields.io/badge/build%20target-Windows%20x64-0078D4?style=flat-square&amp;logo=windows" alt="Windows x64 빌드 대상"></a>
    <a href="../LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0--only-green?style=flat-square" alt="GPL-3.0-only 라이선스"></a>
  </p>
  <img src="../docs/images/parkerlabel-ui-demo.gif" width="960" alt="ParkerLabel 대화형 주석 데모">
</div>


## 🎬 프로젝트 소개

<p align="center">
  <a href="https://www.youtube.com/watch?v=B1eu6EKgbUI"><img src="../docs/images/parkerlabel-video-youtube.jpg" width="43%" alt="YouTube에서 ParkerLabel 소개 보기"></a>&emsp;&emsp;
  <a href="https://www.bilibili.com/video/BV1omps6dEqP"><img src="../docs/images/parkerlabel-video-bilibili.jpg" width="43%" alt="Bilibili에서 ParkerLabel 소개 보기"></a>
</p>

## 실행 방법

### 포터블 버전 사용

1. [GitHub Releases](https://github.com/Parker-Lyu/ParkerLabel/releases) 또는 [Baidu Netdisk](https://pan.baidu.com/s/1mGc8w11JHbTnERI_yztVWA?pwd=md7r)(다운로드 코드: `md7r`)에서 사용 중인 플랫폼에 맞는 공개된 애플리케이션 패키지를 다운로드하세요. 이름이 `models-*`인 릴리스에는 ONNX 모델이 들어 있으며, 애플리케이션 패키지가 아닙니다.

1. macOS와 Windows에서는 프로그램을 열기 전에 압축을 푼 ParkerLabel 폴더 전체를 쓰기 가능한 위치로 옮겨야 합니다.

1. macOS 패키지에는 ad-hoc 서명이 적용되어 있지만 Apple의 공증을 받지 않았으므로, macOS가 첫 실행을 차단할 수 있습니다. 앱 실행을 한 번 시도한 뒤 **시스템 설정 → 개인정보 보호 및 보안**을 열고 보안 항목으로 스크롤하여 **그래도 열기(Open Anyway)**를 선택하세요.

1. Windows에서는 첫 실행 시 Microsoft Defender SmartScreen이 **Windows의 PC 보호(Windows protected your PC)** 메시지를 표시할 수 있습니다. **추가 정보(More info)**를 클릭한 다음 **실행(Run anyway)**을 클릭하세요.

<p align="center">
  <a href="../docs/images/portable-macos-open-1.png"><img src="../docs/images/portable-macos-open-1.png" width="35.2%" alt="macOS 첫 실행 경고: 완료 클릭"></a>
  <a href="../docs/images/portable-macos-open-2.png"><img src="../docs/images/portable-macos-open-2.png" width="45%" alt="macOS 개인정보 보호 및 보안: 그래도 열기 클릭"></a><br>
  <a href="../docs/images/portable-windows-open-1.png"><img src="../docs/images/portable-windows-open-1.png" width="45%" alt="Windows SmartScreen: 추가 정보 클릭"></a>
  <a href="../docs/images/portable-windows-open-2.png"><img src="../docs/images/portable-windows-open-2.png" width="45%" alt="Windows SmartScreen: 실행 클릭"></a>
</p>

이러한 경고만으로 ParkerLabel이 악성 소프트웨어라고 판단할 수는 없습니다. 포터블 버전은 GitHub Actions로 빌드됩니다. [빌드 워크플로](../.github/workflows/release.yml)와 [빌드 지침](../builds/SOP.md)을 확인할 수 있습니다.

### 소스 코드에서 실행

Conda 배포판이 설치되어 있지 않다면 먼저 설치하세요. [Miniforge](https://github.com/conda-forge/miniforge)를 권장하지만 다른 Conda 배포판도 사용할 수 있습니다. [GitHub](https://github.com/Parker-Lyu/ParkerLabel) 또는 [Gitee](https://gitee.com/Parker-Lyu/ParkerLabel)에서 프로젝트를 복제하세요.

```bash
git clone https://github.com/Parker-Lyu/ParkerLabel.git
```

또는:

```bash
git clone https://gitee.com/Parker-Lyu/ParkerLabel.git
```

그런 다음 Python 3.11 환경을 만들고 의존성을 설치한 뒤 ParkerLabel을 실행하세요.

```bash
cd ParkerLabel
conda create -n parker-label -c conda-forge python=3.11 -y
conda activate parker-label
python -m pip install -r requirements.txt
python main.py
```

ParkerLabel은 ONNX 모델을 자동으로 검증하고 누락된 모델을 `pretrain/`에 다운로드합니다.

## 기능 개요

ParkerLabel은 中文（简体）, 中文（繁體）, English, 日本語, 한국어, Deutsch, Français, Italiano, Español을 지원합니다. **설정 → 인터페이스 언어**에서 인터페이스 언어를 변경하고, **설정 → 도구 설명**에서 상황별 도움말 표시를 제어할 수 있습니다.

**설정 → 단축키 설정…**에서 키 할당을 확인, 변경, 해제하거나 기본값으로 복원할 수 있습니다. AI, 수동, 조회 모드의 기본 단축키는 각각 `Q`, `W`, `E`입니다. AI 모드에서는 긍정 및 부정 클릭으로 MobileSAM을 안내하여 현재 대상의 마스크를 생성합니다. 이미지 도구 모음에서 `S`는 겹쳐 보기의 AI 프롬프트 지점 표시를 전환하고, `C`는 품질 검사를 전환합니다. 저장한 키 할당은 즉시 적용되며 다음 실행 시에도 유지됩니다.

### 범주 설정

ParkerLabel에는 표준 COCO 객체 탐지 범주 80개를 포함하는 읽기 전용 설정이 내장되어 있습니다. 빈 범주 설정을 만들거나, 내장 COCO 설정을 포함한 기존 설정을 복사하여 새 버전을 만들 수 있습니다. 저장된 설정은 변경할 수 없으며, 추가로 변경하려면 설정을 다른 버전으로 복사해야 합니다. 사용자가 만든 설정은 선택한 `configs/categories/` 디렉터리에 저장됩니다.

각 주석은 UUID와 SHA-256 다이제스트로 범주 설정에 연결됩니다. 다른 설정이 활성화되어 있으면 ParkerLabel이 필요한 설정으로 전환하도록 안내합니다. 해당 설정을 사용할 수 없거나 무결성 검사를 통과하지 못하거나 사용자가 전환을 거부하면 주석은 읽기 전용으로 열립니다.

시작 시 선택한 범주 설정을 포함한 포터블 설정은 `configs/settings.ini`에 저장됩니다. 애플리케이션 로그는 `configs/app.log`입니다. 실행할 때마다 초기화되며, 앱이 실행되는 동안 각각 1 MB인 로그 파일을 최대 2개 유지합니다.

### 주석 파일

각 원본 이미지에 대해 같은 디렉터리에 다음 세 가지 파일이 저장됩니다.

- `.npy`는 재사용 가능한 이미지 임베딩을 저장합니다.
- `.json`은 각 인스턴스의 범주, 경계 상자, 면적과 원본 이미지 해상도의 비압축 COCO RLE를 저장합니다.
- `.mask.png`는 원본 이미지 해상도의 단일 컬러 미리보기를 저장합니다. 인스턴스가 겹치면 뒤에 있는 인스턴스가 위에 표시됩니다. 인스턴스 마스크는 JSON 데이터를 기준으로 합니다.

이미지별 JSON은 COCO 주석 필드를 사용하지만 완전한 COCO 데이터셋 파일은 아닙니다. 완전한 COCO 데이터셋으로 내보내려면 하나의 데이터셋 JSON에 최상위 `images`, `annotations`, `categories` 배열이 있어야 합니다.

#### JSON 필드

- `format`은 로컬 주석 형식을 식별하며, 현재 값은 `parker-label-instance-v2`입니다.
- `category_config_uuid`는 주석에 연결된 정확한 범주 설정을 식별합니다.
- `category_config_sha256`은 예상치 못한 변경을 감지할 수 있도록 범주 설정의 다이제스트를 기록합니다.
- `image`는 이미지의 `id`, 파일 이름, 너비, 높이를 기록합니다.
- `annotations`는 인스턴스당 하나의 레코드를 포함합니다.
- `id`는 이미지 파일 내의 인스턴스 식별자입니다.
- `image_id`는 인스턴스를 이미지 레코드에 연결합니다.
- `category_id`는 연결된 범주 설정의 범주를 참조합니다.
- `category_name`은 읽기 쉬운 범주 이름을 유지합니다.
- `color_id`는 표시 및 미리보기 색상을 제어합니다.
- `bbox`는 원본 이미지 픽셀 단위의 `[x, y, width, height]`를 저장합니다.
- `area`는 원본 이미지 해상도에서 인스턴스의 픽셀 면적을 저장합니다.
- `iscrowd`는 COCO의 군중 플래그 규칙을 따릅니다.
- `segmentation`은 독립적인 인스턴스 마스크를 비압축 COCO RLE로 저장합니다.

## ONNX 모델 다시 생성

**의존성:** [사용 중인 플랫폼에 맞는 PyTorch 설치 지침](https://pytorch.org/get-started/locally/)에 따라 `torch`와 `torchvision`을 설치한 다음 `python -m pip install timm onnx onnxruntime==1.29.0`을 실행하세요. 검증된 버전: torch 2.13.0, torchvision 0.28.0, timm 1.0.19, onnx 1.22.0, onnxruntime 1.29.0.

**체크포인트:** `pretrain/`을 만들고 공식 [MobileSAM `mobile_sam.pt`](https://github.com/ChaoningZhang/MobileSAM/blob/master/weights/mobile_sam.pt)를 `pretrain/mobile_sam.pt`에 다운로드하세요. 두 내보내기 작업에 필요한 가중치는 이 파일 하나뿐이며, 별도의 TinyViT 또는 SAM 체크포인트는 필요하지 않습니다.

**내보내기:** 저장소 루트에서 다음 명령을 실행하세요.

```bash
python -m mobile_sam.export_mobilesam_encoder --checkpoint pretrain/mobile_sam.pt --output pretrain/encoder.onnx
python -m mobile_sam.export_mobilesam_decoder --checkpoint pretrain/mobile_sam.pt --model-type vit_t --output pretrain/decoder.onnx
```

이 명령은 개발용 ONNX 모델을 다시 생성합니다. ParkerLabel은 시작 시 `model-bundle.json`을 기준으로 모델의 크기와 SHA-256 해시를 확인하고, 일치하지 않는 파일을 공개된 모델로 교체합니다. 사용자 정의 모델을 내보내려면 일치하는 모델 매니페스트가 필요합니다. 실행 시에는 `mobile_sam.pt`와 내보내기용 의존성이 필요하지 않습니다. `pretrain/`의 모델 파일은 Git 관리 대상에서 제외됩니다.

## 라이선스

`mobile_sam/export_mobilesam_encoder.py`를 포함한 ParkerLabel의 자체 코드는 [GPL-3.0-only](../LICENSE) 라이선스를 따릅니다.

`mobile_sam/`의 타사 코드는 각각의 라이선스를 유지합니다. [MobileSAM](https://github.com/ChaoningZhang/MobileSAM)과 [Segment Anything](https://github.com/facebookresearch/segment-anything)은 Apache License 2.0을 사용하며, TinyViT 코드에는 Microsoft의 MIT 라이선스 고지가 포함되어 있습니다. 라이선스 전문과 저작자 표기는 [`mobile_sam/LICENSE`](../mobile_sam/LICENSE), [`mobile_sam/TINYVIT_LICENSE`](../mobile_sam/TINYVIT_LICENSE), [`mobile_sam/THIRD_PARTY.md`](../mobile_sam/THIRD_PARTY.md)를 참고하세요.

GUI에 사용되는 PyQt5와 Qt에는 각각의 라이선스가 적용됩니다. 최종 배포 패키지의 구체적인 고지, 대응 소스 코드 취득 지침, Qt 교체 지침은 [`third_party_licenses/`](../third_party_licenses/)에서 관리합니다. 모델 소스와 내보내기 출처 기록은 [`docs/model-provenance.md`](../docs/model-provenance.md)에, 릴리스 감사 절차는 [`docs/release-licenses.md`](../docs/release-licenses.md)에 있습니다.

## 감사의 말

ParkerLabel의 AI 지원 분할 워크플로는 다음 프로젝트의 성과를 바탕으로 합니다.

- [MobileSAM](https://github.com/ChaoningZhang/MobileSAM): 효율적인 추론을 위해 설계된 경량 Segment Anything 모델.
- [Segment Anything](https://github.com/facebookresearch/segment-anything): Meta AI가 개발한 원본 분할 모델 및 프레임워크.

두 프로젝트의 성과를 공개해 주신 저자와 기여자 여러분께 감사드립니다.
