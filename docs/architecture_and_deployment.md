# TradingAgents-Astock 代码结构与部署说明

本文档用于快速理解本地代码库的结构、核心流程、安装方式、服务启动/重启方式，以及常见运行问题。

## 1. 项目定位

TradingAgents-Astock 是一个面向 A 股的多 Agent 投研系统。它基于 LangGraph 编排多个分析角色，让不同 Agent 依次完成技术面、新闻、基本面、政策、资金、解禁、风险等分析，最后输出投资决策报告。

核心入口包括：

- Web UI：`web/app.py`，通过 Streamlit 提供页面。
- CLI：`cli/main.py`，通过命令 `tradingagents` 交互式运行。
- 核心图执行器：`tradingagents/graph/trading_graph.py`。

## 2. 目录结构

```text
TradingAgents-astock/
├── README.md
├── pyproject.toml
├── .env.example
├── .streamlit/
│   └── config.toml
├── web/
│   ├── app.py
│   ├── runner.py
│   ├── progress.py
│   ├── history.py
│   ├── pdf_export.py
│   └── components/
│       ├── sidebar.py
│       ├── progress_panel.py
│       └── report_viewer.py
├── cli/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── stats_handler.py
│   └── utils.py
├── tradingagents/
│   ├── default_config.py
│   ├── graph/
│   ├── agents/
│   ├── dataflows/
│   └── llm_clients/
├── tests/
├── examples/
└── docs/
```

主要模块说明：

| 路径 | 作用 |
| --- | --- |
| `web/` | Streamlit Web 页面、后台线程、进度展示、历史报告、PDF 导出 |
| `cli/` | 命令行交互入口 |
| `tradingagents/graph/` | LangGraph 工作流编排、状态初始化、checkpoint、信号解析 |
| `tradingagents/agents/` | 各类 Agent 节点：分析师、研究员、交易员、风控、组合经理 |
| `tradingagents/dataflows/` | 数据源适配层：A 股、Yahoo Finance、Alpha Vantage 等 |
| `tradingagents/llm_clients/` | LLM 供应商适配：OpenAI、Anthropic、Google、DeepSeek、Qwen 等 |
| `tests/` | 单元测试 |
| `examples/` | 示例报告和批量运行样例 |

## 3. 核心流程

### 3.1 Web 请求流程

Web UI 主入口是 `web/app.py`。

大体流程：

1. 用户在侧边栏输入股票代码或中文公司名。
2. `web/components/sidebar.py` 调用 `resolve_ticker()` 把输入解析成 6 位 A 股代码。
3. 页面把启动请求写入 `st.session_state["start_analysis"]`。
4. `web/app.py` 创建 `ProgressTracker`。
5. `web/runner.py` 启动后台线程执行分析。
6. 后台线程创建 `TradingAgentsGraph`。
7. LangGraph 按图执行各个 Agent。
8. 每个阶段完成后更新 `ProgressTracker`，页面自动刷新展示进度。
9. 最终状态写入历史 JSON，并在页面展示报告。

关键文件：

- `web/app.py`：页面状态机。
- `web/components/sidebar.py`：输入、模型配置、历史记录。
- `web/runner.py`：后台线程执行分析。
- `web/progress.py`：线程安全进度对象。
- `web/components/progress_panel.py`：实时进度渲染。
- `web/components/report_viewer.py`：最终报告展示和下载。

### 3.2 Agent 图流程

核心图在 `tradingagents/graph/setup.py` 中构建。

默认执行链路：

```text
Market Analyst
  -> Social Analyst
  -> News Analyst
  -> Fundamentals Analyst
  -> Policy Analyst
  -> Hot Money Analyst
  -> Lockup Analyst
  -> Quality Gate
  -> Bull Researcher / Bear Researcher
  -> Research Manager
  -> Trader
  -> Aggressive / Conservative / Neutral Risk Debate
  -> Portfolio Manager
  -> END
```

各阶段用途：

| 阶段 | 作用 |
| --- | --- |
| Market Analyst | 技术面、K 线、指标 |
| Social Analyst | 情绪、讨论热度 |
| News Analyst | 个股新闻、宏观新闻 |
| Fundamentals Analyst | 财报、估值、盈利能力 |
| Policy Analyst | 政策影响 |
| Hot Money Analyst | 游资、资金流、龙虎榜 |
| Lockup Analyst | 解禁、减持、股权相关风险 |
| Quality Gate | 检查报告质量 |
| Bull/Bear Researcher | 多空辩论 |
| Research Manager | 汇总研究结论 |
| Trader | 给出交易计划 |
| Risk Debate | 风险辩论 |
| Portfolio Manager | 最终 Buy/Hold/Sell 决策 |

### 3.3 状态流转

初始状态由 `tradingagents/graph/propagation.py` 创建，包含：

- `company_of_interest`
- `trade_date`
- `messages`
- `market_report`
- `fundamentals_report`
- `sentiment_report`
- `news_report`
- `policy_report`
- `hot_money_report`
- `lockup_report`
- `investment_debate_state`
- `risk_debate_state`

图执行过程中，各 Agent 会不断向状态中写入报告字段。最终由 Portfolio Manager 写入 `final_trade_decision`。

## 4. 数据源结构

主要 A 股数据源在 `tradingagents/dataflows/a_stock.py`。

当前主要来源：

| 数据源 | 用途 |
| --- | --- |
| mootdx / 通达信 | 股票列表、K 线、部分财务/F10 |
| 东方财富 | 龙虎榜、解禁、资金流、板块、个股信息、公司名搜索兜底 |
| 腾讯财经 | 实时报价、估值、市值、换手率 |
| 新浪财经 | K 线和财报 fallback |
| 同花顺 | 盈利预测等 |
| 财联社 | 全球财经快讯 |
| 百度股市通 | 概念板块、资金流相关数据 |

数据路由在 `tradingagents/dataflows/interface.py`，配置来自 `tradingagents/dataflows/config.py` 和 `tradingagents/default_config.py`。

默认 A 股配置：

```python
"data_vendors": {
    "core_stock_apis": "a_stock",
    "technical_indicators": "a_stock",
    "fundamental_data": "a_stock",
    "news_data": "a_stock",
    "signal_data": "a_stock",
}
```

## 5. 本地改动说明

本地做过一个输入体验修复，主要在：

- `tradingagents/dataflows/a_stock.py`
- `tests/test_ticker_symbol_handling.py`

改动内容：

1. 非中文输入必须是有效 A 股代码。
2. 支持 `300750`、`SH688017`、`688017.SH` 这类输入。
3. 中文公司名优先走 mootdx 股票列表解析。
4. 如果 mootdx 股票列表失败，自动走东方财富 suggest API 兜底。
5. 无法识别时给用户可读错误，而不是暴露 `not enough values to unpack` 这类底层异常。

验证示例：

```text
宁德时代 -> 300750
宝光股份 -> 600379
不是股票 -> 找不到股票
300750 -> 300750
```

## 6. 安装方式

当前本地安装目录：

```bash
/Users/gaozhichang/dev/go/baidu/TradingAgents-astock
```

Python 环境：

```bash
/Users/gaozhichang/.local/bin/python3.11
```

安装步骤：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
/Users/gaozhichang/.local/bin/python3.11 -m venv .venv
.venv/bin/pip install -e .
```

说明：

- 项目要求 Python `>=3.10`。
- 当前 `.venv` 是 Python 3.11 环境。
- 使用 `pip install -e .` 是开发模式安装，源码改动后不需要重新安装，只需要重启服务。
- 旧的 Python 3.9 环境保留在 `.venv-py39`，这个环境不满足项目 Python 版本要求。

## 7. 环境变量配置

复制 `.env.example` 或新建 `.env`：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
cp .env.example .env
```

根据使用的模型供应商填写 API Key：

```bash
MINIMAX_API_KEY=
DEEPSEEK_API_KEY=
DASHSCOPE_API_KEY=
ZHIPU_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
XAI_API_KEY=
OPENROUTER_API_KEY=
BACKEND_URL=
```

说明：

- Web 页面中可选择 LLM 供应商和模型。
- API Key 从 `.env` 读取。
- `BACKEND_URL` 用于第三方代理或兼容网关。
- 运行一次完整分析通常需要多次 LLM 调用，必须使用 API Key，不能使用普通网页订阅版。

## 8. mootdx 配置

`mootdx` 是连接通达信行情服务器的 Python 库。这个项目用它获取 A 股股票列表、K 线和部分 F10 数据。

首次使用建议运行：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
source .venv/bin/activate
python -m mootdx bestip
```

该命令会测速通达信服务器，并写入：

```text
/Users/gaozhichang/.mootdx/config.json
```

如果没有运行或服务器不可用，可能出现：

```text
not enough values to unpack (expected 2, got 0)
```

当前代码已经对公司名解析加了东方财富兜底，但 K 线和部分财务数据仍可能需要 mootdx 或其它 fallback 数据源。

## 9. 启动 Web 服务

推荐启动命令：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
STREAMLIT_SERVER_HEADLESS=true \
.venv/bin/python -m streamlit run web/app.py \
  --server.address 127.0.0.1 \
  --server.port 8501
```

访问地址：

```text
http://127.0.0.1:8501
```

也可以使用项目脚本入口：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
source .venv/bin/activate
tradingagents-web
```

不过显式 `streamlit run web/app.py` 更适合本地调试，因为地址、端口、headless 参数都清楚。

## 10. 重启服务

如果服务在当前终端运行：

1. 按 `Ctrl+C` 停止。
2. 重新执行启动命令。

如果是在 Codex/后台 session 中启动，需要先停止旧 session，再执行：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
STREAMLIT_SERVER_HEADLESS=true \
.venv/bin/python -m streamlit run web/app.py \
  --server.address 127.0.0.1 \
  --server.port 8501
```

源码修改后，由于是 editable 安装，通常只需要重启服务即可生效。

## 11. CLI 启动

交互式 CLI：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
source .venv/bin/activate
tradingagents
```

查看帮助：

```bash
tradingagents --help
```

CLI 支持 checkpoint/resume：

```bash
tradingagents --checkpoint
tradingagents --clear-checkpoints
```

## 12. 结果和缓存位置

默认配置在 `tradingagents/default_config.py`。

默认路径：

```text
~/.tradingagents/logs
~/.tradingagents/cache
~/.tradingagents/memory/trading_memory.md
```

报告 JSON 路径大致为：

```text
~/.tradingagents/logs/{ticker}/TradingAgentsStrategy_logs/full_states_log_{date}.json
```

可以通过环境变量覆盖：

```bash
export TRADINGAGENTS_RESULTS_DIR=/path/to/logs
export TRADINGAGENTS_CACHE_DIR=/path/to/cache
export TRADINGAGENTS_MEMORY_LOG_PATH=/path/to/trading_memory.md
```

## 13. 并发和多任务现状

当前 Web UI 是“每个 Streamlit session 一个任务”的设计。

现状：

- 单个浏览器会话中，只能同时跑一个分析。
- 开始分析后按钮会变为“分析进行中...”并禁用。
- 后台执行使用 `threading.Thread`。
- 多个浏览器 session 理论上可以同时跑，但不建议作为正式多用户并发方案。

主要原因：

- `tradingagents/dataflows/config.py` 使用进程级全局配置。
- 多用户选择不同模型、不同 Base URL 时，存在配置互相覆盖风险。
- 同一股票同一天并发分析会写同一个结果 JSON，可能覆盖。

如果要做正式多用户系统，建议增加：

- 任务 ID。
- 任务队列。
- 用户隔离。
- 按用户隔离历史记录。
- 持久化任务状态。
- 避免进程级全局配置。

## 14. 常见问题

### 14.1 输入公司名报错

先确认是否能解析：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
.venv/bin/python -c "from tradingagents.dataflows.a_stock import resolve_ticker; print(resolve_ticker('宁德时代'))"
```

预期输出：

```text
300750
```

如果失败，先运行：

```bash
source .venv/bin/activate
python -m mootdx bestip
```

当前代码还有东方财富兜底，通常公司名解析不应再因为 mootdx 失败而直接崩溃。

### 14.2 `not enough values to unpack`

常见来源是 mootdx 没有可用服务器配置，或通达信服务器响应异常。

处理：

```bash
source .venv/bin/activate
python -m mootdx bestip
```

### 14.3 端口绑定失败

如果 Streamlit 报端口绑定失败：

- 检查是否已有服务占用 `8501`。
- 换端口启动：

```bash
.venv/bin/python -m streamlit run web/app.py \
  --server.address 127.0.0.1 \
  --server.port 8502
```

### 14.4 修改代码后页面没变化

因为 Streamlit 进程已经加载旧代码，需要重启服务：

```bash
Ctrl+C
# 然后重新执行启动命令
```

### 14.5 `pytest` 不存在

当前 `.venv` 只安装了运行依赖，未安装 pytest。

如需跑测试：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests/test_ticker_symbol_handling.py -q
```

## 15. 推荐日常操作命令

启动：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
STREAMLIT_SERVER_HEADLESS=true \
.venv/bin/python -m streamlit run web/app.py \
  --server.address 127.0.0.1 \
  --server.port 8501
```

验证公司名解析：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
.venv/bin/python -c "from tradingagents.dataflows.a_stock import resolve_ticker; print(resolve_ticker('宁德时代'))"
```

配置 mootdx：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
source .venv/bin/activate
python -m mootdx bestip
```

查看 CLI：

```bash
cd /Users/gaozhichang/dev/go/baidu/TradingAgents-astock
source .venv/bin/activate
tradingagents --help
```

