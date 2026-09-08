# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: user_sim.spec.js >> user flow: login then survive 2 poll cycles
- Location: e2e/user_sim.spec.js:2:1

# Error details

```
Test timeout of 30000ms exceeded.
```

# Page snapshot

```yaml
- generic [ref=e3]:
  - banner [ref=e4]:
    - generic [ref=e5]:
      - generic [ref=e6]: AI SRE
      - generic [ref=e7]: Intelligent Reliability Platform
    - button "login 登录" [active] [ref=e8] [cursor=pointer]:
      - img "login" [ref=e10]
      - generic [ref=e13]: 登录
  - main [ref=e14]:
    - generic [ref=e15]:
      - generic [ref=e16]:
        - generic [ref=e17]: 系统概览
        - generic [ref=e18]: 实时监控服务健康状态、Incident 与 AI 诊断结果
      - generic [ref=e20]:
        - generic [ref=e24]:
          - generic [ref=e25]: HEALTHY
          - generic [ref=e26]: 0 active incidents · 0 critical services
        - button "reload 刷新" [ref=e28] [cursor=pointer]:
          - img "reload" [ref=e30]
          - generic [ref=e33]: 刷新
    - generic [ref=e34]:
      - generic [ref=e36]:
        - generic [ref=e37]: Incident
        - generic [ref=e38]: "0"
        - generic [ref=e39]: 0 active critical
      - generic [ref=e41]:
        - generic [ref=e42]: Active
        - generic [ref=e43]: "0"
        - generic [ref=e44]: Currently processing
      - generic [ref=e46]:
        - generic [ref=e47]: Recovered
        - generic [ref=e48]: "0"
        - generic [ref=e49]: Recovered incidents
      - generic [ref=e51]:
        - generic [ref=e52]: Pending Approval
        - generic [ref=e53]: "0"
        - generic [ref=e54]: Require human action
    - generic [ref=e55]:
      - generic [ref=e57]:
        - generic [ref=e58]: Service Health
        - generic [ref=e62]:
          - generic [ref=e63]:
            - generic [ref=e64]: api-gateway
            - generic [ref=e67]: Healthy · 2ms
          - generic [ref=e68]:
            - generic [ref=e69]: order-service
            - generic [ref=e72]: Healthy · 2ms
          - generic [ref=e73]:
            - generic [ref=e74]: inventory-service
            - generic [ref=e77]: Healthy · 2ms
          - generic [ref=e78]:
            - generic [ref=e79]: payment-service
            - generic [ref=e82]: Healthy · 2ms
      - generic [ref=e84]:
        - generic [ref=e85]: Incident Overview
        - generic [ref=e89]:
          - generic [ref=e91]:
            - generic [ref=e92]: Critical
            - generic [ref=e93]: "0"
          - generic [ref=e96]:
            - generic [ref=e97]: High
            - generic [ref=e98]: "0"
          - generic [ref=e101]:
            - generic [ref=e102]: Medium
            - generic [ref=e103]: "0"
          - generic [ref=e106]:
            - generic [ref=e107]: Recovered
            - generic [ref=e108]: "0"
    - generic [ref=e110]:
      - generic [ref=e111]: Recent Incidents
      - table [ref=e121]:
        - rowgroup [ref=e124]:
          - row [ref=e125]:
            - columnheader "Incident" [ref=e126]
            - columnheader "Service" [ref=e127]
            - columnheader "Severity" [ref=e128]
            - columnheader "Status" [ref=e129]
            - columnheader "Started" [ref=e130]
            - columnheader "Root Cause" [ref=e131]
        - rowgroup [ref=e132]:
          - row [ref=e133]:
            - cell "No data No data" [ref=e134]:
              - generic [ref=e135]:
                - img "No data" [ref=e137]
                - generic [ref=e143]: No data
```