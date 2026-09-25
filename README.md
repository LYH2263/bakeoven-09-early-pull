# BakeOven

烘焙占炉排程：发酵+烘烤半开区间占用炉位，冲突检测与下一可开工窗口。

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4500 |
| API | http://localhost:9500 |
| API 文档 | http://localhost:9500/docs |
| Postgres | localhost:5446 |

健康检查：`GET http://localhost:9500/api/health`

## 页面

- `/products` — 产品
- `/ovens` — 炉位
- `/batches` — 批次
- `/gantt` — 甘特
- `/conflicts` — 冲突
- `/windows` — 可开工

## 使用说明

1. 查看产品配方时长与炉位。
2. 创建生产批次，系统按半开区间占炉并检测冲突。
3. 甘特查看占用；冲突与可开工窗口辅助排产。
4. 批次页可登记实际出炉分钟（提前出炉）：仅允许落在原烘烤段内，登记后烘烤占炉截断——甘特烘烤条以实际出炉为终点，释放出的尾段计入可开工窗口且不再判冲突；段外登记会被拒绝。

## 开发与测试

```bash
docker compose exec api pytest -q
```
