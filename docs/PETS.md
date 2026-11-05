# ChatGPT Pets 可选适配

仓库还提供两套 ChatGPT Pets 图集。Pets 需要 Windows 或 macOS 桌面应用及账号或工作区开放的 Pets 功能；它不是独立桌宠的运行依赖。Mac 独立桌宠的源码运行与构建见 [Mac 说明](MACOS.md)。

先下载并解压仓库源码，或克隆仓库，然后在项目目录运行安装脚本。

Windows PowerShell：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Variant ling-heart
```

macOS 终端：

```bash
bash ./install.sh
bash ./install.sh --variant ling-heart
```

第一条命令安装银色原版，第二条安装红心白帽；可按需只安装其中一套。安装脚本会把对应的 `pet.json` 和 `spritesheet.webp` 放在 `${CODEX_HOME}/pets/<造型 ID>/`；未设置 `CODEX_HOME` 时使用用户目录下的 `.codex/pets/`。相同文件重复安装不会改变内容；如果目标目录已有不同文件，脚本会停止，不会覆盖。

安装后在桌面应用的 **Settings → Pets → Refresh** 中刷新并选择 Ling 或 Ling·红心白帽，再输入 `/pet` 显示。若看不到 Pets，请先检查桌面应用与账号或工作区是否支持该功能。两套 Pets 只使用各自的九动作图集；窗口上沿停靠和下沿悬挂属于 Windows/macOS 独立桌宠。

功能与界面说明以 [ChatGPT Pets 官方文档](https://learn.chatgpt.com/docs/pets)为准。安装脚本说明见[开发文档](DEVELOPMENT.md)，授权范围见[素材许可](../LICENSE-ART.md)。
