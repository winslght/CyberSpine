# 代码开发规范、安全准则与性能红线 (Coding Standards & Safety Policy)

**文档编号**：DOC-DEV-002  
**状态**：团队工程基准 (Approved)  
**维护者**：CyberSpine 架构委员会  

---

## 1. 编程语言与代码风格基础规范

### 1.1 Python 核心规范
* **标准基准**：严格遵循 **PEP 8** 规范，采用 4 空格缩进，行宽建议 $\le 100$ 字符；
* **全面强类型注解 (Type Hints)**：
  * 所有函数定义必须具备入参类型与返回值类型（如 `def get_device(device_id: str) -> Optional[DeviceFingerprint]:`）；
  * 严禁在公共接口中使用无约束的裸字典 `dict` 或无类型 `Any` 作为关键数据载荷。
* **数据契约标准**：
  * 统一使用 **Pydantic V2**（使用 `model_dump()` 替代已过期的 `dict()`，使用 `Field(description=...)` 标注字段含义）；
  * 结构体必须自包含合理的默认值与格式校验。

---

## 2. 跨平台时区与 Windows 编码防御规范 (Encoding & Timezone Safety)

### 2.1 时区感知规范 (Timezone-Aware UTC)
* **严禁使用** 已弃用的 `datetime.utcnow()`（会导致 Python 3.12+ 报 `DeprecationWarning` 且产生无时区盲时间戳）；
* **统一使用** 带有时区信息的 UTC 时间：
  ```python
  from datetime import datetime, timezone

  def utc_now() -> datetime:
      return datetime.now(timezone.utc)
  ```

### 2.2 Windows 终端输出编码防御 (GBK Safe Output)
* **问题背景**：Windows 默认终端（CMD/PowerShell）在中文环境下的代码页常为 `GBK (CP936)`，若在 `print()` 中直接输出特殊 Unicode 字符（如部分 Emoji）会抛出致命的 `UnicodeEncodeError`；
* **防守策略**：
  1. 所有测试与运行脚本入口应优先尝试启用 UTF-8 控制台流：
     ```python
     import sys
     if sys.stdout.encoding != 'utf-8':
         try:
             sys.stdout.reconfigure(encoding='utf-8')
         except Exception:
             pass
     ```
  2. 控制台日志与测试提示信息中，优先使用跨平台兼容的标准 ASCII 标记（如 `[PASS]`, `[FAIL]`, `[INFO]`），避免控制台因编码崩溃。

---

## 3. 硬件非侵入式探测与防杀软误判准则 (Non-Intrusive Safety Policy)

这是 CyberSpine 最核心的生命线准则。系统必须像影子一样安静无害，从物理上杜绝 Windows Defender 误判或引发系统发热。

### 3.1 浅层定性嗅探三定律
1. **严格只读原则 (Read-Only Guarantee)**：
   * 探测器枚举文件系统时，只能使用只读句柄（`Path.iterdir()` / `os.scandir()`），**严禁以写模式或修改属性方式触碰任何用户文件**；
2. **浅层深度限制 ($\text{MaxDepth} \le 2$)**：
   * 仅扫描根目录与前 5 个一级子目录，识别特征工程文件（如 `.git`, `requirements.txt`, `package.json`）；
   * **严禁全盘深度递归遍历**，单驱动器采样文件总数上限为 50 个；
3. **毫秒级时间预算 ($\le 5\text{ms}$)**：
   * 单次探测耗时必须控制在 $5\text{ms}$ 以内（实测标准为 $2.1\text{ms}$），单次嗅探完毕立即释放文件系统迭代句柄。

---

## 4. 0% 能耗与系统资源红线 (Resource Redlines)

| 资源维度 | 物理上限红线 | 架构保障手段 |
| :--- | :--- | :--- |
| **空闲 CPU 占用** | $\le 0.05\%$ (趋近于 0%) | 纯事件驱动（WMI/Win32 中断 + 异步队列挂起），杜绝 `while True: pass` 忙轮询 |
| **常驻内存占用** | $\le 60\text{MB}$ (中枢核心) | 延迟加载大型模型依赖，媒体数据通过共享内存零拷贝传递 |
| **磁盘 I/O 写入** | 0 持续磁盘写入 | 禁用全天候录屏与海量原始物理帧落盘，仅在事件闭环后写入结构化 JSON 状态 |
| **句柄与线程泄漏** | 0 泄漏 | 所有系统句柄与子进程必须在 `try...finally` 中显式安全释放 |
