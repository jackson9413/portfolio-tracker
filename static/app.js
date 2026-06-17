// Portfolio Tracker frontend - vanilla JS
let sectorChart = null;
let typeChart = null;

const fmt = (n) => "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct = (n) => (n >= 0 ? "+" : "") + Number(n).toFixed(2) + "%";
const $ = (id) => document.getElementById(id);

async function fetchJSON(url, opts = {}) {
    const res = await fetch(url, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

function renderSummary(s) {
    $("total-value").textContent = fmt(s.total_value);
    $("total-cost").textContent = fmt(s.total_cost);
    $("total-pl").textContent = fmt(s.total_pl);
    $("total-pl-pct").textContent = fmtPct(s.total_pl_pct);
    $("position-count").textContent = s.position_count;

    // Color the P/L based on sign
    const plEl = $("total-pl");
    const pctEl = $("total-pl-pct");
    plEl.className = "card-value " + (s.total_pl >= 0 ? "green" : "red");
    pctEl.className = "card-value " + (s.total_pl_pct >= 0 ? "green" : "red");
}

function renderHoldings(holdings) {
    const tbody = $("holdings-body");
    if (holdings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" class="empty">No holdings yet. Add one above or load demo data.</td></tr>';
        return;
    }
    tbody.innerHTML = holdings.map(h => `
        <tr>
            <td><span class="ticker">${h.ticker}</span></td>
            <td><span class="badge ${h.asset_type}">${h.asset_type}</span></td>
            <td>${h.sector}</td>
            <td>${h.shares}</td>
            <td>${fmt(h.cost_basis)}</td>
            <td>${fmt(h.price)}</td>
            <td class="${h.change_pct >= 0 ? 'green' : 'red'}">${fmtPct(h.change_pct)}</td>
            <td>${fmt(h.value)}</td>
            <td class="${h.pl >= 0 ? 'green' : 'red'}">${fmt(h.pl)}</td>
            <td class="${h.pl_pct >= 0 ? 'green' : 'red'}">${fmtPct(h.pl_pct)}</td>
            <td><button class="delete-btn" data-id="${h.id}">✕</button></td>
        </tr>
    `).join("");

    // Wire up delete buttons
    tbody.querySelectorAll(".delete-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            if (!confirm(`Delete holding ${btn.dataset.id}?`)) return;
            await fetchJSON(`/api/holdings/${btn.dataset.id}`, { method: "DELETE" });
            await loadAll();
        });
    });
}

function renderCharts(allocation) {
    const sectorColors = ["#4ea1ff", "#3fb950", "#f0b341", "#c779ff", "#f85149", "#39c5cf", "#ff7b72"];
    const typeColors = ["#4ea1ff", "#f0b341", "#c779ff"];

    const sectorLabels = allocation.by_sector.map(s => s.label);
    const sectorData = allocation.by_sector.map(s => s.value);
    const typeLabels = allocation.by_type.map(s => s.label);
    const typeData = allocation.by_type.map(s => s.value);

    const baseOpts = (labels, data, colors) => ({
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: colors,
                borderColor: "#1a2028",
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#e6edf3", font: { size: 11 }, padding: 12 }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.label}: ${fmt(ctx.parsed)}`
                    }
                }
            }
        }
    });

    if (sectorChart) sectorChart.destroy();
    if (typeChart) typeChart.destroy();

    if (sectorLabels.length === 0) {
        document.getElementById("sector-chart").getContext("2d").clearRect(0, 0, 300, 300);
        document.getElementById("type-chart").getContext("2d").clearRect(0, 0, 300, 300);
        return;
    }

    sectorChart = new Chart($("sector-chart"), baseOpts(sectorLabels, sectorData, sectorColors));
    typeChart = new Chart($("type-chart"), baseOpts(typeLabels, typeData, typeColors));
}

async function renderTransactions() {
    const data = await fetchJSON("/api/transactions");
    const tbody = $("tx-body");
    if (data.transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">No transactions yet.</td></tr>';
        return;
    }
    tbody.innerHTML = data.transactions.map(t => `
        <tr>
            <td>${t.date}</td>
            <td><span class="ticker">${t.ticker}</span></td>
            <td><span class="badge ${t.action}">${t.action}</span></td>
            <td>${t.shares}</td>
            <td>${fmt(t.price)}</td>
            <td>${t.notes || ""}</td>
        </tr>
    `).join("");
}

async function loadAll() {
    try {
        const [holdings, allocation] = await Promise.all([
            fetchJSON("/api/holdings"),
            fetchJSON("/api/allocation"),
        ]);
        renderSummary(holdings.summary);
        renderHoldings(holdings.holdings);
        renderCharts(allocation);
        await renderTransactions();
    } catch (err) {
        console.error("load failed:", err);
    }
}

// Add holding form
$("add-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const data = Object.fromEntries(new FormData(form).entries());
    if (data.shares) data.shares = parseFloat(data.shares);
    if (data.cost_basis) data.cost_basis = parseFloat(data.cost_basis);
    try {
        const res = await fetchJSON("/api/holdings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        if (res.error) {
            alert(res.error);
            return;
        }
        form.reset();
        await loadAll();
    } catch (err) {
        alert("Failed to add: " + err.message);
    }
});

// Buttons
$("seed-btn").addEventListener("click", async () => {
    if (!confirm("Load demo portfolio? (only works on an empty portfolio)")) return;
    const res = await fetchJSON("/api/seed", { method: "POST" });
    alert(res.msg || "Demo loaded");
    await loadAll();
});

$("refresh-btn").addEventListener("click", loadAll);

// Initial load
loadAll();

// Auto-refresh prices every 60s
setInterval(loadAll, 60000);
