# 接口自动化测试框架（Python + Requests + pytest）

基于公开 API [JSONPlaceholder](https://jsonplaceholder.typicode.com) 的接口自动化测试项目。
把「手工点 Postman 看返回」变成「一条命令批量执行、自动判定对错、失败可回溯」。

```
5 passed in 2.98s
```

## 项目定位

接口测试是手工测试里最重复、最适合自动化的部分：用例固定、执行频繁、判断标准明确（状态码 + 响应体字段）。
这个项目解决三个具体问题：

| 手工测试的痛点 | 本项目的做法 |
|---|---|
| 换个环境就要重改一遍地址 | 环境地址抽到 `config.ini`，改配置、用例零改动 |
| 出了问题不知道当时发了什么 | 每次请求/响应落日志（方法、地址、参数、状态码、耗时） |
| 每次都要人眼判断对错 | pytest `assert` 断言，跑完直接给结论 |

## 快速验证（3 条命令）

```bash
git clone https://github.com/<your-name>/api-auto-test.git
cd api-auto-test
pip install -r requirements.txt
python -m pytest
```

预期输出：`5 passed`。无需任何配置，被测接口是公开的。

> Windows 下若提示 `pytest` 不是内部或外部命令，用 `python -m pytest` 代替。

## 测试用例

| # | 用例 | 场景 | 断言点 | 类型 |
|---|---|---|---|---|
| 1 | `test_get_single_post` | 查单条 `GET /posts/1` | 状态码 200；id 命中；title/body/userId 字段齐全 | 正向 |
| 2 | `test_get_posts_filtered_by_user` | 带查询参数 `GET /posts?userId=1` | 状态码 200；返回列表；恰好 10 条；**每条** userId 都是 1 | 正向（含边界） |
| 3 | `test_create_post` | 新建 `POST /posts` | 状态码 **201**；title/userId 回显一致；服务端分配了新 id | 正向 |
| 4 | `test_get_nonexistent_post_returns_404` | 查不存在的资源 | 状态码 404 | **负向** |
| 5 | `test_delete_post` | 删除 `DELETE /posts/1` | 状态码 200；响应体不含业务数据 | 正向 |

第 4 条是负向用例——验证系统**在该报错时确实报错**。只写正向用例只能证明「功能能用」，写得出负向用例才说明在设计测试。

## 目录结构

```
api-auto-test/
├── common/
│   ├── config_reader.py    # 读 config.ini，对外暴露 BASE_URL / TIMEOUT
│   ├── logger.py           # 日志：控制台 + 文件双输出
│   └── request_client.py   # 请求层：拼域名、记日志、统一超时、安全解析
├── tests/
│   └── test_posts.py       # posts 资源用例（5 条）
├── conftest.py             # pytest 夹具：api 客户端、测试数据
├── config.ini              # 环境配置（base_url / timeout / 日志级别）
├── pytest.ini              # pytest 配置（用例发现规则、默认参数）
└── requirements.txt
```

## 设计说明

**1. 为什么把 base_url 放进配置文件**
测试代码里写死域名，换测试环境就要全局替换一遍，改漏一处就是一个假失败。
现在地址只在 `config.ini` 里改一次：

```ini
[server]
base_url = https://jsonplaceholder.typicode.com
timeout = 10
```

请求层在发请求前才拼上域名，用例只写相对路径 `api.get("/posts/1")`。

**2. 为什么请求层要单独抽出来**
如果不封装，每条用例都得写 `requests.get(url, headers=..., timeout=...)`，日志也要每条自己记。
现在所有请求走同一个 `_send()`，加日志、改超时、加鉴权都只改一处——这是后续能扩展到几十条用例的前提。

**3. 断言为什么先判状态码，再判内容**
状态码不对时，响应体根本没有解析的意义。先判状态码，失败信息也更直接（`期望 201，实际 200`），
而不是让人去猜「为什么 `KeyError: 'id'`」。

**4. 为什么用 `data.get("id")` 而不是 `data["id"]`**
字段缺失时，`data["id"]` 抛 `KeyError`，报错信息只有一行 KeyError；
`data.get("id")` 返回 `None`，断言会明确告诉你「id 应为 1，实际 None」。

**5. 为什么两个 fixture 的 scope 不一样**
`api` 用 `session`：客户端较重，整个测试过程复用一份，省掉重复建连接。
`new_post_payload` 用 `function`：字典是可变对象，被某条用例改过就会污染下一条，每次新建才真正隔离。

**6. `safe_json` 是踩坑之后加的**
不能假设「响应体一定是 JSON」。同一个 404：

- 业务后端可能返回 `{"detail": "Not Found"}`
- 网关 / 负载均衡通常返回一整页 HTML

第二种情况下 `resp.json()` 抛 `JSONDecodeError`，一条本来就预期失败的用例反而把整个进程带崩。
`safe_json()` 解析失败时返回默认值，不抛异常。

这个坑还附带一个排查技巧：**看 404 的响应体格式就能判断请求走到了哪一层**——
JSON 说明进了业务层（资源本身找不到），HTML 说明被网关拦住了（路由或发布问题）。

## 已知限制与后续计划

诚实记录当前版本的边界，避免夸大：

- [ ] 用例数据仍硬编码在代码和夹具里 → 计划外置到 Excel，新增一行数据即新增一条用例
- [ ] 尚未输出 HTML 报告 → 计划集成 `pytest-html`，失败用例自动带请求/响应现场
- [ ] 仅覆盖单接口 → 计划补充「新建后查询」这类跨接口链路用例
- [ ] 断言只校验状态码与关键字段 → 计划补充 JSON Schema 结构校验

## 技术栈

Python 3.10+ / Requests / pytest

## 被测对象说明

[JSONPlaceholder](https://jsonplaceholder.typicode.com) 是公开的假数据 API，
POST / PUT / DELETE 不会真实修改任何数据，适合练习与演示。
因此本项目不含任何私有接口、账号或密钥，克隆后可直接运行。
