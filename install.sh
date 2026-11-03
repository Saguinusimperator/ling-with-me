#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
variant=ling
if [[ $# -ne 0 ]]; then
  if [[ $# -ne 2 || "$1" != --variant || ( "$2" != ling && "$2" != ling-heart ) ]]; then
    echo 'Usage: bash ./install.sh [--variant ling|ling-heart]' >&2
    exit 2
  fi
  variant="$2"
fi
source_dir="$script_dir/pet/$variant"
source_json="$source_dir/pet.json"
source_sheet="$source_dir/spritesheet.webp"
if [[ ! -f "$source_json" || ! -f "$source_sheet" ]]; then
  echo "$variant pet files are missing. Download the complete repository and run this script from it." >&2
  exit 1
fi

codex_home="${CODEX_HOME:-$HOME/.codex}"
pets_dir="$codex_home/pets"
destination="$pets_dir/$variant"

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
    echo "A different pet already exists at $destination. Back it up or remove it manually before installing." >&2
    exit 1
  fi
  echo "$variant is already installed at $destination"
  exit 0
fi

mkdir -p "$pets_dir"
stage="$(mktemp -d "$pets_dir/.$variant-install.XXXXXX")"
trap 'rm -rf "$stage"' EXIT
cp "$source_json" "$stage/pet.json"
cp "$source_sheet" "$stage/spritesheet.webp"
mv "$stage" "$destination"
trap - EXIT

echo "$variant installed at $destination"
echo 'Open Settings > Pets > Refresh, choose the installed variant, then enter /pet to show it.'
