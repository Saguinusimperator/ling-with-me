# Ling with me

小灵是可以待在桌面上的动画伙伴。点击他就会开心雀跃哦。
![银色与红心白帽两套造型的真实播放预览](docs/assets/preview.gif)

## 下载

| 平台 | 下载 | 运行要求 |
| --- | --- | --- |
| macOS（预览版） | [Ling-macOS-arm64.dmg](https://github.com/Saguinusimperator/ling-with-me/releases/download/v1.1.0-macos-preview/Ling-macOS-arm64.dmg) · [发布说明](https://github.com/Saguinusimperator/ling-with-me/releases/tag/v1.1.0-macos-preview) | Apple Silicon（M 系列）；目标最低 macOS 14，当前实测 macOS 27.0；不提供 Intel 版 |
| Windows v1.0 | [Ling-Windows.zip](https://github.com/Saguinusimperator/ling-with-me/releases/download/v1.0/Ling-Windows.zip) · [发布说明](https://github.com/Saguinusimperator/ling-with-me/releases/tag/v1.0) | Windows 10 x64 或更新版本 |
| ChatGPT Pets | [Ling-Pets.zip](https://github.com/Saguinusimperator/ling-with-me/releases/download/v1.0/Ling-Pets.zip) | 桌面应用及账号或工作区支持 Pets，按包内 README 安装 |

Windows 和 Mac 独立桌宠不需要 Python、ChatGPT、Codex 或网络连接。Pets 是另一种可选使用方式。

## 安装与操作

**macOS：** 下载并打开 DMG → 把 Ling 拖到“应用程序” → 从“应用程序”启动。更新时先退出旧版，再拖入并选择“替换”，换装设置会保留。

Mac 预览版采用临时签名，未经 Apple Developer ID 签名和公证。如果首次打开被拦截，先尝试打开一次，再到“系统设置 → 隐私与安全性 → 仍要打开”。具体提示以系统为准，见 [Mac 使用说明](docs/MACOS.md)。

**Windows：** 下载完整 ZIP → 完整解压并保留整个 `Ling` 文件夹 → 双击 `Ling/Ling.exe`。

小灵会在桌面底边播放九种动作。鼠标悬停会触发跳跃，单击会挥手，拖动可以移动位置，拖到普通窗口上沿或下沿松手可以趴住或悬挂。右键点击小灵或系统托盘/菜单栏图标，可以换装、暂停、选择动作或退出。更多操作见[使用指南](docs/USER-GUIDE.md)。

## 其他信息

- [Mac 使用说明与已知限制](docs/MACOS.md)：Retina 上素材可能偏软，多屏、全屏及 Stage Manager 尚未完整验证。
- [ChatGPT Pets 可选适配](docs/PETS.md)。
- [主程序授权](LICENSE-CODE.md)、[素材授权说明](LICENSE-ART.md)、[安装脚本许可](LICENSE-SCRIPTS)、[第三方许可说明](THIRD-PARTY-NOTICES.md)；[微软组件条款](MICROSOFT-TERMS.md)仅适用于 Windows 包。
- [反馈问题](https://github.com/Saguinusimperator/ling-with-me/issues)。
- [开发与构建说明](docs/DEVELOPMENT.md)。
