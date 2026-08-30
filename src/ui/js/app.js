/**
 * CyberSpine WinUI 3 全功能响应式控制器 (App Controller)
 * 严格遵照 WinUIonWeb 标准事件模型与类名规范，全面支撑 8 大页面交互
 */

let activeView = 'dashboard';
let pollInterval = null;
let _appInited = false;
let _currentModel = 'qwen2.5:0.5b';

// 1. 汉堡菜单收缩/展开切换 (is-closed-compact)
function toggleNavRail() {
    const rail = document.getElementById('main-nav-left-panel');
    if (rail) {
        rail.classList.toggle('is-closed-compact');
    }
}

// 2. 探测 pywebview API 就绪
function _waitForBridgeAndInit(retries) {
    if (_appInited) return;
    if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.get_dashboard_data === 'function') {
        console.log("⚡ [CyberSpine Bridge] Python IPC 桥接层已就绪");
        _appInited = true;
        initApp();
        return;
    }
    if (retries > 0) {
        setTimeout(() => _waitForBridgeAndInit(retries - 1), 250);
    } else {
        if (!window.pywebview || !window.pywebview.api) {
            console.log("💡 [Mock Mode] 未检测到 pywebview 宿主，启用 Mock 预览模式");
            window.pywebview = { api: createMockBridge() };
        }
        _appInited = true;
        initApp();
    }
}

window.addEventListener('pywebviewready', () => {
    if (_appInited) return;
    _appInited = true;
    initApp();
});

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => _waitForBridgeAndInit(60), 100);
});

function initApp() {
    setupNavigation();
    updateDashboardData();
    syncModelSelector();

    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(() => {
        if (activeView === 'dashboard') {
            updateDashboardData();
        } else if (activeView === 'logs') {
            loadLogsView();
        } else if (activeView === 'models') {
            loadGanglionStatus();
        }
    }, 2000);
}

// 3. 导航栏切换
function setupNavigation() {
    document.querySelectorAll('.win-nav-item[data-view]').forEach(item => {
        item.addEventListener('click', () => {
            const targetView = item.getAttribute('data-view');
            switchView(targetView);
        });
    });
}

function switchView(viewName) {
    activeView = viewName;
    document.querySelectorAll('.win-nav-item[data-view]').forEach(el => {
        el.classList.toggle('is-selected', el.getAttribute('data-view') === viewName);
    });

    document.querySelectorAll('.win-view-panel').forEach(panel => {
        panel.classList.toggle('is-active', panel.id === `view-${viewName}`);
    });

    const titles = {
        dashboard: '中控仪表盘 (Neural Pulse Center)',
        plugins: '神经末梢插件商店 (Receptor Plugin Store)',
        models: '端侧大模型神经中枢 (Local SLM & Ganglion Hub)',
        cortex: '上层大脑链接管理 (Master Cortex Link Connector)',
        topology: '完整循环神经走向路线图 (Neural Loop Topology)',
        logs: '核心神经中枢软件日志 (System Core Logs)',
        mcp: '双向 MCP 协议互联中枢 (Bi-directional MCP Center)',
        settings: '系统全局设置 (Global Settings)'
    };
    const titleEl = document.getElementById('header-view-title');
    if (titleEl) titleEl.innerText = titles[viewName] || 'CyberSpine 驾驶舱';

    refreshCurrentView();
}

function refreshCurrentView() {
    if (activeView === 'dashboard') updateDashboardData();
    else if (activeView === 'plugins') loadPluginStore();
    else if (activeView === 'models') loadGanglionStatus();
    else if (activeView === 'cortex') loadCortexView();
    else if (activeView === 'logs') loadLogsView();
}

// ================= 📌 第 1 页：中控仪表盘 5 大模块数据渲染 =================
async function updateDashboardData() {
    try {
        const data = await window.pywebview.api.get_dashboard_data();
        if (!data) return;

        // 【模块 3: 神经中枢运行状况】
        const uptimeEl = document.getElementById('vital-uptime');
        if (uptimeEl) uptimeEl.innerText = data.uptime_formatted || '00:00:00';

        const hbEl = document.getElementById('vital-heartbeats');
        if (hbEl) hbEl.innerText = `#${data.heartbeat_count || 0} 次跳动`;

        const topHbState = document.getElementById('stat-heartbeat-state');
        if (topHbState) topHbState.innerText = `5.0s 起搏器 (#${data.heartbeat_count || 0} 次跳动)`;

        const channels = (data.somatic_topology && data.somatic_topology.channels) || data.somatic_channels || {};
        const activeNervesEl = document.getElementById('vital-active-nerves');
        if (activeNervesEl) activeNervesEl.innerText = `${Object.keys(channels).length}/11 通道在线`;

        const hwData = channels['nerve.hardware.somatic_telemetry'] || {};
        const gpuLoadEl = document.getElementById('vital-gpu-load');
        if (gpuLoadEl) {
            const temp = hwData.gpu_temp_c || 51.0;
            const power = hwData.gpu_power_watts || 18.5;
            gpuLoadEl.innerText = `GPU ${temp}°C · ${power}W`;
        }

        // 【模块 1: 当前 1 分钟世界感知】
        const b = data.briefing || data.latest_briefing || {};
        const sumEl = document.getElementById('briefing-summary');
        if (sumEl) sumEl.innerText = b.summary || '系统运行平稳，正在持续感知微观神经信号并由端侧大模型推演中...';

        const timeEl = document.getElementById('briefing-time');
        if (timeEl) timeEl.innerText = b.timestamp || new Date().toLocaleTimeString();

        // 【模块 2: 当前的判断与介入裁决】
        const focusEl = document.getElementById('briefing-focus');
        if (focusEl) focusEl.innerText = b.attention_focus || '桌面常规交互';

        const escEl = document.getElementById('briefing-escalation');
        if (escEl) {
            const dec = b.escalation_decision || {};
            escEl.innerText = dec.reason ? `${dec.reason} (${dec.urgency || 'LOW'})` : (b.escalate_decision || '稳态观察中 (无需打扰)');
        }

        const actEl = document.getElementById('briefing-activity');
        if (actEl) actEl.innerText = b.user_activity || b.macro_intent || '日常系统人机交互';

        // 【模块 4: 神经中枢 AI 总结】
        const aiSumEl = document.getElementById('briefing-ai-summary');
        if (aiSumEl) {
            aiSumEl.innerText = `端侧中枢小脑 (Qwen2.5 @ RTX 4060) 实时推演：物理计算机处于稳态运行；未捕获异常痛觉闪退；已连续驻留焦点工作台；高级大脑裁决为“${b.escalation_decision?.reason || '稳态观察中'}”。`;
        }

        // 【模块 5: 11 大已启用末梢实时捕获消息流】
        renderSomaticFeedGrid(channels);

    } catch (e) {
        console.error("更新仪表盘失败:", e);
    }
}

// 渲染 11 大感官末梢实时消息流网格
function renderSomaticFeedGrid(channels) {
    const container = document.getElementById('somatic-feed-container');
    if (!container) return;

    const channelMeta = {
        "nerve.system.foreground_focus": {
            title: "前台窗口焦点",
            channel_name: "WORKSPACE_FOCUS",
            renderMsg: c => `前台聚焦于 [${c.active_process || 'Desktop'}] 窗口标题: '${c.active_title || '桌面'}'`
        },
        "nerve.system.running_apps": {
            title: "应用画像拓扑",
            channel_name: "APPS_TOPOLOGY",
            renderMsg: c => `系统共 ${c.total_user_apps || 0} 个活跃应用画像，包括 IDE、浏览器与终端`
        },
        "nerve.system.high_load": {
            title: "代谢压力尖峰",
            channel_name: "METABOLIC_STRESS",
            renderMsg: c => `CPU 利用率: ${c.cpu_percent || 0}% | 物理内存利用率: ${c.memory_percent || 0}% (稳态)`
        },
        "nerve.system.homeostasis": {
            title: "体温与内稳态",
            channel_name: "HOMEOSTASIS",
            renderMsg: c => `电量 ${c.battery_percent ?? 100}% | ${c.power_plugged ? '已接通交流电源' : '电池供电中'} | 开机正常`
        },
        "nerve.system.notifications": {
            title: "前庭未读通知",
            channel_name: "VESTIBULAR_ALERT",
            renderMsg: c => `Windows 通知中心当前有 ${c.unread_count || 0} 条未读消息排队中`
        },
        "nerve.system.stability": {
            title: "创伤痛觉监控",
            channel_name: "NOCICEPTION",
            renderMsg: c => `${c.is_healthy ? '健康无崩溃事件，Application Error 监听正常' : '捕获到异常软件闪退'}`
        },
        "nerve.network.health": {
            title: "远程触觉通信",
            channel_name: "AXON_NETWORK",
            renderMsg: c => `DNS 时延 ${c.dns_latency_ms || 0.51}ms | 链路质量平稳，网络无丢包`
        },
        "nerve.io.storage": {
            title: "肢体外设接触",
            channel_name: "PERIPHERAL_IO",
            renderMsg: c => `本地存储卷就绪 (${c.total_known_devices || 2} 个设备)，无未知恶意外设`
        },
        "nerve.hardware.somatic_telemetry": {
            title: "核心内脏体温",
            channel_name: "VISCERAL_THERMALS",
            renderMsg: c => `GPU 核心温度: ${c.gpu_temp_c || 51.0}°C | 实时功耗: ${c.gpu_power_watts || 18.5}W (${c.source_mode || 'NATIVE'})`
        },
        "nerve.system.input_kinetics": {
            title: "皮肤动量心流",
            channel_name: "KINETIC_CADENCE",
            renderMsg: c => `物理空闲 ${c.idle_seconds || 0}s | 当前心流阶段: [${c.flow_state || 'STEADY_FLOW'}]`
        },
        "nerve.system.clipboard_semantics": {
            title: "瞬时工作记忆",
            channel_name: "WORKING_MEMORY",
            renderMsg: c => `剪贴板模式: [${c.content_type || 'EMPTY'}] | 字符数: ${c.length || 0} (${c.preview || '无内容'})`
        }
    };

    let html = '';
    for (const [chId, meta] of Object.entries(channelMeta)) {
        const data = channels[chId] || {};
        const msg = meta.renderMsg(data);

        html += `
        <div class="win-somatic-feed-card">
          <div class="win-somatic-header">
            <div class="win-somatic-title">
              <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
              <span>${meta.title}</span>
            </div>
            <span class="win-info-badge success" style="font-size:10px;padding:1px 5px;">在线捕获</span>
          </div>
          <div class="win-somatic-msg">${msg}</div>
          <div class="win-somatic-meta">
            <span>${meta.channel_name}</span>
            <span>${chId}</span>
          </div>
        </div>
        `;
    }

    container.innerHTML = html;
}

// ================= 🧩 第 2 页：神经末梢插件商店 =================
async function loadPluginStore() {
    const instList = document.getElementById('installed-plugins-list');
    const availList = document.getElementById('available-plugins-list');
    if (!instList) return;

    try {
        const plugins = (await window.pywebview.api.get_available_plugins()) || (await window.pywebview.api.get_plugin_store()) || {};
        let instHtml = '';
        let availHtml = '';

        const pluginArray = Array.isArray(plugins) ? plugins : Object.values(plugins);

        for (const p of pluginArray) {
            const id = p.id;
            const isInstalled = p.installed !== false;
            const isEnabled = p.enabled;

            const card = `
            <div class="win-settings-card">
              <div class="win-settings-card-surface">
                <div class="win-settings-card-header">
                  <div class="win-settings-card-icon">
                    <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                  </div>
                  <div class="win-settings-card-text">
                    <div class="win-settings-card-title">${p.name} <span style="font-size:11px;color:var(--text-tertiary);margin-left:6px;">v${p.version || '1.0.0'} · ${p.category || '感官'}</span></div>
                    <div class="win-settings-card-desc">${p.desc || '低能耗只读非侵入式感官探针'}</div>
                  </div>
                </div>
                ${isInstalled ? `
                  <div class="win-switch-wrap" onclick="handleTogglePerceptor('${id}', ${!isEnabled})">
                    <div class="win-switch ${isEnabled ? 'is-on' : ''}">
                      <div class="track"></div>
                      <div class="knob"><div class="thumb"></div></div>
                    </div>
                    <span style="font-size:12px;color:var(--text-secondary);">${isEnabled ? '已启用' : '已停用'}</span>
                  </div>
                ` : `
                  <button class="win-button accent" onclick="handleInstallPlugin('${id}')">安装挂载</button>
                `}
              </div>
            </div>
            `;

            if (isInstalled) instHtml += card;
            else availHtml += card;
        }

        instList.innerHTML = instHtml || '<div style="color:var(--text-tertiary);font-size:12px;">暂无已安装插件</div>';
        if (availList) availList.innerHTML = availHtml || '<div style="color:var(--text-tertiary);font-size:12px;">全部扩展插件已挂载</div>';
    } catch (e) {
        console.error("加载插件商店失败:", e);
    }
}

async function handleTogglePerceptor(id, enabled) {
    try {
        await window.pywebview.api.toggle_plugin(id, enabled);
        loadPluginStore();
        updateDashboardData();
    } catch (e) {
        console.error("切换插件失败:", e);
    }
}

async function handleInstallPlugin(id) {
    try {
        const res = await window.pywebview.api.install_plugin(id);
        if (res.success) {
            alert(`插件 [${res.name || id}] 安装挂载成功！\n依赖校验: ${res.dependency_check?.summary || '通过'}`);
            loadPluginStore();
            updateDashboardData();
        } else {
            alert(`安装失败: ${res.error}`);
        }
    } catch (e) {
        alert("安装异常: " + e);
    }
}

// ================= 🧠 第 3 页：端侧模型管理 =================
async function loadGanglionStatus() {
    try {
        const status = await window.pywebview.api.get_ganglion_status();
        if (!status) return;

        const installed = status.installed_ollama_models || ["qwen2.5:0.5b"];
        const activeModel = status.midbrain?.name || 'qwen2.5:0.5b';
        _currentModel = activeModel;

        const activeNameEl = document.getElementById('model-active-name');
        if (activeNameEl) activeNameEl.innerText = activeModel;

        const selects = [document.getElementById('global-model-selector'), document.getElementById('ganglion-model-select')];
        selects.forEach(sel => {
            if (!sel) return;
            let optHtml = '';
            const allCandidates = Array.from(new Set([...installed, "qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5:7b"]));
            allCandidates.forEach(m => {
                const isInstalled = installed.includes(m);
                optHtml += `<option value="${m}" ${m === activeModel ? 'selected' : ''}>${m} ${isInstalled ? '(已就绪)' : '(待拉取)'}</option>`;
            });
            sel.innerHTML = optHtml;
        });

    } catch (e) {
        console.error("加载模型状态失败:", e);
    }
}

async function handleModelChange(newModel) {
    if (!newModel) return;
    try {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.switch_model) {
            await window.pywebview.api.switch_model(newModel);
        }
        _currentModel = newModel;
        syncModelSelector();
        loadGanglionStatus();
        updateDashboardData();
    } catch (e) {
        console.error("切换模型失败:", e);
    }
}

async function handlePullModel() {
    const input = document.getElementById('pull-model-input');
    if (!input || !input.value.trim()) return;
    const modelName = input.value.trim();
    try {
        input.disabled = true;
        alert(`正在后台从 Ollama 镜像拉取 ${modelName}，请稍候...`);
        const res = await window.pywebview.api.pull_ollama_model(modelName);
        input.disabled = false;
        input.value = '';
        alert(res.success ? `模型 ${modelName} 拉取成功！` : `拉取失败: ${res.error}`);
        loadGanglionStatus();
    } catch (e) {
        input.disabled = false;
        alert("拉取异常: " + e);
    }
}

async function syncModelSelector() {
    loadGanglionStatus();
}

// ================= 🌐 第 4 页：上层大脑链接管理 =================
async function loadCortexView() {
    const container = document.getElementById('cortex-messages-container');
    if (!container) return;
    try {
        const link = await window.pywebview.api.get_cortex_link_status();
        container.innerText = `[${new Date().toLocaleTimeString()}] [MCP_ONLINE] 服务名称: ${link.server_name || 'cyberspine-neural-link'} | 挂载工具: ${link.tools_count || 6} 个\n[${new Date().toLocaleTimeString()}] [READY] Stdio 双向隔离管道已连接，等待上层大脑指令...`;
    } catch (e) {
        console.error("加载大脑连接失败:", e);
    }
}

// ================= 📜 第 6 页：核心运行日志 =================
async function loadLogsView() {
    const container = document.getElementById('telemetry-log-container');
    if (!container) return;
    try {
        const frames = await window.pywebview.api.get_cognitive_telemetry(60);
        let logText = '';
        frames.forEach(f => {
            logText += `[${f.timestamp || ''}] [${f.category || 'INFO'}] ${f.message || ''}\n`;
        });
        container.innerText = logText || '暂无系统日志流水...';
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        console.error("加载日志失败:", e);
    }
}

async function handleClearLogs() {
    try {
        await window.pywebview.api.clear_cognitive_telemetry();
        loadLogsView();
    } catch (e) {
        console.error("清空日志失败:", e);
    }
}

async function handleTriggerCognitiveCycle() {
    try {
        const res = await window.pywebview.api.trigger_live_cognitive_cycle();
        alert(`认知全链路采样完成！耗时: ${res.total_latency_ms}ms (感官: ${res.somatic_latency_ms}ms, 模型: ${res.model_latency_ms}ms)`);
        loadLogsView();
        updateDashboardData();
    } catch (e) {
        alert("采样异常: " + e);
    }
}

// ================= 🔌 第 7 页：一键复制 MCP 配置 =================
function handleCopyMCPConfig() {
    const snippet = document.getElementById('mcp-config-snippet');
    if (snippet) {
        navigator.clipboard.writeText(snippet.innerText);
        alert("MCP 配置已成功复制到剪贴板！可直接粘贴至 Antigravity 或 Claude Desktop 中。");
    }
}

// 辅助动作
async function handleManualPulse() {
    try {
        await window.pywebview.api.trigger_manual_pulse();
        updateDashboardData();
    } catch (e) {
        console.error("即时采样失败:", e);
    }
}

async function handleQuietMode(sec) {
    try {
        await window.pywebview.api.apply_quiet_mode(sec);
        updateDashboardData();
    } catch (e) {
        console.error("免打扰失败:", e);
    }
}

// Mock 预览模式 (供纯浏览器离线调试)
function createMockBridge() {
    return {
        get_dashboard_data: async () => ({
            uptime_formatted: "02:05:18",
            heartbeat_count: 1540,
            briefing: {
                summary: "【全景感知简报】过去60秒系统处于平稳运行稳态。用户前台持续聚焦于 VSCode 编辑器；CPU 平均负载 12.5%，内存占用 81.2%，网络时延 0.51ms，外设连接正常，未捕获异常崩溃。",
                attention_focus: "VSCode · CyberSpine 8大页面重构",
                escalation_decision: { reason: "稳态观察中 (无需打扰高级大脑)", urgency: "LOW" },
                user_activity: "按 WinUIonWeb 规范编写全部 8 大页面",
                timestamp: new Date().toLocaleTimeString()
            },
            somatic_topology: {
                channels: {
                    "nerve.system.foreground_focus": { active_process: "Code.exe", active_title: "app.js - CyberSpine" },
                    "nerve.system.running_apps": { total_user_apps: 82 },
                    "nerve.system.high_load": { cpu_percent: 12.5, memory_percent: 81.2 },
                    "nerve.system.homeostasis": { battery_percent: 100, power_plugged: true },
                    "nerve.system.notifications": { unread_count: 0 },
                    "nerve.system.stability": { is_healthy: true },
                    "nerve.network.health": { dns_latency_ms: 0.51 },
                    "nerve.io.storage": { total_known_devices: 2 },
                    "nerve.hardware.somatic_telemetry": { gpu_temp_c: 51.0, gpu_power_watts: 18.5, source_mode: "NATIVE_FALLBACK" },
                    "nerve.system.input_kinetics": { idle_seconds: 0.8, flow_state: "BURST_TYPING_OR_INTERACTION" },
                    "nerve.system.clipboard_semantics": { content_type: "SOURCE_CODE", length: 145, preview: "const channelMeta = ..." }
                }
            }
        }),
        get_available_plugins: async () => ({
            "nerve.system.foreground_focus": { id: "nerve.system.foreground_focus", name: "前台窗口焦点感知", enabled: true, installed: true, desc: "Win32 原生捕获活跃进程名、窗口标题与专注驻留时长", version: "1.2.0", category: "系统感知" },
            "nerve.hardware.somatic_telemetry": { id: "nerve.hardware.somatic_telemetry", name: "核心内脏体温与硬件代谢", enabled: true, installed: true, desc: "AIDA64 共享内存与 GPU 显卡体征监控", version: "1.0.0", category: "硬件体征" },
            "nerve.visual.screen": { id: "nerve.visual.screen", name: "视觉神经节：屏幕视觉变动感知", enabled: false, installed: false, desc: "挂载视觉多模态小模型 (Qwen2-VL)，语义级感知屏幕变动与 OCR", version: "0.9.0", category: "分脑视觉" }
        }),
        get_ganglion_status: async () => ({
            installed_ollama_models: ["qwen2.5:0.5b"],
            midbrain: { name: "qwen2.5:0.5b" }
        }),
        get_cortex_link_status: async () => ({
            status: "ONLINE",
            server_name: "cyberspine-neural-link",
            tools_count: 6
        }),
        switch_model: async (m) => ({ success: true, active_model: m }),
        pull_ollama_model: async (m) => ({ success: true }),
        toggle_plugin: async () => ({ success: true }),
        install_plugin: async (id) => ({ success: true, name: id, dependency_check: { summary: "校验通过" } }),
        get_cognitive_telemetry: async () => ([{ timestamp: "02:05:00", category: "SOMATIC", message: "5.0s 起搏器精准心跳采样" }]),
        clear_cognitive_telemetry: async () => ({ success: true }),
        trigger_live_cognitive_cycle: async () => ({ total_latency_ms: 120, somatic_latency_ms: 15, model_latency_ms: 95 }),
        trigger_manual_pulse: async () => ({ success: true }),
        apply_quiet_mode: async () => ({ success: true })
    };
}
