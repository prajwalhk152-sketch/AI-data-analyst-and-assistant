const API_URL = "/api/dashboard";
const uploadUrl = "/api/upload";
const analyzeUrl = "/api/analyze";
const analyzeTableUrl = "/api/analyze-table";
const llmPromptUrl = "/api/llm/prompt";
const llmSqlUrl = "/api/llm/sql";
const llmInsightsUrl = "/api/llm/insights";
const refreshButton = document.getElementById("refreshButton");
const themeToggle = document.getElementById("themeToggle");
const clearButton = document.getElementById("clearButton");
const revenueCard = document.getElementById("revenueCard");
const profitCard = document.getElementById("profitCard");
const ordersCard = document.getElementById("ordersCard");
const growthCard = document.getElementById("growthCard");
const uploadButton = document.getElementById("uploadButton");
const dataFileInput = document.getElementById("dataFileInput");
const selectedFileName = document.getElementById("selectedFileName");
const uploadStatus = document.getElementById("uploadStatus");
const askButton = document.getElementById("askButton");
const analysisResult = document.getElementById("analysisResult");
const analysisOverviewMode = document.getElementById("analysisOverviewMode");
const analysisTableMode = document.getElementById("analysisTableMode");
const analysisTablePanel = document.getElementById("analysisTablePanel");
const analysisTable = document.getElementById("analysisTable");
const llmPromptInput = document.getElementById("llmPromptInput");
const llmSendButton = document.getElementById("llmSendButton");
const llmSqlButton = document.getElementById("llmSqlButton");
const llmInsightsButton = document.getElementById("llmInsightsButton");
const llmResponseResult = document.getElementById("llmResponseResult");
const chartTypeSelect = document.getElementById("chartTypeSelect");
const xAxisSelect = document.getElementById("xAxisSelect");
const yAxisSelect = document.getElementById("yAxisSelect");
const generateChartBtn = document.getElementById("generateChartBtn");
const checkFileQualityButton = document.getElementById("checkFileQualityButton");
const fileCheckResult = document.getElementById("fileCheckResult");
const waffleChartContainer = document.getElementById("waffleChartContainer");

let dynamicChart;
let currentData = null;
let availableColumns = [];
let analysisMode = "overview";

// Vibrant color palette for charts
const colorPalette = [
  "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
  "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B88B", "#ABEBC6",
  "#F1948A", "#85C1E2", "#F8B88B", "#52BE80", "#D7BCCB"
];

// Initialize theme
function initTheme() {
  const savedTheme = localStorage.getItem("theme") || "dark";
  if (savedTheme === "light") {
    document.documentElement.classList.add("light-mode");
    themeToggle.textContent = "☀️";
  } else {
    document.documentElement.classList.remove("light-mode");
    themeToggle.textContent = "🌙";
  }
}

// Check that the page is served over HTTP(S) (not opened via file://)
function ensureServedFromServer() {
  if (!location || !location.protocol || !location.protocol.startsWith("http")) {
    const msg = "Please open the dashboard via the local server: http://127.0.0.1:5000/dashboard";
    if (uploadStatus) uploadStatus.textContent = msg;
    console.error("Dashboard must be served by the backend.", { location: location.href });
    // disable buttons to avoid confusing errors
    [uploadButton, generateChartBtn, askButton, llmSendButton, llmSqlButton, llmInsightsButton, refreshButton, clearButton].forEach(el => {
      if (el) el.disabled = true;
    });
    return false;
  }
  return true;
}

// Toggle theme
function toggleTheme() {
  const isLight = document.documentElement.classList.toggle("light-mode");
  localStorage.setItem("theme", isLight ? "light" : "dark");
  themeToggle.textContent = isLight ? "☀️" : "🌙";
}

// Clear all data
function clearAllData() {
  if (confirm("Are you sure you want to clear all data?")) {
    dataFileInput.value = "";
    uploadStatus.textContent = "No file uploaded yet.";
    analysisResult.textContent = "Upload a dataset and click Analyze.";
    analysisResult.hidden = false;
    if (analysisTablePanel) analysisTablePanel.hidden = true;
    if (analysisTable) analysisTable.innerHTML = "";
    if (llmPromptInput) llmPromptInput.value = "";
    if (llmResponseResult) llmResponseResult.textContent = "Upload data, then send a prompt or generate insights.";
    const revenueValue = revenueCard?.querySelector(".kpi-value");
    const revenueDetail = revenueCard?.querySelector(".kpi-detail");
    if (revenueValue) revenueValue.textContent = "$0";
    if (revenueDetail) revenueDetail.textContent = "Detected currency: USD";
    profitCard.querySelector(".kpi-value").textContent = "$0";
    ordersCard.querySelector(".kpi-value").textContent = "0";
    growthCard.querySelector(".kpi-value").textContent = "$0";
    xAxisSelect.innerHTML = '<option value="">Select column...</option>';
    yAxisSelect.innerHTML = '<option value="">Select column...</option>';
    if (dynamicChart) {
      dynamicChart.destroy();
      dynamicChart = null;
    }
    currentData = null;
    availableColumns = [];
    if (selectedFileName) {
      selectedFileName.textContent = "No file chosen";
    }
  }
}

function formatCurrency(value) {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

function formatLargeCurrency(value, symbol = "$", code = "USD") {
  const absValue = Math.abs(value);
  const sign = value < 0 ? "-" : "";

  if (absValue >= 1e12) {
    return `${sign}${symbol}${(absValue / 1e12).toFixed(2)}T`;
  }
  if (absValue >= 1e9) {
    return `${sign}${symbol}${(absValue / 1e9).toFixed(2)}B`;
  }
  if (absValue >= 1e6) {
    return `${sign}${symbol}${(absValue / 1e6).toFixed(2)}M`;
  }
  if (absValue >= 1e3) {
    return `${sign}${symbol}${(absValue / 1e3).toFixed(0)}K`;
  }
  return `${sign}${symbol}${absValue.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function detectCurrencyType(data) {
  const currencyMap = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
  };
  const symbolMap = {
    USD: "$",
    EUR: "€",
    GBP: "£",
    JPY: "¥",
  };

  if (!data || !data.length) {
    return { code: "USD", symbol: "$" };
  }

  const columns = Object.keys(data[0]);
  const lowerCols = columns.map(c => c.toLowerCase());

  if (lowerCols.some(c => c.includes("usd") || c.includes("dollar") || c.includes("revenue"))) {
    return { code: "USD", symbol: "$" };
  }
  if (lowerCols.some(c => c.includes("eur") || c.includes("euro"))) {
    return { code: "EUR", symbol: "€" };
  }
  if (lowerCols.some(c => c.includes("gbp") || c.includes("pound"))) {
    return { code: "GBP", symbol: "£" };
  }
  if (lowerCols.some(c => c.includes("jpy") || c.includes("yen"))) {
    return { code: "JPY", symbol: "¥" };
  }

  for (const row of data) {
    for (const value of Object.values(row)) {
      if (typeof value === "string") {
        for (const [symbol, code] of Object.entries(currencyMap)) {
          if (value.includes(symbol)) {
            return { code, symbol };
          }
        }
      }
    }
  }

  return { code: "USD", symbol: "$" };
}

function escapeHtml(text) {
  if (!text && text !== 0) return "";
  return text
    .toString()
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getNumericColumns(data) {
  if (!data || !data.length) return [];
  const first = data[0];
  return Object.keys(first).filter(key => typeof first[key] === "number");
}

function getOhlcColumns(columns) {
  const lower = columns.map(c => c.toLowerCase());
  return {
    date: columns[lower.indexOf("date")] || null,
    open: columns[lower.indexOf("open")] || null,
    high: columns[lower.indexOf("high")] || null,
    low: columns[lower.indexOf("low")] || null,
    close: columns[lower.indexOf("close")] || null,
  };
}

function renderWaffleChart(data) {
  waffleChartContainer.innerHTML = "";
  const rows = 10;
  const cols = 10;
  if (!data || !data.length) {
    waffleChartContainer.textContent = "Upload a dataset first to render a waffle chart.";
    return;
  }

  const firstRow = data[0];
  const categories = Object.keys(firstRow).filter(key => typeof firstRow[key] === "string");
  let categoryKey = categories[0] || null;

  if (!categoryKey) {
    const numericColumns = getNumericColumns(data);
    if (numericColumns.length < 1) {
      waffleChartContainer.textContent = "No suitable category data found for waffle chart.";
      return;
    }
    categoryKey = numericColumns[0];
  }

  const valueMap = data.reduce((acc, row) => {
    const key = row[categoryKey] || "Unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const entries = Object.entries(valueMap).sort((a, b) => b[1] - a[1]).slice(0, 5);
  const total = entries.reduce((sum, item) => sum + item[1], 0);
  const colors = ["#10B981", "#22C55E", "#38BDF8", "#FACC15", "#F97316"];

  const cells = [];
  entries.forEach(([label, count], idx) => {
    const percent = Math.round((count / total) * rows * cols);
    for (let i = 0; i < percent; i += 1) {
      cells.push({ label, color: colors[idx] || "#a78bfa" });
    }
  });
  while (cells.length < rows * cols) {
    cells.push({ label: "Other", color: "rgba(255,255,255,0.08)" });
  }

  const grid = document.createElement("div");
  grid.className = "waffle-grid";
  grid.style.gridTemplateColumns = `repeat(${cols}, minmax(0, 1fr))`;

  cells.forEach(cell => {
    const cellEl = document.createElement("div");
    cellEl.className = "waffle-cell";
    cellEl.style.background = cell.color;
    cellEl.title = cell.label;
    grid.appendChild(cellEl);
  });

  const legend = document.createElement("div");
  legend.className = "waffle-legend";
  entries.forEach(([label, count], idx) => {
    const item = document.createElement("div");
    item.className = "waffle-legend-item";
    item.innerHTML = `<span class="waffle-legend-color" style="background:${colors[idx]};"></span><span>${escapeHtml(label)} (${Math.round((count / total) * 100)}%)</span>`;
    legend.appendChild(item);
  });

  const title = document.createElement("div");
  title.className = "waffle-chart-title";
  title.textContent = `Waffle chart by ${categoryKey}`;

  waffleChartContainer.appendChild(title);
  waffleChartContainer.appendChild(grid);
  waffleChartContainer.appendChild(legend);
}

function toggleChartView(showCanvas) {
  const canvas = document.getElementById("dynamicChart");
  if (!canvas) return;
  if (showCanvas) {
    canvas.hidden = false;
    waffleChartContainer.hidden = true;
    canvas.style.display = "block";
    waffleChartContainer.style.display = "none";
  } else {
    canvas.hidden = true;
    waffleChartContainer.hidden = false;
    canvas.style.display = "none";
    waffleChartContainer.style.display = "grid";
  }
}

function updateKpis(kpis) {
  const datasetPreview = currentData && currentData.preview ? currentData.preview : [];
  const currencyInfo = detectCurrencyType(datasetPreview);
  const formattedValue = formatLargeCurrency(kpis.numeric_sum, currencyInfo.symbol, currencyInfo.code);

  const revenueValue = revenueCard?.querySelector(".kpi-value");
  const revenueDetail = revenueCard?.querySelector(".kpi-detail");
  if (revenueValue) revenueValue.textContent = formattedValue;
  if (revenueDetail) revenueDetail.textContent = `Detected currency: ${currencyInfo.code}`;
  profitCard.querySelector(".kpi-value").textContent = kpis.columns.toLocaleString();
  ordersCard.querySelector(".kpi-value").textContent = kpis.numeric_fields.toLocaleString();
  growthCard.querySelector(".kpi-value").textContent = formattedValue;
}

async function uploadFile() {
  const file = dataFileInput.files[0];
  if (!file) {
    uploadStatus.textContent = "Please select a CSV or XLSX file first.";
    return;
  }

  uploadStatus.textContent = `Uploading ${file.name}...`;
  console.debug("Uploading file", file.name, file.type);
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(uploadUrl, { method: "POST", body: formData });
    const data = await response.json();

    if (!response.ok) {
      uploadStatus.textContent = `Upload failed: ${data.error || response.statusText}`;
      return;
    }

    uploadStatus.textContent = `Uploaded ${data.filename}: ${data.rows} rows, ${data.columns.length} columns.`;
    // show a quick preview in the analysis area for visibility
    if (data.preview && data.preview.length) {
      const cols = Object.keys(data.preview[0]);
      const header = '<tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr>';
      const rows = data.preview.map(r => '<tr>' + cols.map(c => '<td>' + (r[c] ?? '') + '</td>').join('') + '</tr>').join('');
      analysisResult.innerHTML = '<div class="analysis-summary"><strong>Preview:</strong></div><table class="preview-table"><thead>' + header + '</thead><tbody>' + rows + '</tbody></table>';
    }
    availableColumns = data.columns;
    populateAxisSelectors();
    currentData = data;
    loadDashboard();
  } catch (error) {
    uploadStatus.textContent = "Upload failed. Check your server and try again.";
    console.error(error);
  }
}

function populateAxisSelectors() {
  // Clear existing options (except first placeholder)
  xAxisSelect.querySelectorAll("option:not(:first-child)").forEach(opt => opt.remove());
  yAxisSelect.querySelectorAll("option:not(:first-child)").forEach(opt => opt.remove());

  // Add column options
  availableColumns.forEach(col => {
    const xOption = document.createElement("option");
    xOption.value = col;
    xOption.textContent = col;
    xAxisSelect.appendChild(xOption);

    const yOption = document.createElement("option");
    yOption.value = col;
    yOption.textContent = col;
    yAxisSelect.appendChild(yOption);
  });

  // Set default selections if available
  if (availableColumns.length >= 2) {
    xAxisSelect.value = availableColumns[0];
    yAxisSelect.value = availableColumns[1];
  }
}

function setAnalysisMode(mode) {
  analysisMode = mode;
  analysisOverviewMode?.classList.toggle("active", mode === "overview");
  analysisTableMode?.classList.toggle("active", mode === "table");

  if (mode === "overview") {
    analysisResult.hidden = false;
    if (analysisTablePanel) analysisTablePanel.hidden = true;
  } else {
    analysisResult.hidden = true;
    if (analysisTablePanel) analysisTablePanel.hidden = false;
  }
}

async function generateDatasetOverview() {
  analysisResult.textContent = "Generating dataset overview...";
  setAnalysisMode("overview");

  try {
    const response = await fetch(analyzeUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await response.json();

    if (!response.ok) {
      analysisResult.textContent = `Analysis failed: ${data.error || response.statusText}`;
      return;
    }

    renderAnalysisResponse(data);
  } catch (error) {
    analysisResult.textContent = "Overview failed. Check your API connection.";
    console.error(error);
  }
}

async function generateOverviewTable() {
  setAnalysisMode("table");
  if (!analysisTable) return;
  analysisTable.textContent = "Generating overview table...";

  try {
    const response = await fetch(analyzeTableUrl, { method: "POST" });
    const data = await response.json();

    if (!response.ok) {
      analysisResult.hidden = false;
      if (analysisTablePanel) analysisTablePanel.hidden = true;
      analysisResult.textContent = `Overview table failed: ${data.error || response.statusText}`;
      return;
    }

    renderOverviewTable(data);
  } catch (error) {
    analysisResult.hidden = false;
    if (analysisTablePanel) analysisTablePanel.hidden = true;
    analysisResult.textContent = "Overview table failed. Check your API connection.";
    console.error(error);
  }
}

function runAnalyzeAction() {
  if (analysisMode === "table") {
    generateOverviewTable();
  } else {
    generateDatasetOverview();
  }
}

async function checkUploadedFileQuality() {
  if (!currentData) {
    fileCheckResult.textContent = "Upload a file first before checking its data quality.";
    return;
  }

  fileCheckResult.textContent = "Checking uploaded file quality...";

  try {
    const response = await fetch("/api/check-file", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: "Check this uploaded dataset for data quality issues, missing values, header consistency, and anomalies." }),
    });
    const data = await response.json();

    if (!response.ok) {
      fileCheckResult.textContent = `File quality check failed: ${data.error || response.statusText}`;
      return;
    }

    fileCheckResult.innerHTML = `
      <div class="analysis-summary"><strong>File Quality Check:</strong><p>${escapeHtml(data.quality_check)}</p></div>
    `;
  } catch (error) {
    fileCheckResult.textContent = "File quality check failed. Check your API connection.";
    console.error(error);
  }
}

function renderAnalysisResponse(data) {
  const answer = data.analysis || data.answer || "No answer returned.";
  analysisResult.innerHTML = `
    <div class="analysis-summary"><strong>Overview:</strong><p>${escapeHtml(answer)}</p></div>
  `;
}

function renderOverviewTable(data) {
  const columns = data.columns || [];
  const rows = data.rows || [];

  if (!columns.length || !rows.length) {
    analysisTable.innerHTML = '<div class="analysis-summary">No overview table data returned.</div>';
    return;
  }

  const header = columns.map(column => `<th>${escapeHtml(column)}</th>`).join("");
  const body = rows.map(row => {
    const cells = columns.map(column => `<td>${escapeHtml(row[column])}</td>`).join("");
    return `<tr>${cells}</tr>`;
  }).join("");

  analysisTable.innerHTML = `
    <div class="analysis-summary"><strong>${escapeHtml(data.title || "Overview Table")}</strong></div>
    <div class="preview-table-wrapper">
      <table class="preview-table">
        <thead><tr>${header}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  `;
}

function renderLlmResponse(data, mode) {
  if (mode === "sql") {
    const sql = data.sql ? `<pre class="analysis-sql">${escapeHtml(data.sql)}</pre>` : "";
    const insight = data.insight ? `<p>${escapeHtml(data.insight)}</p>` : "";
    const rows = Array.isArray(data.result) ? `<p>${data.result.length} row(s) returned.</p>` : "";
    llmResponseResult.innerHTML = `
      <div class="analysis-summary"><strong>Generated SQL:</strong>${sql}${insight}${rows}</div>
    `;
    return;
  }

  const title = mode === "insights" ? "Generated Insights:" : "LLM Response:";
  const responseText = data.response || data.insight || "No response returned.";
  llmResponseResult.innerHTML = `
    <div class="analysis-summary"><strong>${title}</strong><p>${escapeHtml(responseText)}</p></div>
  `;
}

async function sendLlmRequest(mode) {
  const prompt = llmPromptInput.value.trim();
  if (mode !== "insights" && !prompt) {
    llmResponseResult.textContent = "Please enter a prompt or question first.";
    return;
  }

  const label = mode === "sql" ? "Generating SQL..." : mode === "insights" ? "Generating insights..." : "Sending prompt...";
  llmResponseResult.textContent = label;

  const url = mode === "sql" ? llmSqlUrl : mode === "insights" ? llmInsightsUrl : llmPromptUrl;
  const body = mode === "sql"
    ? { question: prompt, execute: true }
    : mode === "insights"
      ? {}
      : { prompt, include_data_context: true };

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();

    if (!response.ok) {
      llmResponseResult.textContent = `LLM request failed: ${data.error || response.statusText}`;
      return;
    }

    renderLlmResponse(data, mode);
  } catch (error) {
    llmResponseResult.textContent = "LLM request failed. Check your API connection.";
    console.error(error);
  }
}

function aggregateByColumn(data, labelColumn, valueColumn, limit = 20) {
  const grouped = new Map();

  data.forEach(row => {
    const rawLabel = row[labelColumn];
    const label = rawLabel === null || rawLabel === undefined || rawLabel === "" ? "Unknown" : String(rawLabel);
    const value = Number.parseFloat(row[valueColumn]);
    grouped.set(label, (grouped.get(label) || 0) + (Number.isFinite(value) ? value : 0));
  });

  return Array.from(grouped.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, limit);
}

function createWaterfallChart(xAxis, yAxis, data) {
  const canvas = document.getElementById("dynamicChart");
  if (!canvas) return;

  const context = canvas.getContext("2d");
  const entries = aggregateByColumn(data, xAxis, yAxis);

  if (!entries.length) {
    alert("No numeric values were found for the selected waterfall chart.");
    return;
  }

  let runningTotal = 0;
  const bars = entries.map(item => {
    const start = runningTotal;
    runningTotal += item.value;
    return {
      label: item.label,
      value: item.value,
      cumulative: runningTotal,
      range: [start, runningTotal],
    };
  });

  bars.push({
    label: "Total",
    value: runningTotal,
    cumulative: runningTotal,
    range: [0, runningTotal],
    isTotal: true,
  });

  if (dynamicChart) {
    dynamicChart.destroy();
  }

  const isDarkMode = !document.documentElement.classList.contains("light-mode");
  const gridColor = isDarkMode ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)";
  const textColor = isDarkMode ? "#f8fafc" : "#1a1a1a";

  dynamicChart = new Chart(context, {
    type: "bar",
    data: {
      labels: bars.map(item => item.label),
      datasets: [{
        label: `${yAxis} running contribution`,
        data: bars.map(item => item.range),
        backgroundColor: bars.map(item => {
          if (item.isTotal) return "#38BDF8";
          return item.value >= 0 ? "#10B981" : "#F97316";
        }),
        borderColor: bars.map(item => {
          if (item.isTotal) return "#0EA5E9";
          return item.value >= 0 ? "#059669" : "#EA580C";
        }),
        borderWidth: 2,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            color: textColor,
            font: { size: 12, weight: "bold" },
            padding: 15,
            usePointStyle: true,
          },
        },
        tooltip: {
          backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.9)" : "rgba(255, 255, 255, 0.95)",
          titleColor: textColor,
          bodyColor: textColor,
          borderColor: "#38BDF8",
          borderWidth: 2,
          padding: 12,
          callbacks: {
            label: context => {
              const item = bars[context.dataIndex];
              if (item.isTotal) return `Total: ${item.cumulative.toLocaleString()}`;
              return `Change: ${item.value.toLocaleString()} | Running total: ${item.cumulative.toLocaleString()}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: gridColor, display: true },
          ticks: { color: textColor, font: { size: 11 }, maxRotation: 45, minRotation: 0 },
        },
        y: {
          grid: { color: gridColor, display: true },
          ticks: { color: textColor, font: { size: 11 } },
        },
      },
    },
  });
}

function createChart(xAxis, yAxis, chartType, data) {
  const canvas = document.getElementById("dynamicChart");
  if (!canvas) return;

  const context = canvas.getContext("2d");

  // Prepare chart data based on selected columns
  let chartData = { labels: [], datasets: [] };
  const labels = data.map(row => row[xAxis]);
  const values = data.map(row => parseFloat(row[yAxis]) || 0);
  const primaryColor = colorPalette[0];
  const isArea = chartType === "area";

  if (["pie", "doughnut", "polarArea", "radar"].includes(chartType)) {
    chartData = {
      labels,
      datasets: [{
        label: yAxis,
        data: values,
        backgroundColor: chartType === "radar"
          ? "rgba(56, 189, 248, 0.45)"
          : colorPalette.slice(0, Math.min(labels.length, colorPalette.length)),
        borderColor: chartType === "radar" ? "#38bdf8" : "white",
        borderWidth: chartType === "radar" ? 2 : 3,
        fill: chartType === "radar",
        tension: chartType === "radar" ? 0.4 : undefined,
      }],
    };
  } else {
    chartData = {
      labels,
      datasets: [{
        label: yAxis,
        data: values,
        backgroundColor: isArea
          ? "rgba(59, 130, 246, 0.35)"
          : chartType === "bar"
            ? colorPalette.slice(0, Math.min(labels.length, colorPalette.length))
            : primaryColor,
        borderColor: primaryColor,
        borderWidth: chartType === "line" || isArea ? 3 : 2,
        fill: isArea,
        tension: chartType === "line" || isArea ? 0.4 : undefined,
        pointBackgroundColor: chartType === "scatter" ? colorPalette[0] : undefined,
        pointBorderColor: chartType === "scatter" ? "white" : undefined,
        pointBorderWidth: chartType === "scatter" ? 2 : undefined,
        pointRadius: chartType === "scatter" ? 6 : undefined,
        pointHoverRadius: chartType === "scatter" ? 8 : undefined,
      }],
    };
  }

  if (dynamicChart) {
    dynamicChart.destroy();
  }

  const isDarkMode = !document.documentElement.classList.contains("light-mode");
  const gridColor = isDarkMode ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)";
  const textColor = isDarkMode ? "#f8fafc" : "#1a1a1a";

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: "top",
        labels: {
          color: textColor,
          font: { size: 12, weight: "bold" },
          padding: 15,
          usePointStyle: true,
        },
      },
      tooltip: {
        backgroundColor: isDarkMode ? "rgba(15, 23, 42, 0.9)" : "rgba(255, 255, 255, 0.9)",
        titleColor: textColor,
        bodyColor: textColor,
        borderColor: colorPalette[0],
        borderWidth: 2,
        padding: 12,
        cornerRadius: 8,
        titleFont: { size: 13, weight: "bold" },
        bodyFont: { size: 12 },
      },
    },
  };

  if (!["pie", "doughnut", "polarArea", "radar"].includes(chartType)) {
    chartOptions.scales = {
      x: {
        grid: { color: gridColor, display: true },
        ticks: { color: textColor, font: { size: 11 } },
      },
      y: {
        beginAtZero: true,
        grid: { color: gridColor, display: true },
        ticks: { color: textColor, font: { size: 11 } },
      },
    };
  }

  const chartTypeKey = chartType === "area" ? "line" : chartType;

  dynamicChart = new Chart(context, {
    type: chartTypeKey,
    data: chartData,
    options: chartOptions,
  });
}

function generateChart() {
  const xAxis = xAxisSelect.value;
  const yAxis = yAxisSelect.value;
  const chartType = chartTypeSelect.value;

  if (!currentData || !currentData.preview) {
    alert("No data loaded. Upload a file first.");
    return;
  }

  if (chartType === "waffle") {
    toggleChartView(false);
    renderWaffleChart(currentData.preview);
    return;
  }

  toggleChartView(true);

  if (!xAxis || !yAxis) {
    alert("Please select both X-axis and Y-axis columns.");
    return;
  }

  if (chartType === "waterfall") {
    createWaterfallChart(xAxis, yAxis, currentData.preview);
    return;
  }

  createChart(xAxis, yAxis, chartType, currentData.preview);
}

async function loadDashboard() {
  try {
    const response = await fetch(API_URL);
    if (!response.ok) {
      throw new Error(`Dashboard request failed: ${response.status}`);
    }

    const data = await response.json();
    const { kpis } = data;
    updateKpis(kpis);
  } catch (error) {
    console.error(error);
  }
}

chartTypeSelect?.addEventListener("change", generateChart);
generateChartBtn?.addEventListener("click", generateChart);
uploadButton?.addEventListener("click", uploadFile);
checkFileQualityButton?.addEventListener("click", checkUploadedFileQuality);
analysisOverviewMode?.addEventListener("click", generateDatasetOverview);
analysisTableMode?.addEventListener("click", generateOverviewTable);
askButton?.addEventListener("click", runAnalyzeAction);
llmSendButton?.addEventListener("click", () => sendLlmRequest("prompt"));
llmSqlButton?.addEventListener("click", () => sendLlmRequest("sql"));
llmInsightsButton?.addEventListener("click", () => sendLlmRequest("insights"));
refreshButton.addEventListener("click", loadDashboard);
themeToggle?.addEventListener("click", toggleTheme);
dataFileInput?.addEventListener("change", () => {
  const file = dataFileInput.files && dataFileInput.files[0];
  selectedFileName.textContent = file ? file.name : "No file chosen";
});
clearButton?.addEventListener("click", clearAllData);

// Initialize
initTheme();
loadDashboard();
