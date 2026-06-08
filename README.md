# agent-memory-briefcase

`agent-memory-briefcase` 是一个离线、可版本化、本地优先的 Python CLI，用来维护“项目长期记忆包”。它把架构决策、约束、术语表、常用命令、风险清单、最近交付摘要、文件 ownership、测试证据整理成 Markdown / JSON 资产，并生成适合 Codex、Claude Code、以及其他 AI coding agent 的短上下文 brief。

它不调用任何 LLM API，不依赖云端服务，适合放进真实代码仓库里长期维护。

## 为什么要用

- 长期记忆和代码一起版本化，便于 review、diff、回滚。
- brief 从结构化资料压缩生成，减少每次手写上下文的成本。
- lint / check / doctor 可以在 CI 中拦截过期记忆、缺失栏目、陈旧测试证据，并输出可执行的修复建议。
- Markdown 与 JSON 同时保留，既适合人读，也适合工具消费。

## 特性

- 离线 Python 3.9+ CLI，运行时零依赖
- 可安装命令：`agent-memory-briefcase`
- 子命令：`init`、`add-decision`、`add-session`、`brief`、`lint`、`check`、`doctor`、`export`
- 项目 profile 管理
- ADR / decision 记录，自动生成 `.json` 与 `.md`
- session 摘要归档，自动生成 `.json` 与 `.md`
- 约束、禁忌、风险热点、术语表、命令清单、ownership map、测试证据清单
- 过期记忆提示
- word / token 预算截断
- Markdown / JSON / handoff 输出
- agent 交接健康报告：ready / attention / blocked、评分、门禁摘要、下一步修复建议
- `--output` 自动创建父目录
- `--check warning|error` 支持 CI 退出码

## 安装

### 本地开发安装

```bash
python -m pip install -e .
```

### 构建 wheel / sdist

```bash
python -m pip install build
python -m build
```

## 快速开始

### 1. 初始化记忆包

```bash
agent-memory-briefcase init \
  --project-name "agent-memory-briefcase" \
  --summary "Offline memory bundle tooling for AI coding agents" \
  --owner "maintainers" \
  --default-branch "main" \
  --primary-language "Python" \
  --review-after-days 21
```

初始化后会生成：

```text
.agent-memory-briefcase/
  briefcase.json
  profile.json
  constraints.md
  glossary.json
  commands.json
  ownership.json
  test_evidence.json
  decisions/
  sessions/
  exports/
```

### 2. 添加架构决策

```bash
agent-memory-briefcase add-decision \
  --title "Use JSON plus Markdown mirrored records" \
  --status accepted \
  --context "Agents need machine-readable and human-readable memory." \
  --decision "Store each decision as both JSON and Markdown." \
  --consequence "Diffs stay readable in code review." \
  --consequence "Other tools can consume the JSON form." \
  --tag storage \
  --tag docs
```

### 3. 添加一次工作 session

```bash
agent-memory-briefcase add-session \
  --summary "Bootstrap the initial CLI" \
  --change "Created argparse command surface." \
  --change "Added brief and lint engines." \
  --deliverable "Installable Python package." \
  --test "python -m unittest discover -s tests -v" \
  --risk "Glossary is still maintained manually."
```

### 4. 维护结构化资料

CLI 会初始化这些可直接版本化的文件：

- `.agent-memory-briefcase/constraints.md`
- `.agent-memory-briefcase/glossary.json`
- `.agent-memory-briefcase/commands.json`
- `.agent-memory-briefcase/ownership.json`
- `.agent-memory-briefcase/test_evidence.json`

推荐把它们像普通工程文档一样在 PR 中更新。

示例格式：

```json
{
  "terms": [
    {
      "term": "brief",
      "definition": "A compressed context package for an AI coding agent."
    }
  ]
}
```

```json
{
  "commands": [
    {
      "name": "Run tests",
      "command": "python -m unittest discover -s tests -v",
      "purpose": "Execute the regression suite"
    }
  ]
}
```

```json
{
  "owners": [
    {
      "path": "src/agent_memory_briefcase/",
      "owner": "platform-team",
      "validated_at": "2026-06-08",
      "notes": "CLI and storage logic"
    }
  ]
}
```

```json
{
  "evidence": [
    {
      "name": "unit",
      "status": "passed",
      "last_run": "2026-06-08",
      "command": "python -m unittest discover -s tests -v",
      "notes": "Core regression suite"
    }
  ]
}
```

### 5. 生成给 AI agent 的 brief

```bash
agent-memory-briefcase brief --max-words 220 --max-tokens 420
```

导出 JSON：

```bash
agent-memory-briefcase brief --format json --output build/brief.json
```

### 6. lint / CI 校验

```bash
agent-memory-briefcase lint
agent-memory-briefcase lint --check warning
agent-memory-briefcase check
agent-memory-briefcase check --check warning
```

`check` 默认对 `error` 级别返回非零退出码；如果希望 warning 也让 CI fail，使用 `--check warning`。

### 7. 生成 agent 交接健康报告

```bash
agent-memory-briefcase doctor
agent-memory-briefcase doctor --format json --output build/agent-doctor.json
agent-memory-briefcase doctor --check warning --output build/agent-doctor.md
```

`doctor` 会把 lint findings 聚合成一份“记忆包能不能信”的报告：

- `status`: `ready`、`attention` 或 `blocked`
- `score`: 0 到 100 的健康分
- `counts`: 约束、术语、命令、ownership、测试证据、decision、session 数量
- `gates`: bundle layout、profile、prompt inputs、freshness、mirrored records 等门禁
- `next_actions`: 可直接交给开发者或 agent 执行的修复建议

建议在交给新 Codex / Claude Code 线程前先跑一次：

```bash
agent-memory-briefcase doctor --check warning --output build/agent-doctor.md
```

如果 CI 希望只阻断 error，可以改用：

```bash
agent-memory-briefcase doctor --check error
```

### 8. 导出完整记忆包

```bash
agent-memory-briefcase export --format markdown --output build/memory-export.md
agent-memory-briefcase export --format json --output build/memory-export.json
```

导出给新 agent 线程的交接包：

```bash
agent-memory-briefcase export --format handoff --output build/agent-handoff.md
```

`handoff` 格式介于短 `brief` 和完整 `export` 之间，适合在 Codex、Claude Code 或其他 agent 新线程开始前粘贴。它会整理项目快照、操作约束、禁忌、风险热点、最近工作、保留决策、验证命令、测试证据、ownership 和下一步提示。

## 适配 Codex / Claude Code 的使用建议

### Codex

1. 在仓库根目录维护 `.agent-memory-briefcase/`
2. 每次重要实现后运行 `add-session`
3. 每次重要架构取舍后运行 `add-decision`
4. 在进入新任务前执行：

```bash
agent-memory-briefcase doctor --check warning
agent-memory-briefcase brief --max-words 240 --max-tokens 520
```

先用 `doctor` 确认记忆包没有过期风险，再把 `brief` 输出贴给 agent，作为紧凑上下文。

如果要把任务交给一个全新线程或另一个 agent，使用更完整的 handoff：

```bash
agent-memory-briefcase export --format handoff --output build/agent-handoff.md
```

### Claude Code

Claude Code 通常更依赖一段高信号、低噪音的项目摘要。建议：

- 先执行 `agent-memory-briefcase doctor --check warning`
- 修正过期 ownership / test evidence
- 再执行 `brief`

这样得到的 brief 更稳定，减少 agent 基于过期信息推断。`doctor` 里的 `next_actions` 也适合直接复制给下一位维护者。

## 数据模型

### `profile.json`

保存项目名、摘要、owner、默认分支、主要语言、review 周期、brief 默认预算。

### `constraints.md`

约束类信息使用 Markdown，按固定章节读取：

- `## Hard Constraints`
- `## Taboos`
- `## Risk Hotspots`

### `glossary.json`

```json
{
  "terms": [
    {
      "term": "ADR",
      "definition": "Architecture Decision Record"
    }
  ]
}
```

### `commands.json`

```json
{
  "commands": [
    {
      "name": "Lint bundle",
      "command": "agent-memory-briefcase lint",
      "purpose": "Check memory completeness"
    }
  ]
}
```

### `ownership.json`

```json
{
  "owners": [
    {
      "path": "tests/",
      "owner": "qa-team",
      "validated_at": "2026-06-08",
      "notes": "Regression coverage owner"
    }
  ]
}
```

### `test_evidence.json`

```json
{
  "evidence": [
    {
      "name": "smoke",
      "status": "passed",
      "last_run": "2026-06-08",
      "command": "python -m agent_memory_briefcase brief --help",
      "notes": "CLI smoke verification"
    }
  ]
}
```

### `decisions/*.json` and `decisions/*.md`

每个 ADR 自动产生成对文件，便于 diff 和程序消费。

### `sessions/*.json` and `sessions/*.md`

每次工作 session 的摘要归档，包括变更、交付物、测试、风险、附加 artifacts。

## 过期规则

默认根据 `profile.json` 中的 `review_after_days` 判定资料是否过期。当前规则包括：

- profile 长时间未更新
- 长时间没有新的 session 摘要
- ownership 条目验证时间过旧
- test evidence 最近执行时间过旧
- 处于 `proposed` / `trial` / `draft` 的 decision 长时间未收敛

这些提示会进入 `lint` / `check`，也会被 `brief` 汇总成 stale hints。

## CI

仓库附带 GitHub Actions 工作流，会在多个 Python 版本上运行：

```bash
python -m unittest discover -s tests -v
python -m agent_memory_briefcase check --root examples/demo_bundle --check warning
python -m agent_memory_briefcase doctor --root examples/demo_bundle --check warning --output build/agent-doctor.md
python -m agent_memory_briefcase export --root examples/demo_bundle --format handoff --output build/agent-handoff.md
```

## 隐私

- 完全本地运行
- 不发送网络请求
- 不调用任何 LLM API
- 适合放在私有仓库或内网仓库使用

## 限制

- token 预算使用字符长度近似估算，不是模型厂商官方 tokenizer
- 术语表、命令清单、ownership、测试证据目前以手工编辑 JSON 为主
- `constraints.md` 依赖固定二级标题命名
- 不是知识图谱系统，也不会自动从 Git 历史推断语义

## examples

`examples/demo_bundle/` 提供了一个可直接执行的示例：

```bash
python -m agent_memory_briefcase brief --root examples/demo_bundle
python -m agent_memory_briefcase doctor --root examples/demo_bundle
python -m agent_memory_briefcase export --root examples/demo_bundle --format json
python -m agent_memory_briefcase export --root examples/demo_bundle --format handoff
python -m agent_memory_briefcase check --root examples/demo_bundle --check warning
```

## 开发与测试

```bash
python -m unittest discover -s tests -v
python -m agent_memory_briefcase brief --root examples/demo_bundle --max-words 180 --max-tokens 360
```

## English

`agent-memory-briefcase` is an offline Python CLI for maintaining a version-controlled long-term memory bundle for AI coding agents. It stores architecture decisions, session summaries, constraints, glossary terms, common commands, ownership metadata, test evidence, and exportable brief artifacts in Markdown and JSON.

Typical workflow:

1. Run `agent-memory-briefcase init` in the repository root.
2. Record ADR-style decisions with `add-decision`.
3. Archive delivery summaries with `add-session`.
4. Maintain `constraints.md`, `glossary.json`, `commands.json`, `ownership.json`, and `test_evidence.json`.
5. Generate a concise prompt-ready context with `brief`.
6. Run `doctor` to get a readiness status, score, gate summary, and concrete next actions.
7. Export a richer new-thread handoff with `export --format handoff`.
8. Enforce freshness with `lint`, `check`, or `doctor --check warning` in CI.

The tool is local-first, has zero runtime dependencies, and never calls an external LLM API.

Handoff export:

```bash
agent-memory-briefcase export --format handoff --output build/agent-handoff.md
```

Use this when a task moves to a fresh Codex, Claude Code, or custom agent thread and you want more context than a compact brief without pasting the entire memory archive.

Doctor report:

```bash
agent-memory-briefcase doctor --format json --output build/agent-doctor.json
agent-memory-briefcase doctor --check warning --output build/agent-doctor.md
```

Use `doctor` before an agent handoff or CI run to decide whether the bundle is ready, needs attention, or is blocked by structural errors.

## License

MIT. See [LICENSE](LICENSE).
