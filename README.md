# Ling with me

Ling is an animated desktop companion. On Windows, it can run on its own without ChatGPT or Codex. The original pet package and installation scripts are also available for the ChatGPT desktop app.

## Windows 独立桌宠

下载本仓库的 `Ling-Windows.zip`，解压后双击 `Ling/Ling.exe`。请保留压缩包中的整个 `Ling` 文件夹；程序需要其中的素材和运行库。Ling 会在当前显示器的可用工作区底边待机，并随机左右行走。右键“变装”可切换银色原版与红心白帽，重启后保留选择。鼠标移到人物上会触发跳跃，单击会挥手；按住左键拖动可以换屏。右键点击人物或使用系统托盘图标可暂停、继续、退出，也可从“播放动作”菜单查看其他动画。此模式不需要启动 ChatGPT 或 Codex，也不读取任务状态。

**趴在窗口上：**按住人偶任意部位拖动，让人偶的可见身体与普通窗口上边沿相交或贴近（容差 28 个逻辑像素），看到“松开即可趴在这个窗口上沿”后松手即可。不要求鼠标、头或脚下的某个点对准；身体任意高度碰到上沿均可。窗口顶部需留约 105 个逻辑像素空间；若提示无法停靠，请先把窗口稍微下移。两套造型均支持，趴着时换装会保持停靠；单击挥手后恢复趴姿，悬停不跳跃，暂停行走仍跟随窗口。拖离窗口上沿或右键“回到桌面底边”可解除停靠。窗口被最小化、关闭、隐藏、接触点被其他窗口遮挡，或顶部空间不足时，会自动回到底边；最大化窗口通常没有足够顶部空间。重启不保留窗口绑定。此动作仅用于独立 Windows 版，不改变 ChatGPT Pets 图集。

**吊在窗口下沿：**只有按住鼠标拖动人偶，让身体与窗口下边缘相交或贴近，并在看到“松开即可抓住这个窗口下沿”后松手，才会双手抓住下沿，身体和腿轻幅左右摆动。静止重叠、自行行走、窗口移动经过人偶或普通单击都不会触发。允许身体超出屏幕下边缘并被裁切，不会向上挪动或因此解除悬挂。悬挂后跟随窗口移动；换装保持抓握点，“暂停活动”停止摆动但继续跟随；悬停、单击保持抓握。拖走、选择其他动作，或通过人物/托盘菜单“回到桌面底边”可解除；窗口关闭、最小化、隐藏或抓握点被遮挡也会解除。上下沿同时符合时选择更靠近身体中心的一边，等距优先上沿。两套造型均支持，重启不保留绑定。

如需从源码构建，在 Windows 上安装 Python 3.12，进入本仓库目录并运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build-windows.ps1
```

脚本默认使用清华 PyPI 镜像安装构建依赖；如需使用官方源，可加 `-IndexUrl https://pypi.org/simple`。它会在 `dist\Ling\Ling.exe` 生成可双击运行的文件夹版程序，不会覆盖 `pet/ling` 中的原始素材。独立程序目前仅支持 Windows，尚未提供开机自启。

## Standalone Windows companion

Download `Ling-Windows.zip` from this repository, extract it, then double-click `Ling.exe` inside the extracted `Ling` folder. Keep the whole folder together. Ling idles and walks along the bottom edge of the current display's usable area. The right-click Wardrobe menu switches between the silver and heart outfits and remembers the choice. Hover over Ling to see a jump, click for a wave, or drag Ling to another display. Right-click Ling or use its system tray icon to pause, resume, quit, or preview the other animations. This mode runs without ChatGPT or Codex and does not follow task status.

To build from source on Windows, install Python 3.12 and run `build-windows.ps1` from this repository. The executable will be at `dist\Ling\Ling.exe`.

**Window ledge:** grab any part of Ling and overlap the visible body with a normal window’s top edge (28 logical pixels of tolerance). Release when the tooltip says “松开即可趴在这个窗口上沿”. Any part of the body can touch the edge; neither the pointer nor the feet need precise alignment. Leave about 105 logical pixels above the window (move it down if necessary). Both outfits support this feature. Ling follows the window even while walking is paused; click to wave and return to resting, or switch outfits without losing the ledge. Drag away from the ledge or choose “回到桌面底边” to detach. Minimizing, closing, hiding, covering the contact point, or moving the ledge too close to the screen top returns Ling to the desktop bottom. Window bindings are not saved across restarts. This feature belongs to the standalone Windows app.

**Hanging below a window:** drag Ling so the body overlaps the bottom edge, then release when the hanging hint appears. Both hands grip the edge while the body gently sways in a two-second loop. Only a mouse drag followed by release can attach; walking, passive overlap, a moving window, and an ordinary click cannot. Hanging may extend below the screen without clamping or detaching. Outfit changes preserve the grips; pause freezes the swing while following continues. Click and hover keep both hands attached. Drag away, select another action, or use the pet/tray “回到桌面底边” menu to recover even a clipped pet. Closing, minimizing, hiding, or covering the grip also detaches. If both edges qualify, the one nearer the body's center wins, with ties preferring the top.

验证命令：`python -m unittest test_window_perch -v` 检查吸附和坐标逻辑；`python tools/smoke_windows.py` 使用临时窗口检查真实 HWND 跟随、拖放、遮挡及失效解除，结果位于 `build/perch-qa/`，不修改个人设置。发布前用 `build-windows.ps1 -SkipPackage` 构建并验证文件夹版，再打包完整 `dist/Ling` 与三个说明/授权文件，最后解压运行验证。

## 第二套造型 / Second outfit

原版素材位于 `pet/ling/`，红心白帽位于 `pet/ling-heart/`。两套图集都是完整的九动作动画，独立桌宠通过右键菜单切换。若要在桌面应用的 Pets 列表中单独选择红心白帽，Windows 使用：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Variant ling-heart
```

macOS 使用 `bash ./install.sh --variant ling-heart`。不加参数仍安装原版 Ling；两套可共存，安装脚本不会覆盖已有的不同内容。安装后在 **Settings > Pets > Refresh** 中选择 **Ling·红心白帽**。原始参考照片不包含在本仓库或发布压缩包中。

Source / 项目地址：https://github.com/Saguinusimperator/ling-with-me

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
