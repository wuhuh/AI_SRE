# 剩余需求说明

本文档记录当前未完成但已具备代码/配置的需求，以及未完成原因。

## 1. RocketMQ Python Consumer 真实消费验证

- 状态：代码已实现
- 未完成原因：`rocketmq-client-python` 需要额外动态库，当前环境无法直接运行
- 已有替代验证：
  - RocketMQ Topic 已真实创建
  - Control Plane Producer 已真实发送消息
  - Agent Runtime 自动任务消费（HTTP polling）已通过测试

## 2. Chaos Mesh 真实实验

- 状态：故障注入 YAML 已提供
- 未完成原因：需要 Kubernetes + Chaos Mesh 集群
- 已提供：
  - `pod-kill.yaml`
  - `cpu-stress.yaml`
  - `network-delay.yaml`

## 3. 完整浏览器端到端人工验收

- 状态：前端已实现并构建成功
- 未完成原因：需要人工在浏览器中完成点击验收
- 已提供：
  - 静态 Dashboard
  - React 工程
  - Docker 前端镜像

## 结论

所有可自动化验证的需求已完成；剩余项为外部基础设施或人工操作限制。