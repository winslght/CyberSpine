## 📝 PR 变更说明 (Description)
<!-- 请简要描述此 PR 修复的问题、引入的新特性或重构的内容 -->

- 关联 Issue / RFC: Fixes #
- 变更模块: `src/...` / `docs/...` / `plugins/...`

---

## 🧪 自动化测试与质量验证 (Testing & QA)
<!-- 请根据 [docs/standards/TESTING_STRATEGY_AND_BOUNDARIES.md] 勾选以下核验项 -->

- [ ] 本地运行 `pytest tests/` 全部通过
- [ ] 遵循 [docs/standards/CODING_STANDARDS.md] 防杀软浅层只读嗅探准则 (无破坏性写操作)
- [ ] 所有时间戳与时区均符合 UTC 规范
- [ ] 字符串编解码经过 Windows GBK / UTF-8 兼容性测试
- [ ] 若新增神经末梢插件，已在 `plugins/` 提供 `manifest.json` 与测试用例

---

## 📌 贡献者签署
- [ ] 本 PR 代码完全由本人编写或符合开源协议授权，自愿遵循本项目 MIT 开源许可证。
