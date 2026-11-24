# 接口自动化测试框架（Python + Requests + pytest）

针对公开 REST API 的接口自动化测试项目。把「手工点 Postman 看返回」换成
「一条命令批量执行、自动判定对错、失败可回溯」。

```text
============================= 22 passed in 10.36s ==============================
```

被测对象：[JSONPlaceholder](https://jsonplaceholder.typicode.com)（主站）+ [httpbin](https://httpbin.org)（异常场景站）。
两者都是公开的假数据服务，**不含任何私有接口、账号或密钥，克隆后可直接运行**。

---

## 项目定位

接口测试是手工测试里最重复、最适合自动化的部分：用例固定、执行频繁、判断标准明确。
这个项目解决四个具体问题：

| 手工测试的痛点 | 本项目的做法 |
|---|---|
| 换个环境就要全局替换地址，改漏一处就是一个假失败 | 环境地址抽到 `config.ini`，改配置、用例代码零改动 |
| 出了问题不知道当时到底发了什么请求 | 每次请求/响应落日志：方法、地址、参数、状态码、耗时 |
| 每次都要人眼判断对错 | pytest `assert` 断言，跑完直接给结论 |
| 加一条用例要改代码、找开发 | 用例外置到 Excel，加一行数据就多一条用例 |

---

## 快速验证（3 条命令）

```bash
git clone https://github.com/<your-name>/api-auto-test.git
cd api-auto-test
pip install -r requirements.txt
python -m pytest
```

预期输出：`22 passed`，并在 `reports/report.html` 生成测试报告。

> Windows 下若提示 `pytest` 不是内部或外部命令，用 `python -m pytest` 代替。
> 若控制台中文显示为乱码，先执行 `chcp 65001` 切到 UTF-8。

常用筛选：

```bash
python -m pytest -m smoke        # 只跑冒烟用例（核心链路）
python -m pytest -m negative     # 只跑负向用例（异常场景）
python -m pytest -k "TC-005"     # 只跑某一条
```

---

## 目录结构

```text
api-auto-test/
├── common/
│   ├── config_reader.py    # 读 config.ini，对外暴露 BASE_URL / ALT_BASE_URL / TIMEOUT
│   ├── logger.py           # 日志：控制台 + 文件双输出
│   ├── request_client.py   # 请求层：拼域名、记日志、统一超时、安全解析 JSON
│   └── excel_reader.py     # 数据层：把 Excel 的每一行解析成用例字典
├── data/
│   └── test_cases.xlsx     # 14 条数据驱动用例（测试人员可直接编辑）
├── tests/
│   ├── test_posts.py       # 5 条代码用例（含链路与结构断言）
│   └── test_data_driven.py # 数据驱动执行器 + 用例表自身校验
├── docs/
│   └── report-sample.html  # 一份实测生成的报告样例（下载后用浏览器打开）
├── conftest.py             # pytest 夹具：api / api_alt / 测试数据
├── config.ini              # 环境配置（主站 + 异常场景站）
├── pytest.ini              # 用例发现规则、标记、默认参数、HTML 报告
└── requirements.txt
```

---

## 用例设计

共 **22 条**：14 条来自 Excel（数据驱动），5 条写在代码里（含跨接口链路），3 条用于校验用例表本身。

### 数据驱动部分（`data/test_cases.xlsx`）

| 编号 | 用例 | 请求 | 期望 | 类型 |
|---|---|---|---|---|
| TC-001 | 查询单条文章 | `GET /posts/1` | 200；id=1；title/body/userId 齐全 | 正向 |
| TC-002 | 按用户过滤列表 | `GET /posts?userId=1` | 200；恰好 10 条 | 正向 |
| TC-003 | 查询全部文章 | `GET /posts` | 200；恰好 100 条 | 正向 |
| TC-004 | 查询用户详情 | `GET /users/1` | 200；id/name/email 齐全 | 正向 |
| TC-005 | 新建文章 | `POST /posts` | **201**；title 回显一致；返回新 id | 正向 |
| TC-006 | 全量更新 | `PUT /posts/1` | 200；id=1；title 被覆盖 | 正向 |
| TC-007 | 局部更新 | `PATCH /posts/1` | 200；只改 title，id 不变 | 正向 |
| TC-008 | 删除文章 | `DELETE /posts/1` | 200；响应体为空对象 | 正向 |
| TC-009 | 查询不存在的文章 | `GET /posts/999999` | **404** | 负向 |
| TC-010 | 访问不存在的路径 | `GET /nonexistent-path` | **404** | 负向 |
| TC-011 | 对已有资源用错方法 | `POST /posts/1` | **404**（该站未按规范返回 405） | 负向 |
| TC-012 | 请求参数非法 | `GET /status/400`（alt） | **400** | 负向 |
| TC-013 | 方法不允许 | `POST /get`（alt） | **405** | 负向 |
| TC-014 | 服务端错误 | `GET /status/500`（alt） | **500** | 负向 |

> 为什么需要第二个环境：主站只会返回 404，想让接口返回 400 / 405 / 500 它做不到。
> 而 4xx 家族里 400（请求本身有问题）和 405（方法不允许）是真实项目里最常见的两类，
> 必须能覆盖到，所以用 httpbin 补齐。
>
> TC-012 用的是 httpbin 的状态码桩，属于「接口约定」验证，不代表真实业务参数校验；
> TC-013 则是 httpbin 路由层的真实拒绝 —— 它的响应体是一整页 HTML，正好能验证
> `safe_json()` 的兜底逻辑。

### 代码部分（`tests/test_posts.py`）

| 用例 | 断言点 | 类型 |
|---|---|---|
| `test_get_single_post` | 200；id 命中；关键字段齐全 | 正向 |
| `test_get_posts_filtered_by_user` | 200；返回列表；恰好 10 条；**每条** userId 都是 1 | 正向（含边界） |
| `test_create_post` | **201**；提交内容被正确回显；服务端分配新 id | 正向 |
| `test_get_nonexistent_post_returns_404` | 404 | 负向 |
| `test_delete_post` | 200；响应体不含业务数据 | 正向 |

负向用例的意义：验证系统**在该报错的时候确实报错**。
只写正向用例只能证明「功能能用」；写得出负向用例，才说明在设计测试。

---

## 怎么加一条用例（不用改代码）

1. 打开 `data/test_cases.xlsx`，在末尾追加一行；
2. 「启用」列填 `Y`；
3. 执行 `python -m pytest`，新用例自动生效。

字段说明见 Excel 里的 `填写说明` 工作表。环境、方法、启用三列都做了下拉选项，避免手填拼错。

**为什么要把用例搬到 Excel**：用例本质是数据，不是代码。测试人员改 Excel 不需要懂 Python，
改完直接跑。但代价也要清楚 —— Excel 表达不了复杂逻辑，凡是要「先造数据再用」「上一步返回值喂给下一步」
的链路用例，写成代码更清楚。所以本项目两种方式并存，真实项目里也是这么分工的。

---

## 测试报告

每次执行都会生成 `reports/report.html`（单文件、CSS/JS 内嵌，可直接发给别人打开）。

`docs/report-sample.html` 是一份实测生成的样例，下载后用浏览器打开可以看到：

- 顶部统计：通过 / 失败 / 跳过条数、总耗时、执行环境
- 每条用例的耗时与结果
- **失败用例自动附带「Captured log」**：失败前发了什么请求、拿到什么响应，不用额外写 `print`

---

## 设计说明

**1. 为什么 `base_url` 放进配置文件**
测试代码里写死域名，换环境就要全局替换，改漏一处就是一个假失败。现在地址只在 `config.ini` 改一次，
请求层在发请求前才拼上域名，用例只写相对路径 `api.get("/posts/1")`。

**2. 为什么请求层单独抽出来**
不封装的话，每条用例都得写 `requests.get(url, headers=..., timeout=...)`，日志也要每条自己记。
现在所有请求走同一个 `_send()`，加日志、改超时、加鉴权都只改一处 —— 这是能扩展到几十条用例的前提。

**3. 断言为什么先判状态码，再判内容**
状态码不对时，响应体根本没有解析的意义。先判状态码，失败信息也更直接（`期望 201，实际 200`），
而不是让人去猜「为什么 `KeyError: 'id'`」。

**4. 为什么数据驱动用例在「收集阶段」读 Excel**
pytest 需要提前知道有多少条用例才能排版号、算进度，所以在模块导入时一次性读完，
用 `parametrize` 生成全部用例。代价是改完 Excel 必须重新执行 pytest，热更新做不到 —— 这个代价可接受。

**5. 为什么 4xx/5xx 的用例不检查响应体**
只有成功响应才去校验字段。异常响应的格式并不固定（可能 HTML、可能空、可能 JSON），
硬去解析只会得到一堆和真正问题无关的报错，反而掩盖了「状态码不对」这个关键信息。

**6. `safe_json()` 是踩坑之后加的**
不能假设「响应体一定是 JSON」。同一个 404：

- 业务后端可能返回 `{"detail": "Not Found"}`
- 网关 / 负载均衡通常返回一整页 HTML（`<html><head>...`）

第二种情况下 `resp.json()` 抛 `JSONDecodeError`，一条本来就预期失败的用例反而把整个进程带崩。
`safe_json()` 解析失败时返回默认值，不抛异常。

这个坑还附带一个排查技巧：**看 404 的响应体格式就能判断请求走到了哪一层** ——
JSON 说明进了业务层（资源本身找不到），HTML 说明被网关拦住了（路由或发布问题）。

**7. 为什么用 `data.get("id")` 而不是 `data["id"]`**
字段缺失时 `data["id"]` 抛 `KeyError`，报错信息只有一行；
`data.get("id")` 返回 `None`，断言会明确告诉你「id 应为 1，实际 None」。

**8. 为什么要校验用例表本身**
`TestCaseTable` 那 3 条用例检查的是 Excel：编号是否重复、必填项是否为空、
负向用例的期望状态码是否真的 ≥400。最后一条能抓出一类隐蔽错误 ——
把一条本该报错的用例写成期望 200，等于把 bug 当成正确行为固定下来，比漏测更危险。

---

## 已知限制与后续计划

诚实记录当前版本的边界，避免夸大：

- [ ] 用例之间相互独立，尚无「新建 → 查询 → 删除」的跨接口链路用例
- [ ] 断言只校验状态码与关键字段，尚未引入 JSON Schema 做结构校验
- [ ] 未做并发与性能测试（接口耗时仅记录，未设阈值断言）
- [ ] 未接入测试数据清理机制（依赖被测站点不真实落库）

---

## 技术栈

Python 3.10+ / Requests / pytest / pytest-html / openpyxl / GitHub Actions
