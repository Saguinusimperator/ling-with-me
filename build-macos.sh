#!/usr/bin/env bash
# Build the standalone Ling desktop pet for macOS (Apple Silicon, macOS 14+).
#
# Outputs:
#   dist/Ling-macOS-arm64.dmg      drag-to-Applications installer image
#
# The bundle is signed ad-hoc. It runs on the machine that built it and on
# other Macs after Gatekeeper approval; see docs/MACOS.md.
set -euo pipefail

cd "$(dirname "$0")"

APP_NAME="Ling"
BUNDLE_ID="com.saguinusimperator.ling"
VERSION="1.3.0"
BUILD_NUMBER="4"
PYTHON_VERSION="3.13"
DMG_PATH="dist/${APP_NAME}-macOS-arm64.dmg"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This build script requires macOS." >&2
  exit 1
fi
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "warning: building on $(uname -m); the published package targets Apple Silicon." >&2
fi

UV="${UV:-}"
if [[ -z "$UV" ]]; then
  if command -v uv >/dev/null 2>&1; then
    UV="$(command -v uv)"
  elif [[ -x build/tools/uv/uv ]]; then
    UV="build/tools/uv/uv"
  else
    echo "uv is required to create the build environment." >&2
    echo "Install it from https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
  fi
fi
export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-$PWD/build/tools/python}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/build/tools/uv-cache}"
# Keep PyInstaller's cache inside the ignored build directory.
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$PWD/build/pyinstaller-cache}"

if [[ ! -x .venv/bin/python ]]; then
  "$UV" venv --python "$PYTHON_VERSION" --seed .venv
fi
"$UV" pip install --python .venv/bin/python -r requirements-build.txt

.venv/bin/python tools/make_macos_icon.py --output build/Ling.icns

.venv/bin/python -m PyInstaller --noconfirm --clean --windowed \
  --name "$APP_NAME" \
  --icon "$PWD/build/Ling.icns" \
  --osx-bundle-identifier "$BUNDLE_ID" \
  --hidden-import macos_perch \
  --specpath build --workpath build/pyinstaller --distpath dist \
  --add-data "$PWD/pet/ling/spritesheet.webp:pet/ling" \
  --add-data "$PWD/pet/ling-heart/spritesheet.webp:pet/ling-heart" \
  --add-data "$PWD/pet/ling/perch.png:pet/ling" \
  --add-data "$PWD/pet/ling-heart/perch.png:pet/ling-heart" \
  --add-data "$PWD/pet/ling/hang.png:pet/ling" \
  --add-data "$PWD/pet/ling-heart/hang.png:pet/ling-heart" \
  --add-data "$PWD/pet/ling/spritesheet@2x.webp:pet/ling" \
  --add-data "$PWD/pet/ling-heart/spritesheet@2x.webp:pet/ling-heart" \
  --add-data "$PWD/pet/ling/perch@2x.png:pet/ling" \
  --add-data "$PWD/pet/ling-heart/perch@2x.png:pet/ling-heart" \
  --add-data "$PWD/pet/ling/hang@2x.png:pet/ling" \
  --add-data "$PWD/pet/ling-heart/hang@2x.png:pet/ling-heart" \
  --add-data "$PWD/pet/ling-feather/spritesheet.webp:pet/ling-feather" \
  --add-data "$PWD/pet/ling-feather/spritesheet@2x.webp:pet/ling-feather" \
  --add-data "$PWD/pet/ling-feather/perch.png:pet/ling-feather" \
  --add-data "$PWD/pet/ling-feather/perch@2x.png:pet/ling-feather" \
  --add-data "$PWD/pet/ling-feather/hang.png:pet/ling-feather" \
  --add-data "$PWD/pet/ling-feather/hang@2x.png:pet/ling-feather" \
  --add-data "$PWD/pet/ling-feather/pet.json:pet/ling-feather" \
  ling_app.py

APP="dist/${APP_NAME}.app"
PLIST="$APP/Contents/Info.plist"

plist_set() { # key type value
  /usr/libexec/PlistBuddy -c "Set :$1 $3" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :$1 $2 $3" "$PLIST"
}

# Menu-bar-only app: no Dock icon, no application menu.
plist_set LSUIElement bool true
plist_set CFBundleShortVersionString string "$VERSION"
plist_set CFBundleVersion string "$BUILD_NUMBER"
plist_set LSMinimumSystemVersion string "14.0"
plist_set NSHighResolutionCapable bool true
plist_set CFBundleDisplayName string "$APP_NAME"

# Keep notices with the app when it is copied out of the DMG.
NOTICES="$APP/Contents/Resources/Notices"
mkdir -p "$NOTICES"
cp README.md LICENSE-CODE.md LICENSE-ART.md LICENSE-SCRIPTS THIRD-PARTY-NOTICES.md "$NOTICES/"
cp -R docs "$NOTICES/"
cp -R licenses "$NOTICES/"

# Changing Info.plist invalidates PyInstaller's signature, so sign last.
# Strip stray Finder metadata first: it makes strict signature checks fail.
xattr -cr "$APP"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"

STAGE="build/dmg"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
xattr -cr "$STAGE/$APP_NAME.app"
ln -s /Applications "$STAGE/Applications"
cp README.md LICENSE-CODE.md LICENSE-ART.md LICENSE-SCRIPTS THIRD-PARTY-NOTICES.md "$STAGE/"
cp -R licenses docs "$STAGE/"
rm -f "$DMG_PATH"

# macOS 26 replaced the classic "hdiutil create -srcfolder" form with one that
# mounts the image while building; that fails without a writable disk-image
# session. Build a writable hybrid image, then compress it to UDZO.
if ! hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -ov -format UDZO "$DMG_PATH" >/dev/null 2>&1; then
  rm -f "$DMG_PATH" build/Ling-rw.dmg
  hdiutil makehybrid -hfs -hfs-volume-name "$APP_NAME" -o build/Ling-rw "$STAGE" >/dev/null
  hdiutil convert build/Ling-rw.dmg -format UDZO -o "$DMG_PATH" >/dev/null
  rm -f build/Ling-rw.dmg
fi
hdiutil verify "$DMG_PATH" >/dev/null

# Leave one deliverable behind. Loose .app copies pile up in Spotlight and
# Launchpad and look like several installations of the same app.
rm -rf "$STAGE" dist/Ling dist/Ling.app

echo
echo "DMG:  $DMG_PATH ($(du -h "$DMG_PATH" | cut -f1))"
echo "SHA:  $(shasum -a 256 "$DMG_PATH" | cut -d' ' -f1)"
