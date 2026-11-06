# 开发与发布维护

本文件记录可长期复用的工程信息。用户操作见[使用指南](USER-GUIDE.md)；素材生成提示词和制作流水账保存在仓库外的私人记录中。

## 结构与运行入口

- `ling_app.py` 是 Windows/macOS 独立桌宠入口，负责 Qt 窗口、动作播放、菜单、换装和设置。
- `window_perch.py` 提供共享的窗口边缘候选、遮挡与坐标判断，以及 Windows 窗口枚举；`macos_perch.py` 提供 Mac 窗口枚举。
- `pet/ling/` 和 `pet/ling-heart/` 各有 8 列 × 9 行、单格 192 × 208 的 `spritesheet.webp`，以及独立桌宠专用的 `perch.png`、`hang.png`。`pet.json` 是 Pets 清单。
- `install.ps1` 和 `install.sh` 安装可选 Pets；`.github/workflows/install-macos.yml` 检查 macOS 脚本的重复安装与冲突处理。
- `build-windows.ps1` 和 `requirements-build.txt` 生成 Windows 文件夹版；`tools/build_windows.py` 处理 PyInstaller 的 Windows ICU 预加载。
- `test_playback.py`、`test_window_perch.py` 是单元测试；`tools/smoke_playback.py` 录制真实 Qt 播放；`tools/smoke_windows.py` 通过临时真实窗口验证停靠、悬挂与解除。
- `tools/pack_hanging.py` 是悬挂素材的裁切与对齐工具；`tools/normalize_face_tones.py` 是现有图集的肤色维护工具，运行它需要 Pillow 和 NumPy，不属于桌宠运行依赖。

## 动画与坐标约束

`ling_app.py` 中的 `ANIMATIONS` 将九个动作分别映射到图集行和有效帧数；更换图集时必须保持行顺序、有效列数、画布尺寸和透明度。独立程序用 Pillow 解码，再以 PNG 内存数据交给 Qt，避免依赖 Qt 的 WebP 插件。

普通动作每个循环约 1.6 秒，自动播放每组两个循环。上沿趴姿使用六帧条图，显示时消除顶部 84 像素透明留白，显示锚点为 `(96, 104)`；站立反应按同一锚点缩放。下沿悬挂使用八帧条图，每帧 250 毫秒，双手共同中心锚点为 `(96, 10)`；银色手部横向偏移为 ±22，红心白帽约为 ±16.56。修改素材时需核对手部、头部和窗口边缘的对齐，不能只凭帧尺寸判断成功。

窗口吸附由拖动后松手触发，候选窗口必须可见且接触点未被遮挡。上沿需给身体留出顶部空间；下沿允许身体伸出屏幕。窗口关闭、隐藏、最小化或接触点被挡住时解除绑定。暂停时悬挂跟随仍继续，但摆动停止。`window_perch.py` 的坐标逻辑和真实 HWND 行为都应在改动后验证。

## 本地构建与验证

在 Windows 上准备 Python 3.12，然后从仓库根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build-windows.ps1 -SkipPackage
```

脚本创建 `.venv`、安装 `requirements-build.txt` 的固定版本，并生成 `dist/Ling/Ling.exe`。默认依赖源为清华 PyPI 镜像，可用 `-IndexUrl https://pypi.org/simple` 选择官方源。若旧 `Ling.exe` 正在运行，先正常退出再重建，避免文件锁阻止清理 `dist/Ling`。

按改动范围执行检查：

```powershell
.venv\Scripts\python.exe -m unittest test_playback test_window_perch -v
.venv\Scripts\python.exe tools\smoke_windows.py
.venv\Scripts\python.exe tools\smoke_playback.py
git diff --check
```

后两项需要实际 Windows 图形桌面；播放录制还需要 FFmpeg。`smoke_windows.py` 在 `build/perch-qa/` 留下截图与动画，`smoke_playback.py` 在 `build/playback-qa/` 留下 30 秒录制和计时数据。它们不能替代打包版菜单实际操作、另一台干净 Windows 电脑上的试用。

## macOS 构建与预览发布

准备 uv 和 Python 3.13，在 Apple Silicon Mac 上执行 `bash build-macos.sh`。若没有 `.venv`，脚本用 uv 创建环境；已有环境会直接复用，因此换平台或 Python 版本时应先检查环境。依赖版本见 `requirements-build.txt`。产物为 `dist/Ling-macOS-arm64.dmg`；脚本签名、校验并清除临时 app 副本。

DMG 和应用内部 `Contents/Resources/Notices/` 均保留原创许可、第三方许可与使用说明。修改包内文件必须发生在签名前；签名后再创建 DMG。

发布前从最终 DMG 复制应用，确认启动/退出、九动作、换装记忆、悬停/单击/拖动、上下沿吸附、遮挡解除、暂停跟随、关窗/最小化解除。首次网络下载的 Gatekeeper 提示应按实际环境记录，不能用本机直接构建启动代替。没有验证的系统、显示器或桌面模式如实列为限制，不为预览版扩展测试框架。

Mac 预览版使用 `v1.2.0-macos-preview`，应用版本 `1.2.0`、构建号 `3`，Retina 屏幕启用 2× 图集。完成文档后重建最终 DMG，记录 SHA-256 和对应提交；提交源码、推送标签，创建 GitHub pre-release（不设为 Latest），仅附加 DMG。发布后检查下载链接和远端附件摘要。v1.0 的 Windows/Pets/Qt 源码附件保持原样。

## Windows 便携 ZIP 与发布流程

1. 先确认文件夹版 `dist/Ling/Ling.exe` 能启动和退出，并检查动作、换装、停靠、悬挂、暂停、菜单与托盘。
2. 将**整个** `dist/Ling` 文件夹与 `README.md`、`LICENSE-CODE.md`、`LICENSE-ART.md`、`LICENSE-SCRIPTS`、`THIRD-PARTY-NOTICES.md`、`MICROSOFT-TERMS.md` 和 `licenses/` 一起压缩；不要只发送 EXE。正式发布包还须使用已核对的微软运行库文件。
3. 解压 ZIP 到另一个目录，核对图集、Qt 平台插件和运行库，并实际启动解压版。记录包体大小、SHA-256 和对应源码 Commit。
4. 检查仓库及包体没有密钥、个人路径、调试日志或私人制作记录。授权与第三方许可验收通过后，再准备 Release 和 README 正式下载入口。
5. 正式分享前请另一台干净 Windows 电脑的使用者验证下载、解压、启动、操作与退出；记录环境、结果和限制。

## Retina 图集（2×）

`pet/<skin>/spritesheet@2x.webp`、`perch@2x.png`、`hang@2x.png` 由原始生成条图重建，脚本是 `tools/build_retina_assets.py`，依赖 `requirements-assets.txt`（numpy、scipy）。这些依赖只用于构建素材，不会打进应用。

原始条图不在仓库内，运行时用 `--source-root` 指向外接盘 `ling/` 目录（`ling-pet-run/decoded`、`versions/ling-heart/decoded`、`ling-with-me/build/{perch,hanging}-qa/source`）。脚本对每帧做蓝底抠图、去溢色和连通域清理，再用掩码配准把 1× 帧映射回源图，输出 384×416 单格与 3072×3744 图集；`build/retina-qa/registration.json` 记录每帧的缩放、偏移和回采 IoU。`failed`、`left` 等动作的源图与成品存在轻微差异，修改后用该报告逐行核对。

运行时由 `preferred_scale()` 决定：仅 macOS 且屏幕 `devicePixelRatio ≥ 1.5` 时加载 2×；Windows 和非 Retina 屏幕始终使用 1×。ChatGPT Pets 的图集格式固定为 1536×1872，必须继续使用 1× 文件。只改 1× 或只改 2× 素材都会造成两套渲染不一致。

## 已知边界

独立桌宠支持 Windows 和 macOS；Mac 使用 Quartz 读取窗口并复用相同的停靠几何，详见 [Mac 说明](MACOS.md)。窗口绑定不跨重启保存。当前项目未设置开机自启或自动更新。v1.0 的 Windows 便携包已在另一台电脑上解压并启动。仓库外的私人素材制作记录不会随 Git 同步，需要单独备份。
