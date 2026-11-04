# Third-party notices for Ling Windows v1.0

This file describes the Windows portable package. Ling's original code and artwork have separate licenses. The texts in `licenses/` apply to the respective third-party components and do not grant rights to Ling's original artwork.

| Component in the portable build | Version | License / bundled text |
| --- | --- | --- |
| Qt Base, Qt SVG, Qt Image Formats and Qt Translations | 6.12.0 | LGPLv3 option for the shipped libraries and resources; `licenses/Qt-LGPL-3.0-only.txt` and `licenses/Qt-GPL-3.0-only.txt`; source modules and specific third-party texts described below |
| PySide6 Essentials and Shiboken6 | 6.12.0 | LGPLv3 option per installed wheel metadata; the same `licenses/Qt-LGPL-3.0-only.txt` and `licenses/Qt-GPL-3.0-only.txt` texts, verified byte-identical to the binding source archive's copies |
| Python runtime and standard library | 3.12.7 | PSF License; `licenses/Python-3.12.7-LICENSE.txt` |
| Pillow and bundled image codecs | 12.1.1 | Pillow license and codec notices; `licenses/Pillow-12.1.1-LICENSE.txt` |
| OpenSSL | 3.0.15 | Apache License 2.0; `licenses/OpenSSL-3.0.15-LICENSE.txt` |
| bzip2 | 1.0.8 | `licenses/bzip2-1.0.8-LICENSE.txt` |
| expat | 2.6.3 | MIT; `licenses/expat-2.6.3-COPYING.txt` |
| libffi | 3.4.4 | MIT; `licenses/libffi-3.4.4-LICENSE.txt` |
| XZ Utils liblzma | 5.4.6 | `licenses/XZ-5.4.6-COPYING.txt` says liblzma is public domain; this is the matched local package's licensing statement for the DLL, subject to final binary composition check |
| zlib | 1.2.13 | zlib terms in `licenses/zlib-1.2.13-zlib.h` |
| Mesa llvmpipe software OpenGL fallback | Qt wheel's `opengl32sw.dll` | Qt's binary attribution for Mesa, Khronos and Boost components: `licenses/Qt-Mesa-llvmpipe-NOTICE.txt` |
| Microsoft Visual C++ runtime files | 14.44.35112 | Eleven unmodified x64 files from the licensed Visual Studio Community 2022 `VC/Redist/MSVC/14.44.35112/x64/Microsoft.VC143.CRT/` directory, in `Ling/_internal/`, `PySide6/`, and `shiboken6/`; the [Visual Studio 2022 REDIST list](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution) and [Community license terms](https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/) apply. No app-local UCRT files are included. |

The Qt DLLs and image-format plugins `qjpeg.dll`, `qtiff.dll`, and `qwebp.dll` are included in the portable folder. The Qt files in `licenses/` provide notices for the Qt modules and their bundled third-party code. See the [Qt 6.12 third-party list](https://doc.qt.io/qt-6/licenses-used-in-qt.html). [PyInstaller's official exception](https://pyinstaller.org/en/stable/license.html) does not require its license or credit to be shipped with generated application bundles.

## Qt/PySide6 source and replacement

The Qt/PySide6/Shiboken6 components are supplied as separate DLLs and Python extension modules in `Ling/_internal/PySide6/` and `Ling/_internal/shiboken6/`. Users may replace those LGPL components with ABI-compatible modified versions for debugging or use under the LGPL; Ling's custom code license does not restrict that right.

To substitute a compatible library in an extracted portable folder, close Ling, back up the target DLL or `.pyd`, copy the replacement to the same relative path and filename under `Ling/_internal/`, then start `Ling/Ling.exe`. The replacement must match the 64-bit Windows architecture and the Qt/PySide6 6.12 ABI; dependent libraries may need corresponding replacements. Restore the backed-up file if startup fails.

Corresponding source is provided as [Ling-Qt-Source-v1.0.zip](https://github.com/Saguinusimperator/ling-with-me/releases/download/v1.0/Ling-Qt-Source-v1.0.zip) with the v1.0 Release, SHA-256 `cffaf59cca011827734b607679c228f538d6cf89ee9bf718810fcdb5db8a3436`. It contains six official Qt/PySide6 6.12.0 source archives and a manifest of their URLs and hashes.

The Windows package targets Windows 10 x64 or later and uses the operating system's Universal C Runtime. Microsoft component use terms are in `MICROSOFT-TERMS.md`.
