# Ling with me

Ling is an animated desktop companion. On Windows, it can run on its own without ChatGPT or Codex. The original pet package and installation scripts are also available for the ChatGPT desktop app.

## Windows 独立桌宠

下载本仓库的 `Ling-Windows.zip`，解压后双击 `Ling/Ling.exe`。请保留压缩包中的整个 `Ling` 文件夹；程序需要其中的素材和运行库。Ling 会在当前显示器的可用工作区底边待机，并随机左右行走。鼠标移到人物上会触发跳跃，单击会挥手；按住左键拖动可以换屏，松开后会贴回该屏幕底边。右键点击人物或使用系统托盘图标可暂停、继续、退出，也可从“播放动作”菜单查看其他动画。此模式不需要启动 ChatGPT 或 Codex，也不读取任务状态。

如需从源码构建，在 Windows 上安装 Python 3.12，进入本仓库目录并运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build-windows.ps1
```

脚本默认使用清华 PyPI 镜像安装构建依赖；如需使用官方源，可加 `-IndexUrl https://pypi.org/simple`。它会在 `dist\Ling\Ling.exe` 生成可双击运行的文件夹版程序，不会覆盖 `pet/ling` 中的原始素材。首版仅支持 Windows；没有开机自启或服装切换。

## Standalone Windows companion

Download `Ling-Windows.zip` from this repository, extract it, then double-click `Ling.exe` inside the extracted `Ling` folder. Keep the whole folder together. Ling idles and walks along the bottom edge of the current display's usable area. Hover over Ling to see a jump, click for a wave, or drag Ling to another display. Right-click Ling or use its system tray icon to pause, resume, quit, or preview the other animations. This mode runs without ChatGPT or Codex and does not follow task status.

To build from source on Windows, install Python 3.12 and run `build-windows.ps1` from this repository. The executable will be at `dist\Ling\Ling.exe`.

## ChatGPT Pets 安装 / Install for ChatGPT Pets

需要 Windows 或 macOS 版 ChatGPT 桌面应用，且账号或工作区已开放 Pets 功能。请下载仓库 ZIP 并解压，或用 Git 克隆仓库。**在解压后的项目目录中**运行：

Windows（PowerShell）：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

macOS（终端）：

```bash
bash ./install.sh
```

脚本会把 `pet/ling/pet.json` 和 `pet/ling/spritesheet.webp` 安装到 `${CODEX_HOME}/pets/ling`；如果未设置 `CODEX_HOME`，则使用用户目录的 `.codex/pets/ling`。重复运行不会改变相同的安装。若目标位置已有不同内容，脚本会停止并提示你手动处理，不会覆盖。

安装后打开桌面应用 **Settings > Pets > Refresh**，选择 **Ling**，再输入 `/pet` 显示桌宠。Windows 也可以按 **Win+Alt+P**，macOS 可以按 **Option+Space**。若找不到 Pets，请更新桌面应用，并检查你的账号或工作区是否开放该功能。VS Code 中的 Codex 扩展本身不提供悬浮桌宠。

官方说明：[Pets](https://learn.chatgpt.com/docs/pets)。

## Install in English

You need the ChatGPT desktop app on Windows or macOS, with Pets available to your account or workspace. Download and extract this repository, or clone it with Git. From the extracted project directory, run:

Windows (PowerShell):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

macOS (Terminal):

```bash
bash ./install.sh
```

The scripts install the two files from `pet/ling/` to `${CODEX_HOME}/pets/ling`, or to `~/.codex/pets/ling` if `CODEX_HOME` is unset. Running the installer again with the same files is safe. If another Ling pet is present there, the installer stops without overwriting it.

Then open **Settings > Pets > Refresh**, choose **Ling**, and enter `/pet` to show the floating pet. You can also use **Win+Alt+P** on Windows or **Option+Space** on macOS. If Pets is missing, update the desktop app and check account or workspace availability. The Codex VS Code extension does not itself display the floating pet.

See the [official Pets guide](https://learn.chatgpt.com/docs/pets).

## License / 授权

The Ling artwork and pet package are subject to [LICENSE-ART.md](LICENSE-ART.md): personal noncommercial use and redistribution of the unchanged original are allowed; publishing modified artwork or commercial use requires separate permission. The installation scripts are under the [MIT license](LICENSE-SCRIPTS).

Ling 图片及桌宠素材遵循 [LICENSE-ART.md](LICENSE-ART.md)：允许个人非商用使用、分享未修改的原版；公开发布修改版或商业使用须另获授权。安装脚本采用 [MIT 许可](LICENSE-SCRIPTS)。
