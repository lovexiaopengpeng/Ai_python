# 后端接口文档

## 基础信息

- **服务地址**: `https://ai-python-3x1q.onrender.com`
- **本地地址**: `http://localhost:8000`
- **文档版本**: v1.0
- **更新时间**: 2026-05-28

---

## 目录

1. [认证接口](#认证接口)
2. [新闻资讯接口](#新闻资讯接口)
3. [股票接口](#股票接口)
4. [虚拟币接口](#虚拟币接口)
5. [响应状态码](#响应状态码)

---

## 认证接口

### 1. 用户注册

**接口地址**: `POST /register`

**功能描述**: 新用户注册账户

**请求体**:
```json
{
  "username": "string (手机号，必填)",
  "password": "string (密码，必填)"
}
```

**成功响应**:
```json
{
  "success": true,
  "user_id": "285617",
  "username": "13888888888",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "注册成功"
}
```

**失败响应**:
```json
{
  "success": false,
  "message": "用户已存在"
}
```

---

### 2. 用户登录

**接口地址**: `POST /login`

**功能描述**: 用户登录获取Token

**请求体**:
```json
{
  "username": "string (手机号，必填)",
  "password": "string (密码，必填)"
}
```

**成功响应**:
```json
{
  "success": true,
  "user_id": "285617",
  "username": "13888888888",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "登录成功"
}
```

**失败响应**:
```json
{
  "success": false,
  "error": "password_error",
  "message": "密码错误"
}
```

---

### 3. 重置密码

**接口地址**: `POST /reset-password`

**功能描述**: 修改用户密码

**请求体**:
```json
{
  "username": "string (手机号，必填)",
  "old_password": "string (旧密码，必填)",
  "new_password": "string (新密码，必填)"
}
```

**成功响应**:
```json
{
  "success": true,
  "message": "密码重置成功"
}
```

---

### 4. 退出登录

**接口地址**: `POST /user/logout`

**功能描述**: 用户退出登录，记录退出时间

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| Authorization | string | 是 | Bearer Token |
| userid | string | 是 | 用户ID |

**请求体**:
```json
{
  "timestamp": "string (时间戳，必填)"
}
```

**成功响应**:
```json
{
  "success": true,
  "message": "退出登录成功"
}
```

---

### 5. 获取用户信息

**接口地址**: `GET /user/profile`

**功能描述**: 获取当前登录用户的详细信息

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| Authorization | string | 是 | Bearer Token |

**成功响应**:
```json
{
  "success": true,
  "user": {
    "id": "285617",
    "username": "13888888888",
    "created_at": "2026-05-28 10:30:00",
    "last_login": "2026-05-28 10:35:00"
  }
}
```

---

### 6. 注销用户账户

**接口地址**: `POST /user/delete`

**功能描述**: 永久删除用户账户

**请求体**:
```json
{
  "username": "string (手机号，必填)",
  "password": "string (密码，必填)"
}
```

**成功响应**:
```json
{
  "success": true,
  "message": "账户注销成功"
}
```

---

### 7. 验证Token

**接口地址**: `POST /verify-token`

**功能描述**: 验证Token有效性

**请求体**:
```json
{
  "token": "string (JWT Token，必填)"
}
```

**成功响应**:
```json
{
  "success": true,
  "user_id": "285617",
  "username": "13888888888"
}
```

---

## 新闻资讯接口

### 1. 获取热点资讯

**接口地址**: `GET /news/hot`

**功能描述**: 获取热点新闻资讯，最多返回50条

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 否 | 新闻类型（tech/finance/entertainment/sports） |

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户ID |

**成功响应**:
```json
{
  "success": true,
  "count": 50,
  "userid": "285617",
  "data": [
    {
      "title": "科技巨头发布新款AI芯片",
      "url": "https://news.sina.com.cn/xxx",
      "time": "2026-05-28 10:30:00",
      "source": "新浪财经"
    }
  ],
  "update_time": "2026-05-28 10:35:00"
}
```

---

### 2. 获取支持的新闻类型

**接口地址**: `GET /news/types`

**功能描述**: 获取系统支持的新闻分类类型

**成功响应**:
```json
{
  "success": true,
  "types": [
    {"code": "tech", "name": "科技"},
    {"code": "finance", "name": "财经"},
    {"code": "entertainment", "name": "娱乐"},
    {"code": "sports", "name": "体育"}
  ]
}
```

---

## 股票接口

### 1. 获取国内股票基金动态

**接口地址**: `GET /stock/cn`

**功能描述**: 获取国内股票和基金的最新动态

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户ID |

**成功响应**:
```json
{
  "success": true,
  "count": 20,
  "userid": "285617",
  "data": [
    {
      "symbol": "上证指数",
      "name": "上证指数",
      "price": "3,256.80",
      "change": "+1.25%",
      "volume": "2.3亿",
      "time": "2026-05-28 10:30:00",
      "source": "新浪财经"
    }
  ],
  "update_time": "2026-05-28 10:35:00"
}
```

---

### 2. 获取美股最新动态

**接口地址**: `GET /stock/us`

**功能描述**: 获取美股市场最新动态，数据来源包括WSJ、Yahoo Finance等

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户ID |

**成功响应**:
```json
{
  "success": true,
  "count": 20,
  "userid": "285617",
  "data": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "price": "$178.50",
      "change": "+2.35%",
      "volume": "$12.5B",
      "time": "2026-05-28 10:30:00",
      "source": "Yahoo Finance",
      "url": "https://finance.yahoo.com/quote/AAPL"
    }
  ],
  "update_time": "2026-05-28 10:35:00"
}
```

---

### 3. 查询股票/基金历史行情

**接口地址**: `GET /stock/history`

**功能描述**: 查询某股票或基金的历史涨跌行情

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票/基金代码 |
| start_date | string | 是 | 开始日期 (YYYY-MM-DD) |
| end_date | string | 是 | 结束日期 (YYYY-MM-DD) |

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户ID |

**成功响应**:
```json
{
  "success": true,
  "symbol": "sh600519",
  "name": "贵州茅台",
  "userid": "285617",
  "data": [
    {
      "date": "2026-05-28",
      "open": "1,850.00",
      "close": "1,865.50",
      "high": "1,870.00",
      "low": "1,845.00",
      "volume": "125600"
    }
  ],
  "update_time": "2026-05-28 10:35:00"
}
```

---

## 虚拟币接口

### 1. 获取主流虚拟币大额买卖情况

**接口地址**: `GET /crypto/large-trades`

**功能描述**: 获取主流虚拟币的大额交易情况，数据来源包括Binance、CoinGecko等

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户ID |

**成功响应**:
```json
{
  "success": true,
  "count": 50,
  "userid": "285617",
  "data": [
    {
      "symbol": "BTC/USDT",
      "price": "$75,587.00",
      "change": "-1.59%",
      "volume": "$37,256,768,692",
      "platform": "Binance",
      "time": "2026-05-28 10:30:00",
      "type": "spot",
      "url": "https://www.binance.com/en/trade/BTC_USDT"
    }
  ],
  "update_time": "2026-05-28 10:35:00"
}
```

---

### 2. 获取排名前100的虚拟币

**接口地址**: `GET /crypto/top-100`

**功能描述**: 获取市值排名前100的虚拟币，包含买入建议分析

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户ID |

**成功响应**:
```json
{
  "success": true,
  "count": 100,
  "userid": "285617",
  "data": [
    {
      "rank": 1,
      "symbol": "BTC",
      "name": "Bitcoin",
      "price": "$75,587.00",
      "price_usd": 75587,
      "market_cap": "$1,514,031,928,440",
      "market_cap_usd": 1514031928440,
      "volume_24h": "$37,256,768,692",
      "volume_24h_usd": 37256768692,
      "change_24h": "-1.59%",
      "change_7d": "+2.30%",
      "change_30d": "+5.80%",
      "buy_signal": {
        "buy": true,
        "confidence": "high",
        "score": 65,
        "reasons": ["RSI低于30，超卖状态", "成交量活跃"],
        "risk_level": "low"
      },
      "platform": "CoinGecko",
      "time": "2026-05-28 10:30:00",
      "url": "https://www.coingecko.com/en/coins/bitcoin"
    }
  ],
  "buy_recommend": {
    "count": 40,
    "data": [...]
  },
  "not_recommend": {
    "count": 60,
    "data": [...]
  },
  "update_time": "2026-05-28 10:35:00"
}
```

**买入建议说明**:

| 评分范围 | 买入建议 | 置信度 | 风险等级 |
|---------|---------|--------|---------|
| ≥55 | 买入 | high | low |
| 35-54 | 买入 | medium | medium |
| 20-34 | 不买入 | low | medium-high |
| <20 | 不买入 | very_low | high |

---

### 3. 查询特定虚拟币详情

**接口地址**: `GET /crypto/coin/{symbol}`

**功能描述**: 查询特定虚拟币的详细信息，包含买入建议分析

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 虚拟币符号（如 BTC、ETH、SOL），不区分大小写 |

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户ID |

**成功响应**:
```json
{
  "success": true,
  "symbol": "BTC",
  "name": "Bitcoin",
  "price": "$75,587.00",
  "price_usd": 75587,
  "market_cap": "$1,514,031,928,440",
  "market_cap_usd": 1514031928440,
  "volume_24h": "$37,256,768,692",
  "volume_24h_usd": 37256768692,
  "change_24h": "-1.59%",
  "change_7d": "+2.30%",
  "change_30d": "+5.80%",
  "rank": 1,
  "circulating_supply": 19612687,
  "max_supply": 21000000,
  "high_24h": "$76,250.00",
  "low_24h": "$74,800.00",
  "buy_signal": {
    "buy": true,
    "confidence": "high",
    "score": 65,
    "reasons": ["RSI低于30，超卖状态", "成交量活跃"],
    "risk_level": "low"
  },
  "platform": "CoinGecko",
  "time": "2026-05-28 10:30:00",
  "url": "https://www.coingecko.com/en/coins/bitcoin",
  "userid": "285617"
}
```

**失败响应**:
```json
{
  "success": false,
  "message": "未找到虚拟币: BTC"
}
```

**使用示例**:
```bash
# 查询比特币详情
curl -X GET https://ai-python-3x1q.onrender.com/crypto/coin/BTC -H "userid: 285617"

# 查询以太坊详情
curl -X GET https://ai-python-3x1q.onrender.com/crypto/coin/ETH -H "userid: 285617"
```

---

## 响应状态码

| 状态码 | 说明 | 典型场景 |
|--------|------|---------|
| 200 | 成功 | 请求正常处理 |
| 400 | 请求参数错误 | 缺少必要参数或格式错误 |
| 401 | 未授权 | Token无效、过期或未提供 |
| 403 | 禁止访问 | 权限不足 |
| 404 | 资源未找到 | 用户不存在或接口不存在 |
| 500 | 服务器内部错误 | 数据库错误或API调用失败 |

---

## 使用示例

### cURL 示例

```bash
# 用户登录
curl -X POST https://ai-python-3x1q.onrender.com/login \
  -H "Content-Type: application/json" \
  -d '{"username": "13888888888", "password": "88888888"}'

# 获取虚拟币排名
curl -X GET https://ai-python-3x1q.onrender.com/crypto/top-100 \
  -H "userid: 285617"

# 获取新闻资讯
curl -X GET "https://ai-python-3x1q.onrender.com/news/hot?type=finance" \
  -H "userid: 285617"
```

---

## 备注

1. 所有需要 `userid` 的接口，该参数需放在请求头中
2. Token有效期为24小时，过期后需要重新登录
3. 股票和虚拟币数据来自实时API，可能存在延迟
4. 部署地址可能因服务器负载原因响应较慢
5. 数据来源包括：新浪财经、WSJ、Yahoo Finance、CoinGecko、Binance等
6. 买入建议仅供参考，不构成投资建议