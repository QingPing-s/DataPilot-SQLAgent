import {
  AlertCircle,
  BarChart3,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Circle,
  Clipboard,
  Database,
  Download,
  FileText,
  Gauge,
  Home,
  Maximize2,
  Play,
  Server,
  Settings,
  TableProperties,
  TerminalSquare,
  Workflow,
  X,
} from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

const navItems = [
  { id: "home", label: "首页", icon: Home },
  { id: "database", label: "数据库", icon: Database },
  { id: "analysis", label: "SQL 分析", icon: TerminalSquare },
  { id: "trace", label: "执行轨迹", icon: Workflow },
  { id: "evaluation", label: "评测报告", icon: FileText },
  { id: "settings", label: "设置", icon: Settings },
];

const viewMeta = {
  home: ["DataPilot SQL Agent", "多智能体 SQL 数据分析工作台"],
  database: ["数据库", "查看 Northwind 的真实表结构、关联和数据规模"],
  analysis: ["SQL 分析", "检查当前查询的计划、SQL、执行结果和最终回答"],
  trace: ["执行轨迹", "查看本次 Agent 工作流的真实节点事件"],
  evaluation: ["评测报告", "查看 Spider-style 离线评测状态与客观指标"],
  settings: ["设置", "查看本地 Agent API、模型与数据库连接配置"],
};

const workflowNodes = [
  ["schema", "Schema Agent"],
  ["sql_plan", "SQL Planner"],
  ["sql_generate", "SQL Generator"],
  ["sql_execute", "SQL Executor"],
  ["sql_repair", "SQL Debugger"],
  ["judge", "Judge"],
];

const nodeLabels = {
  schema: "Schema Agent",
  sql_plan: "SQL Planner",
  sql_generate: "SQL Generator",
  sql_execute: "SQL Executor",
  sql_repair: "SQL Debugger",
  answer: "Answer Analyst",
  judge: "Judge",
  report: "Report Generator",
};

const columnLabels = {
  product_category: "产品类别",
  category_name: "产品类别",
  product: "产品",
  product_name: "产品",
  company_name: "公司名称",
  first_name: "名",
  last_name: "姓",
  order_count: "订单数",
  sales_amount: "销售额",
  revenue: "销售额",
  total_sales: "销售额",
  average_order_value: "平均订单金额",
  unit_cost: "单位成本",
  cost_price: "历史成本",
  cost: "成本",
  gross_profit: "毛利",
  gross_margin_percent: "毛利率（%）",
  target_completion_percent: "目标完成率（%）",
  sales_target: "销售目标",
  on_time_rate: "准时率（%）",
  average_shipping_days: "平均配送天数",
  returned_quantity: "退货数量",
  return_count: "退货次数",
  reorder_level: "补货点",
  units_on_order: "在途库存",
  units_in_stock: "库存",
  units_sold: "销量",
  sales_month: "月份",
  limitation: "数据限制",
};

function Sidebar({ activeView, collapsed, onNavigate, onToggle }) {
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="brand">
        <div className="brandMark">D</div>
        {!collapsed && <div className="brandText">DataPilot SQL Agent</div>}
      </div>
      <nav className="navList">
        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            className={`navItem ${activeView === id ? "active" : ""}`}
            key={id}
            onClick={() => onNavigate(id)}
            aria-label={label}
            title={collapsed ? label : undefined}
          >
            <Icon size={18} />
            {!collapsed && <span>{label}</span>}
          </button>
        ))}
      </nav>
      <button className="collapseButton" onClick={onToggle} aria-label={collapsed ? "展开侧栏" : "收起侧栏"}>
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        {!collapsed && <span>收起</span>}
      </button>
    </aside>
  );
}

function Header({ activeView, apiStatus }) {
  const statusText = {
    checking: "检查连接中",
    online: "Agent 已连接",
    offline: "Agent 未连接",
  }[apiStatus];
  const [title, subtitle] = viewMeta[activeView];

  return (
    <header className="header">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="headerActions">
        <div className={`statusBadge ${apiStatus}`}>
          <span className="statusDot" />
          {statusText}
        </div>
        <button className="avatarButton" aria-label="用户头像">DP</button>
      </div>
    </header>
  );
}

function QuestionCard({ question, onQuestionChange, onGenerate, isGenerating, notice }) {
  return (
    <section className="card questionCard">
      <div className="cardTitleRow">
        <div>
          <h2>自然语言提问</h2>
          <p>问题将发送到本地 Python Agent，生成并执行 SQLite 查询。</p>
        </div>
      </div>
      <textarea value={question} onChange={(event) => onQuestionChange(event.target.value)} />
      {notice && <div className={`queryNotice ${notice.type}`}>{notice.text}</div>}
      <div className="questionActions">
        <label>
          数据库
          <select value="Northwind" disabled aria-label="数据库">
            <option>Northwind</option>
          </select>
        </label>
        <button className="primaryButton" onClick={onGenerate} disabled={isGenerating}>
          <Play size={18} />
          {isGenerating ? "生成中..." : "生成 SQL"}
        </button>
      </div>
    </section>
  );
}

function SqlCard({ generatedSql, explanation, onCopy, onFullscreen, copyStatus }) {
  return (
    <section className="card">
      <div className="cardTitleRow">
        <div>
          <h2>生成的 SQL</h2>
          <p>{explanation || "SQLite dialect"}</p>
        </div>
        <div className="iconActions">
          {copyStatus && <span className="toolStatus">{copyStatus}</span>}
          <button aria-label="复制 SQL" title="复制 SQL" onClick={onCopy}>
            <Clipboard size={17} />
          </button>
          <button aria-label="全屏查看 SQL" title="全屏查看 SQL" onClick={onFullscreen}>
            <Maximize2 size={17} />
          </button>
        </div>
      </div>
      <pre className="codeBlock"><code>{generatedSql}</code></pre>
    </section>
  );
}

function ResultCard({ columns, rows, rowCount, onExport }) {
  return (
    <section className="card">
      <div className="cardTitleRow">
        <div>
          <h2>查询结果预览</h2>
          <p>返回 {rowCount} 行</p>
        </div>
      </div>
      <div className="tableWrap">
        <table>
          <thead>
            <tr>{columns.map((column) => <th key={column}>{columnLabels[column] || column}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((column) => <td key={column}>{formatCell(row[column])}</td>)}
              </tr>
            ))}
            {!rows.length && (
              <tr><td className="emptyResult" colSpan={Math.max(columns.length, 1)}>提交问题后将在这里显示真实查询结果</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="tableFooter">
        <span>第 1 页 / 共 1 页</span>
        <button className="secondaryButton" onClick={onExport} disabled={!rows.length}>
          <Download size={16} />导出 CSV
        </button>
      </div>
    </section>
  );
}

function FinalAnswerCard({ finalAnswer, fallbackUsed }) {
  if (!finalAnswer?.answer) return null;
  return (
    <section className="card answerCard">
      <div className="cardTitleRow">
        <div>
          <h2>分析结论</h2>
          <p>{fallbackUsed ? "部分步骤使用本地 fallback" : "由 Answer Analyst 生成"}</p>
        </div>
      </div>
      <p className="answerText">{finalAnswer.answer}</p>
      {!!finalAnswer.key_insights?.length && (
        <ul className="insightList">
          {finalAnswer.key_insights.map((insight, index) => <li key={index}>{insight}</li>)}
        </ul>
      )}
    </section>
  );
}

function DatabaseCard({ databaseInfo, apiStatus }) {
  const counts = databaseInfo?.row_counts || {};
  const coreTables = ["orders", "order_details", "products", "returns", "employee_targets", "inventory_transactions"];
  const topics = ["销售与毛利", "员工目标", "配送准时率", "库存补货", "退货分析", "客户价值", "月度趋势"];
  return (
    <section className="card">
      <div className="dbHeader">
        <div className="dbIcon"><Database size={22} /></div>
        <div>
          <h2>Northwind V2</h2>
          <p>SQLite · {apiStatus === "online" ? "已连接" : "未连接"} · 2023–2025 企业经营示例库</p>
        </div>
      </div>
      <p className="dbDescription">包含销售、历史成本、退货、配送、库存流水和员工月度目标，可用于更完整的 Text-to-SQL 企业分析。</p>
      <div className="dbStats">
        <span><strong>{databaseInfo?.table_count ?? "-"}</strong> 张表</span>
        <span><strong>{counts.orders ?? "-"}</strong> 个订单</span>
        <span><strong>{counts.products ?? "-"}</strong> 个产品</span>
        <span><strong>{counts.customers ?? "-"}</strong> 个客户</span>
      </div>
      <div className="databaseSection">
        <h3>核心表</h3>
        <div className="tagWrap">{coreTables.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div>
      </div>
      <div className="databaseSection">
        <h3>可分析主题</h3>
        <div className="topicList">{topics.map((topic) => <span key={topic}>{topic}</span>)}</div>
      </div>
      <div className="schemaNote">
        <strong>数据限制</strong>
        <span>当前可以计算毛利，但不包含工资、税务和管理费用，因此不能代表完整财务净利润。</span>
      </div>
    </section>
  );
}

function WorkflowCard({ trace, fallbackUsed }) {
  return (
    <section className="card">
      <div className="cardTitleRow">
        <div><h2>Agent 工作流</h2><p>StateGraph execution path</p></div>
      </div>
      <div className="workflowList">
        {workflowNodes.map(([nodeId, label], index) => {
          const status = getNodeStatus(trace, nodeId);
          const Icon = status === "error" ? AlertCircle : status === "success" ? CheckCircle2 : Circle;
          return (
            <div className={`workflowItem ${status}`} key={nodeId}>
              <Icon size={18} />
              <span>{label}</span>
              {nodeId === "sql_generate" && fallbackUsed && <em>fallback</em>}
              {index < workflowNodes.length - 1 && <span className="arrow">→</span>}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function MetricsCard({ evaluationInfo }) {
  const items = buildMetricItems(evaluationInfo);
  return (
    <section className="card">
      <div className="cardTitleRow">
        <div><h2>评估指标</h2><p>Spider-style evaluation</p></div>
        <Gauge size={20} className="mutedIcon" />
      </div>
      {!evaluationInfo?.available ? (
        <EmptyState compact title="尚无有效评测" text="请准备 Spider 数据库后重新运行评测。" />
      ) : (
        <div className="metricsList">
          {items.map((metric) => (
            <div className="metricItem" key={metric.label}>
              <div className="metricTop"><span>{metric.label}</span><strong>{metric.value}</strong></div>
              <div className="progressTrack"><div className="progressFill" style={{ width: `${metric.percent}%` }} /></div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function TraceCard({ trace, full = false }) {
  const events = full ? trace : trace.slice(-6);
  return (
    <section className="card">
      <div className="cardTitleRow">
        <div><h2>执行轨迹</h2><p>{trace.length ? `${trace.length} 个真实事件` : "latest trace"}</p></div>
        <BarChart3 size={20} className="mutedIcon" />
      </div>
      {!events.length ? (
        <EmptyState compact title="暂无执行轨迹" text="生成一次 SQL 后，这里将显示真实节点状态。" />
      ) : (
        <div className="timeline">
          {events.map((event, index) => (
            <div className={`timelineItem ${event.status}`} key={`${event.timestamp}-${event.node}-${index}`}>
              <span className="timelineDot" />
              <div>
                <div className="timelineMeta">
                  <span>{formatTime(event.timestamp)}</span>
                  <strong>{formatNodeName(event.node)}</strong>
                  <em>{formatStatus(event.status)}</em>
                </div>
                <p>{event.message}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function HomeView(props) {
  return (
    <div className="contentGrid">
      <div className="leftColumn">
        <QuestionCard {...props.questionProps} />
        <SqlCard {...props.sqlProps} />
        <ResultCard {...props.resultProps} />
        <FinalAnswerCard finalAnswer={props.finalAnswer} fallbackUsed={props.fallbackUsed} />
      </div>
      <div className="rightColumn">
        <DatabaseCard databaseInfo={props.databaseInfo} apiStatus={props.apiStatus} />
        <WorkflowCard trace={props.trace} fallbackUsed={props.fallbackUsed} />
        <MetricsCard evaluationInfo={props.evaluationInfo} />
        <TraceCard trace={props.trace} />
      </div>
    </div>
  );
}

function DatabaseView({ databaseInfo }) {
  const tables = databaseInfo?.tables || [];
  return (
    <div className="viewStack">
      <section className="summaryBand">
        <div><strong>{databaseInfo?.table_count ?? 0}</strong><span>用户表</span></div>
        <div><strong>{databaseInfo?.row_counts?.orders ?? 0}</strong><span>订单</span></div>
        <div><strong>{databaseInfo?.row_counts?.order_details ?? 0}</strong><span>订单明细</span></div>
        <div><strong>{databaseInfo?.database_type || "SQLite"}</strong><span>数据库类型</span></div>
      </section>
      {!tables.length ? <EmptyState title="数据库信息不可用" text="请确认 FastAPI 和 Northwind 数据库已启动。" /> : (
        <div className="schemaGrid">
          {tables.map((table) => (
            <section className="card schemaCard" key={table.table_name}>
              <div className="schemaCardHeader">
                <div><TableProperties size={18} /><h2>{table.table_name}</h2></div>
                <span>{table.row_count} 行</span>
              </div>
              <div className="columnList">
                {table.columns.map((column) => (
                  <div key={column.name}>
                    <code>{column.name}</code>
                    <span>{column.type || "TEXT"}</span>
                    {column.primary_key && <em>PK</em>}
                  </div>
                ))}
              </div>
              <div className="relationNote">
                {table.foreign_keys.length
                  ? table.foreign_keys.map((key) => `${key.from} → ${key.to_table}.${key.to}`).join(" · ")
                  : "无外键"}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function AnalysisView({ sqlPlan, sqlProps, resultProps, finalAnswer, fallbackUsed, onBack }) {
  return (
    <div className="viewStack narrowView">
      <div className="viewToolbar">
        <div><strong>当前分析结果</strong><span>{fallbackUsed ? "包含 fallback 步骤" : "完整 Agent 流程"}</span></div>
        <button className="secondaryButton" onClick={onBack}>返回首页提问</button>
      </div>
      <section className="card planCard">
        <div className="cardTitleRow"><div><h2>SQL Plan</h2><p>Planner 输出</p></div></div>
        {!Object.keys(sqlPlan || {}).length ? <EmptyState compact title="暂无查询计划" text="请先在首页生成 SQL。" /> : (
          <dl className="planGrid">
            <div><dt>相关表</dt><dd>{(sqlPlan.relevant_tables || []).join(", ") || "-"}</dd></div>
            <div><dt>聚合</dt><dd>{(sqlPlan.aggregations || []).join(", ") || "-"}</dd></div>
            <div><dt>连接键</dt><dd>{(sqlPlan.join_keys || []).join(", ") || "-"}</dd></div>
            <div><dt>排序</dt><dd>{(sqlPlan.order_by || []).join(", ") || "-"}</dd></div>
          </dl>
        )}
      </section>
      <SqlCard {...sqlProps} />
      <ResultCard {...resultProps} />
      <FinalAnswerCard finalAnswer={finalAnswer} fallbackUsed={fallbackUsed} />
    </div>
  );
}

function EvaluationView({ evaluationInfo }) {
  const items = buildMetricItems(evaluationInfo);
  return (
    <div className="viewStack narrowView">
      {!evaluationInfo?.available ? (
        <section className="card evaluationEmpty">
          <AlertCircle size={24} />
          <div>
            <h2>尚无有效评测结果</h2>
            <p>{evaluationInfo?.message || "未找到评测输出。"}</p>
            <code>python eval/run_eval.py --cases data/spider_subset/eval_cases.json --limit 50</code>
          </div>
        </section>
      ) : (
        <section className="metricGrid">
          {items.map((metric) => <div className="metricTile" key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong></div>)}
        </section>
      )}
      {!!evaluationInfo?.failed_cases?.length && (
        <section className="card">
          <div className="cardTitleRow"><div><h2>未完成 Case</h2><p>数据库缺失或执行失败</p></div></div>
          <div className="failureList">
            {evaluationInfo.failed_cases.map((item) => (
              <div key={item.case_id}><strong>{item.case_id}</strong><span>{item.question}</span><em>{item.error}</em></div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function SettingsView({ health, apiStatus }) {
  return (
    <div className="settingsGrid">
      <section className="card settingCard">
        <Server size={22} />
        <div><span>Agent API</span><strong>{API_BASE_URL}</strong><small>{apiStatus === "online" ? "连接正常" : "当前不可用"}</small></div>
      </section>
      <section className="card settingCard">
        <TerminalSquare size={22} />
        <div><span>模型</span><strong>{health?.model_name || "-"}</strong><small>{health?.api_key_configured ? "API Key 已在后端配置" : "未配置 API Key"}</small></div>
      </section>
      <section className="card settingCard">
        <Database size={22} />
        <div><span>数据库</span><strong>data/northwind/northwind.db</strong><small>{health?.database_exists ? "文件存在" : "文件不存在"}</small></div>
      </section>
      <section className="card securityNote">
        <h2>安全说明</h2>
        <p>DeepSeek API Key 只从 Python 后端的环境变量读取，不会发送到浏览器或写入前端构建产物。</p>
      </section>
    </div>
  );
}

function EmptyState({ title, text, compact = false }) {
  return <div className={`emptyState ${compact ? "compact" : ""}`}><Circle size={18} /><div><strong>{title}</strong><span>{text}</span></div></div>;
}

function SqlModal({ sql, onClose }) {
  return (
    <div className="modalOverlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="modalPanel" role="dialog" aria-modal="true" aria-label="SQL 全屏查看">
        <div className="modalHeader"><div><h2>生成的 SQL</h2><p>SQLite dialect</p></div><button onClick={onClose} aria-label="关闭全屏 SQL"><X size={20} /></button></div>
        <pre className="codeBlock modalCode"><code>{sql}</code></pre>
      </section>
    </div>
  );
}

function App() {
  const [activeView, setActiveView] = useState("home");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [question, setQuestion] = useState("统计每个产品类别的销售额，并按销售额降序展示");
  const [generatedSql, setGeneratedSql] = useState("-- 点击“生成 SQL”调用本地 DataPilot Agent");
  const [sqlExplanation, setSqlExplanation] = useState("");
  const [sqlPlan, setSqlPlan] = useState({});
  const [columns, setColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [rowCount, setRowCount] = useState(0);
  const [finalAnswer, setFinalAnswer] = useState({});
  const [trace, setTrace] = useState([]);
  const [fallbackUsed, setFallbackUsed] = useState(false);
  const [notice, setNotice] = useState(null);
  const [copyStatus, setCopyStatus] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSqlModalOpen, setIsSqlModalOpen] = useState(false);
  const [apiStatus, setApiStatus] = useState("checking");
  const [health, setHealth] = useState(null);
  const [databaseInfo, setDatabaseInfo] = useState(null);
  const [evaluationInfo, setEvaluationInfo] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    const loadJson = async (path) => {
      const response = await fetch(`${API_BASE_URL}${path}`, { signal: controller.signal });
      if (!response.ok) throw new Error(`${path} failed`);
      return response.json();
    };

    loadJson("/api/health").then((data) => { setHealth(data); setApiStatus("online"); }).catch((error) => {
      if (error.name !== "AbortError") setApiStatus("offline");
    });
    loadJson("/api/database-info").then(setDatabaseInfo).catch(() => setDatabaseInfo(null));
    loadJson("/api/evaluation").then(setEvaluationInfo).catch(() => setEvaluationInfo(null));
    return () => controller.abort();
  }, []);

  const handleGenerate = async () => {
    const normalizedQuestion = question.trim();
    if (!normalizedQuestion) {
      setNotice({ type: "error", text: "请输入需要分析的问题。" });
      return;
    }

    setIsGenerating(true);
    setNotice({ type: "info", text: "Agent 正在读取 Schema、生成 SQL 并执行查询..." });
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: normalizedQuestion, db_path: "data/northwind/northwind.db", db_id: "northwind" }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || `Agent API 请求失败 (${response.status})`);

      const execution = payload.execution_result || {};
      setSqlPlan(payload.sql_plan || {});
      setGeneratedSql(payload.generated_sql || "-- Agent 未返回 SQL");
      setSqlExplanation(payload.sql_explanation || "");
      setColumns(execution.columns || []);
      setRows(execution.rows || []);
      setRowCount(execution.row_count || 0);
      setFinalAnswer(payload.final_answer || {});
      setTrace(payload.trace || []);
      setFallbackUsed(Boolean(payload.fallback_used));
      setApiStatus("online");

      if (!execution.success) {
        setNotice({ type: "error", text: execution.error || payload.error || "SQL 执行失败。" });
      } else if (payload.fallback_used) {
        setNotice({ type: "warning", text: `查询已执行，部分 Agent 步骤使用了本地 fallback。${payload.final_answer?.answer || ""}` });
      } else {
        setNotice({ type: "success", text: payload.final_answer?.answer || `SQL 执行成功，返回 ${execution.row_count || 0} 行。` });
      }
    } catch (error) {
      setApiStatus("offline");
      setNotice({ type: "error", text: `无法连接 DataPilot Agent：${error.message}。请确认 FastAPI 服务已启动。` });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopySql = async () => {
    try {
      await navigator.clipboard.writeText(generatedSql);
      setCopyStatus("已复制");
    } catch {
      setCopyStatus("复制失败");
    }
    window.setTimeout(() => setCopyStatus(""), 1600);
  };

  const handleExport = () => {
    if (!rows.length) return;
    const csv = [columns, ...rows.map((row) => columns.map((column) => row[column]))]
      .map((values) => values.map(csvCell).join(","))
      .join("\n");
    const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "datapilot-query-result.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const sqlProps = {
    generatedSql,
    explanation: sqlExplanation,
    onCopy: handleCopySql,
    onFullscreen: () => setIsSqlModalOpen(true),
    copyStatus,
  };
  const resultProps = { columns, rows, rowCount, onExport: handleExport };
  const questionProps = { question, onQuestionChange: setQuestion, onGenerate: handleGenerate, isGenerating, notice };

  const view = useMemo(() => {
    if (activeView === "database") return <DatabaseView databaseInfo={databaseInfo} />;
    if (activeView === "analysis") return <AnalysisView sqlPlan={sqlPlan} sqlProps={sqlProps} resultProps={resultProps} finalAnswer={finalAnswer} fallbackUsed={fallbackUsed} onBack={() => setActiveView("home")} />;
    if (activeView === "trace") return <div className="viewStack narrowView"><TraceCard trace={trace} full /></div>;
    if (activeView === "evaluation") return <EvaluationView evaluationInfo={evaluationInfo} />;
    if (activeView === "settings") return <SettingsView health={health} apiStatus={apiStatus} />;
    return <HomeView questionProps={questionProps} sqlProps={sqlProps} resultProps={resultProps} finalAnswer={finalAnswer} fallbackUsed={fallbackUsed} databaseInfo={databaseInfo} apiStatus={apiStatus} evaluationInfo={evaluationInfo} trace={trace} />;
  }, [activeView, apiStatus, columns, copyStatus, databaseInfo, evaluationInfo, fallbackUsed, finalAnswer, generatedSql, health, isGenerating, notice, question, rowCount, rows, sqlExplanation, sqlPlan, trace]);

  return (
    <div className="appShell">
      <Sidebar activeView={activeView} collapsed={sidebarCollapsed} onNavigate={setActiveView} onToggle={() => setSidebarCollapsed((value) => !value)} />
      <main className="mainArea">
        <Header activeView={activeView} apiStatus={apiStatus} />
        {view}
      </main>
      {isSqlModalOpen && <SqlModal sql={generatedSql} onClose={() => setIsSqlModalOpen(false)} />}
    </div>
  );
}

function getNodeStatus(trace, nodeId) {
  const events = trace.filter((event) => event.node === nodeId);
  if (events.some((event) => event.status === "error")) return "error";
  if (events.some((event) => event.status === "end")) return "success";
  if (events.some((event) => event.status === "start")) return "running";
  return "pending";
}

function buildMetricItems(evaluationInfo) {
  if (!evaluationInfo?.available || !evaluationInfo.metrics) return [];
  const metrics = evaluationInfo.metrics;
  return [
    ["SQL Valid Rate", metrics.sql_valid_rate, "percent"],
    ["Execution Accuracy", metrics.execution_accuracy, "percent"],
    ["Repair Success Rate", metrics.repair_success_rate, "percent"],
    ["Judge Score", metrics.average_judge_score, "score"],
  ].map(([label, rawValue, type]) => {
    const value = Number(rawValue || 0);
    return {
      label,
      value: type === "score" ? `${value.toFixed(2)} / 5` : `${(value * 100).toFixed(1)}%`,
      percent: type === "score" ? value * 20 : value * 100,
    };
  });
}

function formatCell(value) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  return String(value);
}

function formatTime(timestamp) {
  if (!timestamp) return "--:--:--";
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleTimeString("zh-CN", { hour12: false });
}

function formatNodeName(node) {
  return nodeLabels[node] || node;
}

function formatStatus(status) {
  return { start: "开始", end: "成功", error: "失败" }[status] || status;
}

function csvCell(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

createRoot(document.getElementById("root")).render(<App />);
