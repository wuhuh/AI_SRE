# Upgrade / Rollback

## Docker Compose Upgrade

```bash
git pull
docker compose up -d --build
```

数据库 Migration 由 Flyway 自动执行。

## Kubernetes Upgrade

```bash
kubectl apply -k deploy/k8s/
kubectl rollout status deployment/control-plane -n ai-sre
```

## Rollback

```bash
docker compose up -d --build <service>
# 或使用上一版本镜像 tag
```

Kubernetes：

```bash
kubectl rollout undo deployment/control-plane -n ai-sre
```