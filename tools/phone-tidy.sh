#!/data/data/com.termux/files/usr/bin/bash
# Phone Tidy for Termux, by Frantz Vardman.
# Finds clutter in your phone's shared storage and, only with your OK, MOVES it to a review folder.
# It never deletes anything, never judges a file by how old it is, and writes an undo script.
#   1. Installer files (.apk/.apks/.xapk) left in Download after installing apps
#   2. Exact duplicate files (same size AND same SHA-256 fingerprint): keeps one copy, moves the extras
#   3. Thumbnail caches (.thumbnails): Android rebuilds these on its own
#   4. Empty folders
#   5. Your biggest files: listed only, never moved
set -u
S="$HOME/storage/shared"
# Why readlink: on phones, storage/shared is a shortcut (symlink) to the real storage, and find won't walk into a shortcut.
[ -L "$S" ] && S=$(readlink -f "$S")
if [ ! -d "$S" ]; then
  echo "First give Termux access to your files: run  termux-setup-storage  , tap Allow, then run this again."; exit 1
fi
command -v sha256sum >/dev/null || { echo "Installing tools…"; pkg install -y coreutils findutils >/dev/null; }
STAMP=$(date +%Y-%m-%d_%H%M); BIN="$S/_to_review/$STAMP"; LOG="$BIN/moved.txt"; UNDO="$BIN/undo.sh"; TMP=$(mktemp -d)
human() { awk -v b="$1" 'BEGIN{ s="B KB MB GB"; split(s,u," "); i=1; while (b>=1024 && i<4) { b/=1024; i++ } printf (i==1?"%d %s":"%.1f %s"), b, u[i] }'; }
total() { local t=0 f; while IFS= read -r f; do [ -f "$f" ] && t=$((t + $(stat -c %s "$f" 2>/dev/null || echo 0))); done < "$1"; echo $t; }
ask() { local a; read -r -p "$1 [y/N] " a; [ "$a" = "y" ] || [ "$a" = "Y" ]; }
moveall() { # list-file category
  mkdir -p "$BIN"; [ -f "$UNDO" ] || { echo '#!/data/data/com.termux/files/usr/bin/bash' > "$UNDO"; echo '# Puts every moved file back where it was.' >> "$UNDO"; chmod +x "$UNDO"; }
  local n=0 f rel dest
  while IFS= read -r f; do [ -e "$f" ] || continue
    rel="${f#$S/}"; dest="$BIN/$2/$rel"; mkdir -p "$(dirname "$dest")"
    if mv -n "$f" "$dest" 2>/dev/null; then n=$((n+1)); echo "$rel" >> "$LOG"; printf 'mkdir -p "%s"; mv -n "%s" "%s"\n' "$(dirname "$f")" "$dest" "$f" >> "$UNDO"; fi
  done < "$1"; echo "  moved $n item(s)."
}
echo "Scanning your phone's shared storage (this can take a minute)…"; echo

# 1. Installer files
find "$S/Download" "$S/Downloads" -maxdepth 3 -type f \( -iname '*.apk' -o -iname '*.apks' -o -iname '*.xapk' \) 2>/dev/null > "$TMP/apk"
N=$(wc -l < "$TMP/apk"); if [ "$N" -gt 0 ]; then
  echo "1) $N app installer file(s) in Download, $(human $(total "$TMP/apk")). Installed apps don't need these."
  sed "s|$S/||" "$TMP/apk" | head -15 | sed 's/^/     /'; [ "$N" -gt 15 ] && echo "     …and $((N-15)) more"
  ask "   Move them to the review folder?" && moveall "$TMP/apk" installers; echo; fi

# 2. Exact duplicates (same size first, then same fingerprint)
find "$S/" \( -path "$S/_to_review" -o -path "$S/Android/data" -o -path "$S/Android/obb" \) -prune -o -type f -size +100k -printf '%s\t%p\n' 2>/dev/null | sort -n > "$TMP/sizes"
if [ ! -s "$TMP/sizes" ]; then
  echo "   (Couldn't list files in $S. If Termux was just updated, run  termux-setup-storage  , answer y, tap Allow, and try again.)"; echo
fi
awk -F'\t' '{c[$1]++; p[$1]=p[$1] $2 "\n"} END{for (s in c) if (c[s]>1) printf "%s", p[s]}' "$TMP/sizes" | sed '/^$/d' > "$TMP/same"
: > "$TMP/dups"
if [ -s "$TMP/same" ]; then
  # Which copy to keep: the one in your organized folders (Camera, Pictures, Music, Documents) beats Download,
  # messaging-app folders, thumbnail caches and "(1)" copies. Lower score = keep.
  tr '\n' '\0' < "$TMP/same" | xargs -0 sha256sum 2>/dev/null | awk '{h=$1; $1=""; sub(/^ +/,""); p=$0; s=50
    if (p ~ /\/(DCIM|Pictures|Music|Documents)\//) s=10
    if (p ~ /\/(Download|Downloads)\//) s=60
    if (p ~ /WhatsApp|Telegram|Messenger|Signal/) s=70
    if (p ~ /\.thumbnails/) s=90
    if (p ~ /\([0-9]+\)\.[A-Za-z0-9]+$/) s+=5
    printf "%s\t%03d\t%s\n", h, s, p}' | sort -t$'\t' -k1,1 -k2,2n -k3,3 > "$TMP/hashes"
  awk -F'\t' '{if ($1==last) print $3; last=$1}' "$TMP/hashes" > "$TMP/dups"   # every copy after the one to keep
fi
N=$(wc -l < "$TMP/dups"); if [ "$N" -gt 0 ]; then
  echo "2) $N exact duplicate file(s), $(human $(total "$TMP/dups")). One copy of each is always kept."
  sed "s|$S/||" "$TMP/dups" | head -15 | sed 's/^/     extra copy: /'; [ "$N" -gt 15 ] && echo "     …and $((N-15)) more"
  ask "   Move the extra copies to the review folder?" && moveall "$TMP/dups" duplicates; echo; fi

# 3. Thumbnail caches
find "$S" -path "$S/_to_review" -prune -o -type d -name '.thumbnails' -print 2>/dev/null > "$TMP/thumbdirs"
: > "$TMP/thumbs"; while IFS= read -r d; do find "$d" -type f >> "$TMP/thumbs" 2>/dev/null; done < "$TMP/thumbdirs"
N=$(wc -l < "$TMP/thumbs"); if [ "$N" -gt 0 ]; then
  echo "3) Thumbnail caches: $N file(s), $(human $(total "$TMP/thumbs")). Your gallery rebuilds these when needed."
  ask "   Move them to the review folder?" && moveall "$TMP/thumbs" thumbnails; echo; fi

# 4. Empty folders (not hidden ones, not Android's own)
find "$S" -mindepth 2 \( -path "$S/Android" -o -path "$S/_to_review" \) -prune -o -type d -empty ! -name '.*' -print 2>/dev/null > "$TMP/empty"
N=$(wc -l < "$TMP/empty"); if [ "$N" -gt 0 ]; then
  echo "4) $N empty folder(s)."; sed "s|$S/||" "$TMP/empty" | head -10 | sed 's/^/     /'
  ask "   Move them to the review folder?" && moveall "$TMP/empty" empty-folders; echo; fi

# 5. Biggest files: for you to decide, never moved
echo "5) Your 15 biggest files (listed only, nothing is moved):"
sort -rn "$TMP/sizes" | head -15 | while IFS=$'\t' read -r sz p; do printf "     %9s  %s\n" "$(human "$sz")" "${p#$S/}"; done
echo
if [ -s "$LOG" ] 2>/dev/null; then
  echo "Done. Moved items are in:  Internal storage/_to_review/$STAMP"
  echo "Freed up: $(du -sh "$BIN" 2>/dev/null | cut -f1) (once you delete that folder)."
  echo "Changed your mind? Run:  bash \"$UNDO\"   to put everything back."
  echo "Happy with it after a few days? Delete the _to_review folder in your Files app."
else echo "Nothing was moved."; fi
echo
echo "Also worth a look (Termux can't do these for you):"
echo "  • Settings › Apps: sort by size or last used, and uninstall apps you don't use."
echo "  • Settings › Storage › Apps: 'Clear cache' on the biggest apps (keeps your data)."
echo "  • Settings › Battery: check which apps use the most in the background."
rm -rf "$TMP"
