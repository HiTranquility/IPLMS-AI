#!/usr/bin/env bash
# Xoá mật khẩu DB cũ khỏi MỌI nhánh + tag của IPLMS-AI rồi force push (IPLMS-AI bug-053).
# Cách dùng (Git Bash / Linux / macOS, cần git + python3):
#   1. bash clean_history.sh            -> chỉ chuẩn bị + kiểm, KHÔNG push
#   2. bash clean_history.sh --push     -> force push sau khi đã xem kết quả kiểm
# Mật khẩu cũ được script TỰ lấy từ dòng `PGPASSWORD=` trong .github/workflows/ci.yml
# của nhánh main hiện tại, không in ra màn hình. Có file secret.txt cạnh script thì dùng file đó.
# Trước khi --push: tạm tắt branch protection chặn force push trên main/develop (nếu có).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SECRET="$HERE/secret.txt"
WORK="$HERE/work"
REPO="https://github.com/HiTranquility/IPLMS-AI.git"
rm -rf "$WORK" && mkdir -p "$WORK"
git clone -q --mirror "$REPO" "$WORK/mirror.git"

if [ ! -s "$SECRET" ]; then
  SECRET="$WORK/secret.txt"
  ( umask 077
    git -C "$WORK/mirror.git" show main:.github/workflows/ci.yml 2>/dev/null \
      | grep -oE 'PGPASSWORD=[A-Za-z0-9]+ ' | head -1 \
      | sed -E 's/^PGPASSWORD=//; s/ $//' | tr -d '\n' > "$SECRET" )
  [ -s "$SECRET" ] || { echo "Không tự tìm được mật khẩu cũ — có thể lịch sử đã sạch rồi."; exit 1; }
  echo "Đã tự tìm mật khẩu cũ trong lịch sử ($(wc -c < "$SECRET") ký tự, không in ra)."
fi
git init -q --bare "$WORK/clean.git"

cat > "$WORK/replace_stream.py" <<'PY'
import sys
secret = open(sys.argv[1], 'rb').read().strip()
assert secret
repl = b'***REMOVED***'
inp, out = sys.stdin.buffer, sys.stdout.buffer
hits = 0
while True:
    line = inp.readline()
    if not line:
        break
    if line.startswith(b'data ') and not line.startswith(b'data <<'):
        n = int(line[5:].strip()); body = inp.read(n)
        hits += body.count(secret); body = body.replace(secret, repl)
        out.write(b'data %d\n' % len(body)); out.write(body)
    else:
        out.write(line)
out.flush()
sys.stderr.write(f'replaced {hits} occurrence(s)\n')
PY

cd "$WORK/mirror.git"
REFS=$(git for-each-ref --format='%(refname)' refs/heads refs/tags)
git fast-export --signed-tags=strip --reencode=no $REFS \
  | python3 "$WORK/replace_stream.py" "$SECRET" \
  | (cd "$WORK/clean.git" && git fast-import --quiet)

cd "$WORK/clean.git"
git fetch -q "$WORK/mirror.git" 'refs/heads/*:refs/old/heads/*' 'refs/tags/*:refs/old/tags/*'
LEFT=$(git log $REFS -p --format= | grep -c -F -f "$SECRET" || true)
echo "Còn lại sau khi lọc: $LEFT (phải là 0)"
[ "$LEFT" = 0 ] || { echo "DỪNG: còn sót"; exit 1; }
ARGS=()
for r in $REFS; do
  o=$(git rev-parse "refs/old/${r#refs/}")
  n=$(git rev-parse "$r")
  echo "${r#refs/}: ${o:0:7} -> ${n:0:7}  commits $(git rev-list --count "$o") -> $(git rev-list --count "$r")  file đổi: $(git diff --name-only "$o" "$r" | tr '\n' ' ')"
  ARGS+=(--force-with-lease="$r:$o" "$r:$r")
done

if [ "${1:-}" = "--push" ]; then
  git push "$REPO" "${ARGS[@]}"
  echo "Xong. Cả nhóm: xoá clone cũ rồi clone lại (đừng pull đè). Nhờ GitHub Support dọn refs/pull/* + cache."
  rm -rf "$WORK"
else
  echo "Chưa push. Xem kết quả trên rồi chạy lại với --push."
fi
