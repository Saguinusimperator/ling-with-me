#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_dir="$script_dir/pet/ling"
source_json="$source_dir/pet.json"
source_sheet="$source_dir/spritesheet.webp"
if [[ ! -f "$source_json" || ! -f "$source_sheet" ]]; then
  echo 'Ling pet files are missing. Download the complete repository and run this script from it.' >&2
  exit 1
fi

codex_home="${CODEX_HOME:-$HOME/.codex}"
pets_dir="$codex_home/pets"
destination="$pets_dir/ling"

if [[ -e "$destination" || -L "$destination" ]]; then
  if [[ ! -d "$destination" ]]; then
    echo "Destination exists and is not a directory: $destination" >&2
    exit 1
  fi
  shopt -s nullglob dotglob
  entries=("$destination"/*)
  shopt -u nullglob dotglob
  if [[ ${#entries[@]} -ne 2 || ! -f "$destination/pet.json" || ! -f "$destination/spritesheet.webp" ]] ||
     ! cmp -s "$source_json" "$destination/pet.json" ||
     ! cmp -s "$source_sheet" "$destination/spritesheet.webp"; then
    echo "A different Ling pet already exists at $destination. Back it up or remove it manually before installing." >&2
    exit 1
  fi
  echo "Ling is already installed at $destination"
  exit 0
fi

mkdir -p "$pets_dir"
stage="$(mktemp -d "$pets_dir/.ling-install.XXXXXX")"
trap 'rm -rf "$stage"' EXIT
cp "$source_json" "$stage/pet.json"
cp "$source_sheet" "$stage/spritesheet.webp"
mv "$stage" "$destination"
trap - EXIT

echo "Ling installed at $destination"
echo 'Open Settings > Pets > Refresh, select Ling, then enter /pet to show it.'
