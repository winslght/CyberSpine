# 缺陷跟踪、踩坑实战与解决进度看板 (Issue & Bug Tracker)

**文档编号**：DOC-TRK-001  
**状态**：持续维护看板 (Live Tracking)  
**维护者**：CyberSpine 工程研发组  

---

## 1. 缺陷跟踪看板概述

本文档用于**真实、透明、全量记录 CyberSpine 在研发和测试过程中遇到的所有物理踩坑、环境异构 Bug、根因剖析与解决状态**，作为团队防返工与跨平台排错的活知识库。

---

* **根因剖析**：Windows 中文系统的默认控制台代码页为 `GBK (CP936)`，在终端使用 `print(f"✅ ...")` 输出特殊 Unicode 符号时，由于 GBK 字符集未包含该字符，直接导致测试抛出致命异常中断。
* **解决对策**：
  1. 在测试入口添加 `sys.stdout.reconfigure(encoding='utf-8')` 尝试自动升频；
  2. 控制台输出统一采用跨平台强健的 ASCII 标准标签（如 `[PASS]`, `[FAIL]`, `[INFO]`）。
* **状态**：**已彻底修复并合入基线 ✅**

---

### ✅ BUG-002: Python 3.12+ `datetime.utcnow()` 弃用告警与无时区盲时间戳
* **发现日期**：2026-08-28 (组件 1 测试阶段)
* **影响模块**：`src/models/somatic_signals.py`, `src/perceptors/io/device_db.py`
* **异常现象**：
  ```text
  DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version.
  ```
* **根因剖析**：Python 3.12+ 官方将 `datetime.utcnow()` 列为废弃方法，生成的 `datetime` 对象缺乏 `tzinfo`，跨系统传输时极易产生时区解析偏差。
* **解决对策**：封装统一的 `utc_now()` 辅助方法，统一使用 `datetime.now(timezone.utc)` 生成时区感知的标准时间戳。
* **状态**：**已彻底修复并合入基线 ✅**

---

### ✅ BUG-003: Pydantic V2 `dict()` 方法过时提示
* **发现日期**：2026-08-28 (组件 1 测试阶段)
* **影响模块**：`src/perceptors/io/io_manager.py`
* **异常现象**：`PydanticDeprecatedSince20: The dict method is deprecated; use model_dump instead.`
* **解决对策**：将所有模型实例的序列化方法全面更新为 Pydantic V2 官方标准的 `model_dump()`。
* **状态**：**已彻底修复并合入基线 ✅**

---

### ✅ BUG-004: Windows 微软商店 Python 占位快捷方式拦截
* **发现日期**：2026-08-28 (环境初始化阶段)
* **异常现象**：执行 `python` 命令时提示 `Python was not found; run without arguments to install from the Microsoft Store...`
* **根因剖析**：WindowsApps 下的别名占位符覆盖了真实二进制路径。
* **解决对策**：在守护进程启动脚本中自动探测真实物理 Python 路径，并成功为运行环境安装 `psutil` 与 `pydantic` 依赖。
### ✅ BUG-005: Windows 批处理启动脚本 UTF-8/Emoji 代码页解析乱码
* **发现日期**：2026-08-28 (实机演练阶段)
* **影响模块**：`run_demo.bat`
* **异常现象**：Windows CMD 报 `'炴満婕旂粌缁堢'` 与 `'冧粨搴揰CyberSpine_Core"'` 无法识别，导致路径切换失败。
* **解决对策**：采用纯 ASCII 命名 `run_demo.bat`，并于工作区根目录提供自动寻址的 `demo_minimal_loop.py` 转发器。
* **状态**：**已彻底修复并合入基线 ✅**

---

### ✅ BUG-006: 实机硬件监听模式调用旧接口抛出 AttributeError
* **发现日期**：2026-08-28 (模式 2 实测)
* **异常现象**：`AttributeError: 'IOPerceptorManager' object has no attribute 'take_somatic_snapshot'`
* **解决对策**：统一使用规范的 `get_full_io_snapshot()` 提取全局物理磁盘拓扑。
* **状态**：**已彻底修复并合入基线 ✅**

---

### ✅ BUG-007: 下行抑制导致连续插入新设备时信号包为 None
* **发现日期**：2026-08-28 (真实 U 盘连插实测)
* **异常现象**：首个 U 盘处理完毕后进入 300s 抑制期，紧接着插入全新 U 盘被误拦截，导致 `packet=None` 抛出异常。
* **解决对策**：
  1. 架构升级为 **设备定向抑制机制 (Device-Scoped Inhibition)**，仅抑制已处理设备指纹，放行全新外设；
  2. 脊髓意图门控全面增加防 `None` 安全防御。
* **状态**：**已彻底修复并通过 38 组全量回归测试 ✅**

---

## 3. 里程碑完成看板 (Milestones)

| 里程碑编号 | 版本 | 核心交付物 | 实机测试指标 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| **MILESTONE-001** | v3.2.0 | 仿生 4 大核心脑区最小闭环 MVP (IO+时钟+脊髓+大脑+双手+下行抑制) | 14/14 测试通过 (0.414s) | ✅ 已交付 |
| **MILESTONE-002** | v3.3.0 | 7 大宏观神经末梢 + SomaticPerceptorHub 全身调度与自动化留痕 | 38/38 测试通过 (1.332s) | ✅ 已交付 |

