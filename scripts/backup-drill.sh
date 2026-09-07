#!/usr/bin/env bash
# P3-备份演练：backup → drop → restore → 计数校验（compose 环境自动跑通闭环）。
# 用法: scripts/backup-drill.sh  （要求 aisre-postgres-1 在跑）
set -euo pipefail
C=${CONTAINER:-aisre-postgres-1}
TS=$(date +%Y%m%d_%H%M%S)
OUT="backup/aisre_${TS}.sql"
mkdir -p backup

count() { docker exec "$C" psql -U aisre -d aisre -tAc "$1"; }

echo "[1/5] baseline counts"
B_INC=$(count "SELECT count(*) FROM incident")
B_TASK=$(count "SELECT count(*) FROM agent_task")
B_APR=$(count "SELECT count(*) FROM approval")
echo "incidents=$B_INC tasks=$B_TASK approvals=$B_APR"

echo "[2/5] pg_dump"
docker exec "$C" pg_dump -U aisre -d aisre -F c -f /tmp/backup.dump
docker cp "$C:/tmp/backup.dump" "$OUT"
echo "saved $OUT ($(du -h "$OUT" | cut -f1))"

echo "[3/5] destroy schema (drop all)"
docker exec "$C" psql -U aisre -d aisre -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" >/dev/null
AFTER_DROP=$(count "SELECT count(*) FROM pg_tables WHERE schemaname='public'")
echo "tables after drop=$AFTER_DROP"

echo "[4/5] pg_restore --clean --if-exists"
docker cp "$OUT" "$C:/tmp/restore.dump"
# dump 来自 DROP 后的空 schema：直接整库恢复（--clean 需要 dump 内含 drop 语句，
# 我们在演练里已手动 drop，用 --data-only? 不——直接常规恢复即可）
docker exec "$C" pg_restore -U aisre -d aisre /tmp/restore.dump
# pg_restore --if-exists 对 --clean 的报错已抑制；exit 0 即成功

echo "[5/5] verify counts match baseline"
A_INC=$(count "SELECT count(*) FROM incident")
A_TASK=$(count "SELECT count(*) FROM agent_task")
A_APR=$(count "SELECT count(*) FROM approval")
echo "incidents=$A_INC tasks=$A_TASK approvals=$A_APR"
test "$B_INC" = "$A_INC" && test "$B_TASK" = "$A_TASK" && test "$B_APR" = "$A_APR" \
  && echo "DRILL PASSED: backup=$OUT" \
  || { echo "DRILL FAILED"; exit 1; }
