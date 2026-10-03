# socratic-mirror

<p align="center"><img src="assets/socrates-hero.jpg" alt="戴着墨镜的苏格拉底说 &quot;Know thyself.&quot;" width="100%"></p>

> 基于 Claude Code 对话记录的苏格拉底式自我诘问

[English](README.md) · [한국어](README.ko.md) · **简体中文**

这是一个 Claude Code 插件。它会在你过去与 Claude 的对话中，找出一个你反复默认、却从未拿出证据的前提，然后只用提问来追问它。不给建议，也不安慰。当你承认这个前提站不住脚时，它只说一句 `Aporia.`（困惑）便停下。

```
> /socrates
这个工具只提问，不安慰。随时输入 `stop` 即可结束。
你反复假设"客户只在乎价格"。
  "they'll just pick the cheapest" (2026-09-02) / "price is the only lever" (2026-09-18)
那为什么你最贵的那位客户续约了两次？
> ……他们对售后服务很满意。
```

（以上对话为说明用的虚构示例。）

## 安装

在 Claude Code 中运行以下两行：

```
/plugin marketplace add qjc-office/socratic-mirror
/plugin install socratic-mirror
```

需要 Python 3.9 或更高版本（macOS 已预装）。

## 用法

| 命令 | 作用 |
|---|---|
| `/socrates` | 从当前项目最近 30 天的对话中挑出一个前提并进行诘问 |
| `/socrates triad` | 轮流使用三种视角：苏格拉底（反例诘问）、孔子（正名：你给自己定的角色和实际行为是否一致）、佛陀（十二因缘：追溯执着最初的触点）。只有三者的结论指向同一处时，才宣告 `Triple aporia.` |
| `/socrates close` | 收尾：用三行总结（你误以为的事、真正该回答的问题、今天就改的一个行动），再拆成本周三个行动，并写入日志 |
| `--days N` | 修改时间范围（默认 30 天） |
| `--all-projects` | 使用所有项目的对话 |

"当前项目"指：如果你在 git 仓库里，就是整个仓库；否则是从当前文件夹开始的对话。随时输入 `stop` 即可结束。

## 隐私

- 对话记录（`~/.claude/projects`）只在本机读取，插件本身不发起任何网络请求。
- 但提取出的发言会像普通对话一样发送给模型提供方（Anthropic），相当于你亲手粘贴给 Claude。
- 看起来像 API 密钥的字符串会先被遮盖，但无法保证拦住所有密钥。
- 诘问日志保存在 `~/.socratic-mirror/log.md`，权限为仅本人可读（600）。
- 每次运行会在 `~/.socratic-mirror/cache/` 生成临时提取文件，分析结束后立即删除；未能清理的残留文件会在下次运行时删除超过 1 小时的部分。
- 删除 `~/.socratic-mirror` 文件夹即可清除全部数据。

## 安全

这是一个只提问、不安慰的工具，情绪低落时可能并不合适。如果对话中出现危机信号，它会停止诘问并引导你寻求帮助（在韩国请拨打 109；其他地区请联系当地紧急电话或心理危机热线）。本插件不能替代心理咨询或治疗。

## 来源

诘问提示词改编自社交媒体上分享的提示词。

## 已知限制

- Claude Code 的对话记录格式不是公开规范，可能随版本变化。如果有记录却提取不出任何内容，插件会说明原因并停止（退出码 3）。欢迎提交 issue。
- 你粘贴的日志或代码也会被当作你说的话。分析阶段会尽量过滤，但并不完美。
- 为了速度，`--days` 会先按文件修改时间筛选会话文件。从备份恢复、修改时间较旧的会话文件可能被跳过。

## 开发

```
python3 -m pytest              # 单元测试
bash scripts/run-evals.sh      # 行为评测（在 Claude Code 会话之外的普通终端中运行）
```

## 许可证

MIT
