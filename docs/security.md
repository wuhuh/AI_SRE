# Security

## 已实现

- JWT 登录
- RBAC：VIEWER / OPERATOR / ADMIN
- 后端权限校验
- 静态 RiskPolicy 风险分级
- 高风险操作人工审批
- 一次性 Approval Execution Token
- Tool Allowlist
- Tool Server 审批 Token 校验
- Secret 通过环境变量配置
- 敏感数据脱敏工具

## 建议生产补充

- 使用 BCrypt/Argon2 保存用户密码
- JWT Secret 使用强随机值
- 限制 JWT 过期时间
- 生产关闭 `/faults`
- 使用 Ingress TLS
- 定期 Secret Scan