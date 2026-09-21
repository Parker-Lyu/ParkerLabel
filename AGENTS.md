该项目使用 Miniforge 管理 Python 运行环境。`conda activate parker-label`。
修改的时候保持文件简洁，不要写为什么修改，直接改就行
任何代码修改必须在基于最新 main 创建的独立 Git worktree 中进行，
禁止直接修改主工作区。任务完成后测试并 commit，提交到main分支，然后清理worktree
commit格式，按照业界标准格式，比如feat:***等
不要push代码

## 发布约定
- macOS 和 Windows 均提供免安装便携包，解压后运行，无需安装 Python、Conda 或依赖；配置和模型保存在程序旁的 `configs/`，升级保留该目录。
- SOP、平台说明、脚本、PyInstaller spec 和分平台依赖锁文件统一放在 `builds/`。macOS 用 `build-macos.sh`；Windows 用 `build-windows.ps1`，另提供 `.sh` 入口。详细步骤维护在 SOP，不在此重复。
- 程序版本唯一来源为 `parker_label_app/app_info.py` 的 `APP_VERSION`，UI、平台元数据和产物名称统一读取；根目录 `CHANGELOG.md` 日常记录到 `Unreleased`，发布时归入版本及日期。
- 正式发布使用指向源码提交的 Git Tag（如 `v0.1.0`）；构建校验工作区干净、HEAD 对应 Tag 且 Tag 与程序版本一致。普通开发提交不创建发布 Tag。
- 构建生成 `build-info.json`，记录程序版本、Tag、完整提交 SHA、模型清单 SHA-256、平台架构、依赖版本和构建时间，随程序分发；压缩后另生成 `SHA256SUMS`。本地输出放在 Git 忽略的 `builds/output/<版本>/<平台-架构>/`，正式发布时将记录与产物保存到对应 Release，不把生成记录回写进被构建的提交。
- 程序版本与模型版本独立；以 `model-bundle.json` 固定模型版本、地址、大小和 SHA-256。模型不变则复用，更换则发布新模型版本，不覆盖已发布文件，不让旧程序追随最新模型。
- `.npy` 缓存的模型及图片身份校验暂不实现，记录在 README 待实现部分，后续按任务要求处理。
- 保留项目 GPL-3.0-only；补齐实际依赖及模型的许可、通知、来源和所需对应源码获取材料。第三方许可维护在 `third_party_licenses/`，发布规范维护在 `docs/release-licenses.md`，UI 提供离线开源许可入口。
- 检查更新由用户手动触发，后台查询 GitHub、失败回退 Gitee，排除模型版本和预发布；有更新时提供两个平台的下载页面入口，不自动替换程序。新增文案沿用九种语言 JSON。
- macOS 先构建 arm64，不以付费 Apple 开发者会员、Developer ID 签名或公证为前提；可用本地 ad-hoc 签名，但不能将其描述为 Apple 身份认证或公证。SOP 说明首次打开可能需要系统安全确认，不要求全局关闭 Gatekeeper。
- 各平台分别构建和实测，覆盖真实推理、保存重开、模型下载及离线运行、中文路径、原生界面和升级后配置保留。Windows 参考流程不代表验收通过，免安装不代表没有系统安全提示。
