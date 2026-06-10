# 后端接口文档

## 基础信息

- **服务地址**: `http://111.230.110.33`
- **本地地址**: `http://localhost:8000`
- **文档版本**: v1.3
- **更新时间**: 2026-06-05

---

## 目录

1. [认证接口](#认证接口)
2. [新闻资讯接口](#新闻资讯接口)
3. [股票接口](#股票接口)
4. [虚拟币接口](#虚拟币接口)
5. [美团美食接口](#美团美食接口)
6. [企业微信机器人接口](#企业微信机器人接口)
7. [天气播报接口](#天气播报接口)
8. [响应状态码](#响应状态码)

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

### 7. 查询用户信息

**接口地址**: `POST /user_info`

**功能描述**: 根据 userid 查询用户的完整信息（需要管理员权限）

**请求体**:
```json
{
  "userid": "string (用户 ID，必填)"
}
```

**请求参数说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户 ID |

**成功响应**:
```json
{
  "userid": "34442",
  "username": "张三",
  "email": "zhangsan@example.com",
  "phone": "13800138000",
  "created_at": "2024-01-01 12:00:00",
  "last_login": "2026-06-05 10:30:00",
  "success": true
}
```

**用户不存在响应**:
```json
{
  "userid": "34442",
  "username": null,
  "success": false,
  "error": "用户不存在"
}
```

**查询失败响应**:
```json
{
  "userid": "34442",
  "success": false,
  "error": "(1054, \"Unknown column 'user_id' in 'where clause'\")"
}
```

**使用示例**:
```bash
# 查询用户信息
curl -X POST http://111.230.110.33/user_info \
  -H "Content-Type: application/json" \
  -d '{"userid": "34442"}'
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
curl -X GET http://111.230.110.33/crypto/coin/BTC -H "userid: 285617"

# 查询以太坊详情
curl -X GET http://111.230.110.33/crypto/coin/ETH -H "userid: 285617"
```

---

### 4. 收藏虚拟币

**接口地址**: `POST /crypto/favorites`

**功能描述**: 收藏指定的虚拟币

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户ID |

**请求体**:
```json
{
    "symbol": "BTC",
    "name": "Bitcoin"
}
```

**响应示例**:
```json
{
    "success": true,
    "message": "收藏成功"
}
```

**使用示例**:
```bash
# 收藏比特币
curl -X POST http://111.230.110.33/crypto/favorites \
    -H "Content-Type: application/json" \
    -H "userid: 285617" \
    -d '{"symbol": "BTC", "name": "Bitcoin"}'
```

---

### 5. 取消收藏虚拟币

**接口地址**: `DELETE /crypto/favorites/{symbol}`

**功能描述**: 取消收藏指定的虚拟币

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 虚拟币符号 |

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户ID |

**响应示例**:
```json
{
    "success": true,
    "message": "取消收藏成功"
}
```

**使用示例**:
```bash
# 取消收藏比特币
curl -X DELETE http://111.230.110.33/crypto/favorites/BTC -H "userid: 285617"
```

---

### 6. 获取收藏的虚拟币列表

**接口地址**: `GET /crypto/favorites`

**功能描述**: 获取当前用户收藏的所有虚拟币

**请求头**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userid | string | 是 | 用户ID |

**响应示例**:
```json
{
    "success": true,
    "count": 2,
    "favorites": [
        {
            "symbol": "BTC",
            "name": "Bitcoin",
            "created_at": "2026-05-28 10:30:00"
        },
        {
            "symbol": "ETH",
            "name": "Ethereum",
            "created_at": "2026-05-28 11:00:00"
        }
    ]
}
```

**使用示例**:
```bash
# 获取收藏列表
curl -X GET http://111.230.110.33/crypto/favorites -H "userid: 285617"
```

---

## 美团美食接口

### 1. 获取美团外卖商家列表

**接口地址**: `GET /meituan/food`

**功能描述**: 获取美团外卖商家列表

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
      "name": "肯德基(万达广场店)",
      "rating": 4.8,
      "min_price": 25,
      "delivery_time": "30分钟",
      "distance": "1.2km",
      "tags": ["快餐", "炸鸡"],
      "icon": "https://xxx"
    }
  ],
  "update_time": "2026-06-02 16:30:00"
}
```

---

## 企业微信机器人接口

### 1. 发送企业微信消息（支持定时）

**接口地址**: `POST /wechat/send`

**功能描述**: 发送企业微信消息，支持定时发送

**请求体**:
```json
{
  "is_daily": true,
  "send_time": "14:30",
  "content": "你好呀，今天又是nice的一天呀"
}
```

**请求参数说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| is_daily | boolean | 是 | 是否每日定时发送 |
| send_time | string | 是 | 发送时间，格式：HH:MM |
| content | string | 是 | 发送内容 |

**成功响应**:
```json
{
  "success": true,
  "message": "消息任务已创建",
  "data": {
    "message_id": 1,
    "is_daily": true,
    "send_time": "14:30",
    "status": "scheduled"
  }
}
```

---

### 2. 立即发送企业微信消息

**接口地址**: `POST /wechat/send-now`

**功能描述**: 立即发送企业微信消息

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string | 是 | 发送内容 |

**成功响应**:
```json
{
  "success": true,
  "message": "消息发送成功"
}
```

**使用示例**:
```bash
# 立即发送消息
curl -X POST "http://111.230.110.33/wechat/send-now?content=你好世界"
```

---

### 3. 获取企业微信消息列表

**接口地址**: `GET /wechat/messages`

**功能描述**: 获取企业微信消息列表

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 筛选状态（scheduled/sent/failed/cancelled） |

**成功响应**:
```json
{
  "success": true,
  "count": 3,
  "messages": [
    {
      "id": 1,
      "is_daily": true,
      "send_time": "14:30",
      "content": "你好呀",
      "status": "scheduled",
      "created_at": "2026-06-02 10:00:00"
    }
  ]
}
```

---

### 4. 获取单个企业微信消息

**接口地址**: `GET /wechat/messages/{message_id}`

**功能描述**: 获取单个企业微信消息详情

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message_id | integer | 是 | 消息ID |

**成功响应**:
```json
{
  "success": true,
  "message": {
    "id": 1,
    "is_daily": true,
    "send_time": "14:30",
    "content": "你好呀",
    "status": "scheduled"
  }
}
```

---

### 5. 取消企业微信消息

**接口地址**: `DELETE /wechat/messages/{message_id}`

**功能描述**: 取消企业微信消息

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message_id | integer | 是 | 消息ID |

**成功响应**:
```json
{
  "success": true,
  "message": "消息已取消"
}
```

---

## 天气播报接口

### 1. 获取天气播报配置

**接口地址**: `GET /weather/config`

**功能描述**: 获取天气播报配置

**成功响应**:
```json
{
  "success": true,
  "config": {
    "id": 1,
    "city": "长沙",
    "district": "岳麓区",
    "send_time": "13:50",
    "enabled": true
  }
}
```

---

### 2. 更新天气播报配置

**接口地址**: `POST /weather/config`

**功能描述**: 更新天气播报配置

**请求体**:
```json
{
  "city": "长沙",
  "district": "岳麓区",
  "send_time": "13:50",
  "enabled": true
}
```

**请求参数说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| city | string | 是 | 城市名称 |
| district | string | 是 | 区县名称 |
| send_time | string | 是 | 发送时间，格式：HH:MM |
| enabled | boolean | 是 | 是否启用 |

**成功响应**:
```json
{
  "success": true,
  "message": "配置已更新"
}
```

---

### 3. 立即发送天气播报

**接口地址**: `POST /weather/send-now`

**功能描述**: 立即发送天气播报

**成功响应**:
```json
{
  "success": true,
  "message": "天气播报已发送"
}
```

---

### 4. 获取当前天气信息

**接口地址**: `GET /weather/current`

**功能描述**: 获取当前天气信息（使用阿里云 DashScope API）

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| location | string | 否 | 地点名称，默认：长沙市岳麓区 |

**成功响应**:
```json
{
  "success": true,
  "message": "天气信息获取成功",
  "data": {
    "success": true,
    "location": "长沙市岳麓区",
    "dashscope_response": {
      "output": {
        "text": "🌤️ 【每日天气播报】...",
        "finish_reason": "stop"
      },
      "usage": {
        "models": [
          {
            "input_tokens": 10,
            "output_tokens": 200
          }
        ]
      }
    },
    "update_time": "2026-06-02 16:30:00"
  }
}
```

**使用示例**:
```bash
# 获取长沙市岳麓区天气
curl "http://111.230.110.33/weather/current?location=长沙市岳麓区"
```

---

### 5. 安排天气播报任务

**接口地址**: `POST /weather/schedule`

**功能描述**: 安排天气播报定时任务

**请求体**:
```json
{
  "send_time": "14:30",
  "is_daily": true
}
```

**请求参数说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| send_time | string | 是 | 发送时间，格式：HH:MM |
| is_daily | boolean | 是 | 是否每日发送 |

**成功响应**:
```json
{
  "success": true,
  "message": "每日天气播报任务已安排",
  "data": {
    "send_time": "14:30",
    "is_daily": true,
    "job_id": "weather_custom_daily_14:30",
    "location": "长沙市岳麓区"
  }
}
```

---

### 6. 获取所有天气播报任务

**接口地址**: `GET /weather/jobs`

**功能描述**: 获取所有天气播报定时任务

**成功响应**:
```json
{
  "success": true,
  "count": 1,
  "jobs": [
    {
      "id": "weather_custom_daily_14:30",
      "type": "daily",
      "trigger": "cron[hour='14', minute='30']",
      "next_run_time": "2026-06-03 14:30:00+08:00"
    }
  ]
}
```

---

### 7. 天气播报调试接口

**接口地址**: `GET /weather/debug`

**功能描述**: 获取天气播报调试信息

**成功响应**:
```json
{
  "success": true,
  "data": {
    "scheduler_running": true,
    "current_time": "2026-06-02 16:30:00",
    "timezone": "Asia/Shanghai",
    "weather_config": {
      "id": 1,
      "city": "长沙",
      "district": "岳麓区",
      "send_time": "13:50",
      "enabled": true
    },
    "jobs_count": 1,
    "jobs": [
      {
        "id": "weather_custom_daily_14:30",
        "next_run_time": "2026-06-03 14:30:00+08:00"
      }
    ]
  }
}
```

---

### 8. 测试天气播报功能

**接口地址**: `POST /weather/test`

**功能描述**: 立即测试天气播报功能

**成功响应**:
```json
{
  "success": true,
  "message": "测试消息已发送"
}
```

---

### 9. 取消指定的天气播报任务

**接口地址**: `POST /weather/cancel/{job_id}`

**功能描述**: 取消指定的天气播报定时任务

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| job_id | string | 是 | 任务ID |

**成功响应**:
```json
{
  "success": true,
  "message": "任务 weather_custom_daily_14:30 已取消"
}
```

**使用示例**:
```bash
# 取消指定任务
curl -X POST http://111.230.110.33/weather/cancel/weather_custom_daily_14:30
```

---

### 10. 取消所有天气播报任务

**接口地址**: `POST /weather/cancel-all`

**功能描述**: 取消所有天气播报定时任务

**成功响应**:
```json
{
  "success": true,
  "message": "已取消所有天气播报定时任务",
  "removed_count": 2,
  "removed_jobs": [
    "weather_custom_daily_14:30",
    "weather_report_daily"
  ],
  "weather_config_enabled": false
}
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
curl -X POST http://111.230.110.33/login \
  -H "Content-Type: application/json" \
  -d '{"username": "13888888888", "password": "88888888"}'

# 获取虚拟币排名
curl -X GET http://111.230.110.33/crypto/top-100 \
  -H "userid: 285617"

# 获取新闻资讯
curl -X GET "http://111.230.110.33/news/hot?type=finance" \
  -H "userid: 285617"

# 立即发送企业微信消息
curl -X POST "http://111.230.110.33/wechat/send-now?content=你好世界"

# 安排定时发送企业微信消息
curl -X POST http://111.230.110.33/wechat/send \
  -H "Content-Type: application/json" \
  -d '{"is_daily": true, "send_time": "14:30", "content": "你好呀"}'

# 获取长沙市岳麓区天气
curl "http://111.230.110.33/weather/current?location=长沙市岳麓区"

# 安排每日天气播报任务
curl -X POST http://111.230.110.33/weather/schedule \
  -H "Content-Type: application/json" \
  -d '{"send_time": "14:30", "is_daily": true}'

# 查看所有天气播报任务
curl http://111.230.110.33/weather/jobs

# 取消指定天气播报任务
curl -X POST http://111.230.110.33/weather/cancel/weather_custom_daily_14:30
```

---

## 备注

1. 所有需要 `userid` 的接口，该参数需放在请求头中
2. Token有效期为24小时，过期后需要重新登录
3. 股票和虚拟币数据来自实时API，可能存在延迟
4. 部署地址可能因服务器负载原因响应较慢
5. 数据来源包括：新浪财经、WSJ、Yahoo Finance、CoinGecko、Binance、阿里云 DashScope 等
6. 买入建议仅供参考，不构成投资建议
7. 天气播报任务使用 `Asia/Shanghai` 时区（北京时间）