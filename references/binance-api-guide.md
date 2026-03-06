# 币安广场 API Key 获取教程

## 前置准备

1. 一个已认证（KYC）的币安账号
2. 币安广场创作者身份

## 步骤

### 1. 成为币安广场创作者

1. 打开币安 App 或网页版
2. 进入 **广场（Square）** 板块
3. 如果尚未成为创作者，按页面提示完成创作者注册
4. **等待审批**：创作者审核通常需要 **24-48 小时**，审批通过前无法进行下一步

### 2. 申请 OpenAPI Key

> **注意**：**OpenAPI** 选项只有在创作者身份审批通过后才会出现。如果看不到该选项，请确认创作者审核已通过。

1. 进入币安广场的 **创作者后台**
2. 找到 **OpenAPI** 或 **API 管理** 选项
3. 申请创建一个 OpenAPI Key
4. 复制生成的 API Key

### 3. 配置 API Key

将 API Key 填入项目 `.env` 文件：

```
BINANCE_SQUARE_API_KEY=your_api_key_here
```

### 4. API 接口说明

**发布帖子**

```
POST https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add
```

Headers:
```
X-Square-OpenAPI-Key: {your_api_key}
Content-Type: application/json
```

Body:
```json
{
    "bodyTextOnly": "你的帖子内容"
}
```

成功响应：
```json
{
    "code": "000000",
    "message": null,
    "data": {
        "id": "post_id_here"
    }
}
```

### 5. 错误码对照

| 错误码 | 含义 | 处理 |
|--------|------|------|
| `000000` | 成功 | -- |
| `220009` | 日发帖上限 | 自动暂停至午夜 |
| `220003` | API Key 无效 | 检查 Key 是否正确 |
| `220004` | API Key 权限不足 | 联系币安客服 |
| `20002` | 内容含敏感词 | 跳过该推文 |
| `20022` | 内容审核未通过 | 跳过该推文 |
| `20013` | 内容过长 | 自动截断重试 |

## 注意事项

- API Key 属于敏感凭证，不要提交到 Git
- 每日发帖有上限（通常 50 条），超限后服务会自动暂停到第二天
- API Key 仅用于发布文字帖，不支持发布图片/视频
- 如果 Key 失效，服务会发送 CRITICAL 级别 Discord 告警
