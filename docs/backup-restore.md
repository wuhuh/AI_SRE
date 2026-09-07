# Backup / Restore

## 自动演练（P3-备份演练，round 17）

```bash
bash scripts/backup-drill.sh
```

闭环：基线计数 → pg_dump（custom format）→ DROP SCHEMA（真实销毁）→
pg_restore → 计数比对，不一致 exit 1。已实测通过（109/109/144 精确还原）。

## Backup

```powershell
.\scripts\backup-db.ps1
```

默认备份到：

```text
backup/aisre_<timestamp>.sql
```

## Restore

```powershell
.\scripts\restore-db.ps1 -BackupFile backup/aisre_xxx.sql
```

## 验证方式

1. 创建 Incident
2. 执行 Backup
3. 删除数据库或清空数据
4. 执行 Restore
5. 确认 Incident 仍然存在