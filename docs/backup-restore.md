# Backup / Restore

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