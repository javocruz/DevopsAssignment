var SCORECARD_PAIRS = [
  {decider: "stub", context: "basic"},
  {decider: "stub", context: "news"},
  {decider: "jev", context: "basic"},
  {decider: "jev", context: "news"}
];

var TABS = ["overview", "charts", "markets", "portfolio", "guide"];

var state = {
  markets: [],
  estimates: [],
  portfolio: {bets: [], total_pnl: 0},
  scorecards: {},
  pairChosen: false
};

var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

var COLOR = {
  ink: cssVar("--ink"),
  muted: cssVar("--muted"),
  line: cssVar("--border"),
  accent: cssVar("--accent"),
  accentDim: "rgba(79, 134, 247, 0.4)",
  market: cssVar("--market"),
  pos: cssVar("--good"),
  neg: cssVar("--bad")
};

Chart.defaults.color = COLOR.muted;
Chart.defaults.borderColor = COLOR.line;
Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
Chart.defaults.font.size = 13;
Chart.defaults.plugins.legend.position = "top";
Chart.defaults.plugins.legend.labels.color = COLOR.ink;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 10;
Chart.defaults.plugins.tooltip.padding = 10;
if (reduceMotion) {
  Chart.defaults.animation = false;
}

// ---------- Number formatting: the only place a number becomes text ----------

function isMissing(value) {
  return value === null || value === undefined;
}

// One decimal. A nonzero value that would round to 0.0% reads "<1%" instead of a misleading zero.
function fmtProb(value) {
  if (isMissing(value)) {
    return "none";
  }
  var pct = value * 100;
  if (value > 0 && pct < 0.05) {
    return "<1%";
  }
  return pct.toFixed(1) + "%";
}

// Two decimals. A nonzero price that would round to 0.00 reads "<0.01" so a long shot never looks free.
function fmtPrice(value) {
  if (isMissing(value)) {
    return "none";
  }
  if (value > 0 && value < 0.005) {
    return "<0.01";
  }
  return Number(value).toFixed(2);
}

// Unsigned money, for a stake.
function fmtAmount(value) {
  if (isMissing(value)) {
    return "none";
  }
  return Number(value).toFixed(2);
}

// Signed money, for profit and loss. Sign comes from the rounded text so "-0.00" never shows.
function fmtMoney(value) {
  if (isMissing(value)) {
    return "none";
  }
  var text = Number(value).toFixed(2);
  if (text === "0.00" || text === "-0.00") {
    return "0.00";
  }
  return value > 0 ? "+" + text : text;
}

// Edge in percentage points: Jev 40% against market 30% is +10.0 pts.
function fmtEdge(value) {
  var text = (value * 100).toFixed(1);
  if (text === "0.0" || text === "-0.0") {
    return "0.0 pts";
  }
  return (value > 0 ? "+" : "") + text + " pts";
}

function fmtBrier(value) {
  if (isMissing(value)) {
    return "none";
  }
  return Number(value).toFixed(3);
}

// ---------- Count-up: numbers roll from the last value shown to the new one ----------

var shownNumbers = {};
var rollTickets = {};

function formatCount(value) {
  return String(Math.round(value));
}

// Each element keeps a ticket, so a second render mid-roll cancels the first instead of fighting it.
function animateNumber(id, target, format) {
  var el = document.getElementById(id);
  var from = shownNumbers[id] === undefined ? 0 : shownNumbers[id];
  var ticket = (rollTickets[id] || 0) + 1;
  rollTickets[id] = ticket;
  shownNumbers[id] = target;
  if (reduceMotion || from === target) {
    el.textContent = format(target);
    return;
  }
  var startedAt = null;
  function step(now) {
    if (rollTickets[id] !== ticket) {
      return;
    }
    if (startedAt === null) {
      startedAt = now;
    }
    var progress = Math.min(1, (now - startedAt) / 800);
    var eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = format(from + (target - from) * eased);
    if (progress < 1) {
      window.requestAnimationFrame(step);
    }
  }
  window.requestAnimationFrame(step);
}

// A value with nothing to roll to (the word "none") stops any roll and shows the text.
function showPlain(id, text) {
  rollTickets[id] = (rollTickets[id] || 0) + 1;
  delete shownNumbers[id];
  byId(id).textContent = text;
}

function plural(count, word) {
  return count + " " + word + (count === 1 ? "" : "s");
}

function signClass(value) {
  if (isMissing(value) || value === 0) {
    return "";
  }
  return value > 0 ? "pos" : "neg";
}

function shorten(text, length) {
  if (isMissing(text) || text.length <= length) {
    return text;
  }
  return text.slice(0, length - 1) + "…";
}

// ---------- DOM helpers ----------

// Every piece of text goes in with textContent, so a market question cannot inject HTML.
function makeEl(tag, className, text) {
  var el = document.createElement(tag);
  if (className) {
    el.className = className;
  }
  if (text !== undefined) {
    el.textContent = isMissing(text) ? "" : text;
  }
  return el;
}

function byId(id) {
  return document.getElementById(id);
}

function clearBody(id) {
  byId(id).replaceChildren();
}

function setText(id, text) {
  byId(id).textContent = text;
}

// ---------- Feedback: status line and toasts ----------

function showStatus(text) {
  setText("status", text);
}

function toast(text, kind) {
  var el = makeEl("div", "toast " + (kind || "ok"), text);
  byId("toasts").appendChild(el);
  window.setTimeout(function () {
    el.remove();
  }, kind === "error" ? 7000 : 3500);
}

function reportError(error) {
  document.body.classList.remove("loading");
  showStatus(error.message);
  toast(error.message, "error");
}

function adminHeaders() {
  var token = byId("admin-token").value;
  if (token === "") {
    return {};
  }
  return {"X-Admin-Token": token};
}

function errorDetail(body) {
  if (body === null || isMissing(body.detail)) {
    return "";
  }
  if (typeof body.detail === "string") {
    return body.detail;
  }
  return JSON.stringify(body.detail);
}

// An error page may not be JSON, so a failed parse becomes null instead of hiding the real status.
async function getJson(path, options) {
  var response = await fetch(path, options);
  var body = null;
  try {
    body = await response.json();
  } catch (parseError) {
    body = null;
  }
  if (!response.ok) {
    var failure = new Error(response.status + " " + errorDetail(body));
    failure.status = response.status;
    throw failure;
  }
  return body;
}

// ---------- Loading ----------

function scorecardUrl(decider, context) {
  return "/scorecard?decider=" + encodeURIComponent(decider) + "&context=" + encodeURIComponent(context);
}

function pairKey(decider, context) {
  return decider + "/" + context;
}

var scorecardGeneration = 0;

// One request at a time. Parallel reads make FastAPI close the sqlite
// connection on a different thread than the one that opened it.
// A newer load drops this one so an older reply cannot overwrite it.
async function loadScorecards() {
  var generation = ++scorecardGeneration;
  var next = {};
  for (var i = 0; i < SCORECARD_PAIRS.length; i++) {
    var pair = SCORECARD_PAIRS[i];
    var card = await getJson(scorecardUrl(pair.decider, pair.context));
    if (generation !== scorecardGeneration) {
      return false;
    }
    next[pairKey(pair.decider, pair.context)] = card;
  }
  state.scorecards = next;
  return true;
}

async function refresh() {
  state.markets = await getJson("/markets");
  state.estimates = await getJson("/estimates");
  state.portfolio = await getJson("/portfolio");
  if (await loadScorecards() === false) {
    return;
  }
  choosePairOnce();
  renderAll();
  document.body.classList.remove("loading");
}

async function loadFooter() {
  var health = await getJson("/healthz");
  setText("schema-version", "Schema version " + health.schema_version);
}

// ---------- The active pair: every tab shows one decider + context ----------

function currentPair() {
  return {decider: byId("decider").value, context: byId("context").value};
}

function inPair(item) {
  var pair = currentPair();
  return item.decider === pair.decider && item.context_level === pair.context;
}

function selectedScorecard() {
  var pair = currentPair();
  return state.scorecards[pairKey(pair.decider, pair.context)] || null;
}

// Mixed runs show every market twice, so the first load picks one pair. Stub + basic wins if it has
// rows, otherwise the pair with the most estimates. After that the reader's choice is left alone.
function choosePairOnce() {
  if (state.pairChosen || state.estimates.length === 0) {
    return;
  }
  state.pairChosen = true;
  var best = SCORECARD_PAIRS[0];
  var bestCount = countEstimates(best);
  if (bestCount === 0) {
    SCORECARD_PAIRS.forEach(function (pair) {
      var count = countEstimates(pair);
      if (count > bestCount) {
        best = pair;
        bestCount = count;
      }
    });
  }
  byId("decider").value = best.decider;
  byId("context").value = best.context;
}

function countEstimates(pair) {
  return state.estimates.filter(function (estimate) {
    return estimate.decider === pair.decider && estimate.context_level === pair.context;
  }).length;
}

function pairEstimates() {
  return state.estimates.filter(inPair);
}

function pairBets() {
  return state.portfolio.bets.filter(inPair);
}

// ---------- Tabs ----------

function tabFromHash() {
  var name = window.location.hash.replace("#", "");
  return TABS.indexOf(name) >= 0 ? name : "overview";
}

// Charts drawn inside a hidden panel measure 0px wide, so they are told to resize when shown.
function resizeCharts() {
  Object.keys(Chart.instances).forEach(function (key) {
    var chart = Chart.instances[key];
    chart.resize();
    chart.update("none");
  });
}

function showTab(name) {
  document.querySelectorAll("[data-panel]").forEach(function (panel) {
    panel.hidden = panel.dataset.panel !== name;
  });
  document.querySelectorAll("[data-tab]").forEach(function (link) {
    link.setAttribute("aria-selected", link.dataset.tab === name ? "true" : "false");
  });
  window.requestAnimationFrame(resizeCharts);
}

function measureHeader() {
  var header = document.querySelector(".topbar");
  document.documentElement.style.setProperty("--header-h", header.offsetHeight + "px");
}

// ---------- Overview ----------

function winLossCounts(bets) {
  var won = bets.filter(function (bet) { return bet.status === "won"; }).length;
  var lost = bets.filter(function (bet) { return bet.status === "lost"; }).length;
  return {won: won, lost: lost, open: bets.length - won - lost};
}

function totalPnl(bets) {
  return bets.reduce(function (sum, bet) {
    return isMissing(bet.pnl) ? sum : sum + bet.pnl;
  }, 0);
}

function renderChip() {
  var pair = currentPair();
  setText("pair-chip", pair.decider + " + " + pair.context);
}

function setSigned(id, value) {
  var el = byId(id);
  animateNumber(id, value, fmtMoney);
  el.classList.remove("pos", "neg");
  if (signClass(value)) {
    el.classList.add(signClass(value));
  }
}

function renderOverview() {
  var bets = pairBets();
  var counts = winLossCounts(bets);
  var settled = counts.won + counts.lost;
  animateNumber("count-markets", state.markets.length, formatCount);
  animateNumber("count-estimates", pairEstimates().length, formatCount);
  animateNumber("count-bets", bets.length, formatCount);
  setSigned("total-pnl", totalPnl(bets));
  if (settled === 0) {
    showPlain("win-rate", "none");
  } else {
    animateNumber("win-rate", counts.won / settled * 100, function (value) { return Math.round(value) + "%"; });
  }
  setText("win-note", settled === 0
    ? "No bet has settled yet."
    : counts.won + " of " + settled + " settled bets made money.");
}

// Lower Brier wins, so the margin is the larger score minus the smaller one.
function renderVerdict(card) {
  var jevBox = document.querySelector(".score-jev");
  var marketBox = document.querySelector(".score-market");
  var note = byId("verdict-note");
  jevBox.classList.remove("winner");
  marketBox.classList.remove("winner");
  byId("beats-badge").hidden = true;
  note.hidden = true;
  if (card === null || isMissing(card.jev_brier) || isMissing(card.market_brier)) {
    setText("verdict-text", "Nothing to score yet for this pair. Press the five pipeline buttons in order.");
    return;
  }
  var margin = fmtBrier(Math.abs(card.market_brier - card.jev_brier));
  if (card.jev_brier < card.market_brier) {
    jevBox.classList.add("winner");
    byId("beats-badge").hidden = false;
    setText("verdict-text", "Jev was closer to the truth than the market, by " + margin + ".");
  } else {
    marketBox.classList.add("winner");
    setText("verdict-text", "The market was closer to the truth than Jev, by " + margin + ".");
  }
  if (currentPair().decider === "stub") {
    note.textContent = "Stub is a placeholder, not a forecaster. A win here shows the pipeline works, not skill.";
    note.hidden = false;
  }
}

function showBrier(id, value) {
  if (isMissing(value)) {
    showPlain(id, "none");
  } else {
    animateNumber(id, value, fmtBrier);
  }
}

function renderScorecard() {
  var card = selectedScorecard();
  renderVerdict(card);
  setText("score-count", card === null ? 0 : card.count);
  showBrier("jev-brier", card === null ? null : card.jev_brier);
  showBrier("market-brier", card === null ? null : card.market_brier);
  fillBuckets("jev-buckets", "jev-buckets-empty", card === null ? [] : card.jev_calibration);
  fillBuckets("market-buckets", "market-buckets-empty", card === null ? [] : card.market_calibration);
}

// ---------- Charts ----------

function chartOptions(extra) {
  var options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: reduceMotion ? false : {duration: 800, easing: "easeOutQuart"}
  };
  return Object.assign(options, extra);
}

function clearChart(canvasId) {
  var old = Chart.getChart(byId(canvasId));
  if (old) {
    old.destroy();
  }
}

// Chart.js keeps one chart per canvas, so the old one goes first or a filter change stacks them.
function drawChart(canvasId, config) {
  clearChart(canvasId);
  return new Chart(byId(canvasId), config);
}

function setChartVisible(boxId, canvasId, visible) {
  byId(boxId).hidden = !visible;
  if (!visible) {
    clearChart(canvasId);
  }
}

function setInsight(id, text) {
  byId(id).textContent = text;
}

function unitAxis(title) {
  return {
    type: "linear",
    min: 0,
    max: 1,
    title: {display: true, text: title},
    ticks: {callback: function (value) { return Math.round(value * 100) + "%"; }}
  };
}

// --- Brier bars ---

// The market Brier should match across pairs, so any non-null one stands in when the selected pair has none.
function marketBrierForChart() {
  var selected = selectedScorecard();
  if (selected !== null && !isMissing(selected.market_brier)) {
    return selected.market_brier;
  }
  for (var i = 0; i < SCORECARD_PAIRS.length; i++) {
    var card = state.scorecards[pairKey(SCORECARD_PAIRS[i].decider, SCORECARD_PAIRS[i].context)];
    if (card && !isMissing(card.market_brier)) {
      return card.market_brier;
    }
  }
  return null;
}

function brierBars() {
  var bars = [];
  var market = marketBrierForChart();
  var pair = currentPair();
  if (!isMissing(market)) {
    bars.push({label: "Market", value: market, color: COLOR.market});
  }
  SCORECARD_PAIRS.forEach(function (candidate) {
    var card = state.scorecards[pairKey(candidate.decider, candidate.context)];
    if (card && !isMissing(card.jev_brier)) {
      var selected = candidate.decider === pair.decider && candidate.context === pair.context;
      bars.push({
        label: candidate.decider + " " + candidate.context,
        value: card.jev_brier,
        color: selected ? COLOR.accent : COLOR.accentDim
      });
    }
  });
  return bars;
}

// Draws each bar's number on top of it, so nobody has to read it off the axis.
var valueLabels = {
  id: "valueLabels",
  afterDatasetsDraw: function (chart) {
    var ctx = chart.ctx;
    ctx.save();
    ctx.fillStyle = COLOR.ink;
    ctx.font = "600 13px " + Chart.defaults.font.family;
    ctx.textAlign = "center";
    chart.getDatasetMeta(0).data.forEach(function (bar, index) {
      ctx.fillText(fmtBrier(chart.data.datasets[0].data[index]), bar.x, bar.y - 8);
    });
    ctx.restore();
  }
};

var BASELINE_BRIER = 0.25;

function renderBrierInsight(bars) {
  if (bars.length === 0) {
    setInsight("brier-insight", "");
    return;
  }
  var best = bars.reduce(function (low, bar) { return bar.value < low.value ? bar : low; });
  setInsight("brier-insight", "Right now: the lowest bar is " + best.label + " at " + fmtBrier(best.value) + ".");
}

function drawBrierChart() {
  var bars = brierBars();
  var hasBars = bars.length > 0;
  byId("brier-empty").hidden = hasBars;
  setChartVisible("brier-box", "brier-chart", hasBars);
  renderBrierInsight(bars);
  if (!hasBars) {
    return;
  }
  drawChart("brier-chart", {
    type: "bar",
    plugins: [valueLabels],
    data: {
      labels: bars.map(function (bar) { return bar.label; }),
      datasets: [{
        label: "Brier score",
        data: bars.map(function (bar) { return bar.value; }),
        backgroundColor: bars.map(function (bar) { return bar.color; }),
        borderRadius: 6,
        maxBarThickness: 90,
        order: 2
      }, {
        type: "line",
        label: "Always guessing 50% scores 0.25",
        data: bars.map(function () { return BASELINE_BRIER; }),
        borderColor: COLOR.neg,
        borderDash: [8, 5],
        borderWidth: 2,
        pointStyle: "line",
        pointRadius: 0,
        order: 1
      }]
    },
    options: chartOptions({
      layout: {padding: {top: 20}},
      plugins: {
        legend: {
          display: true,
          labels: {filter: function (item) { return item.datasetIndex === 1; }}
        },
        tooltip: {
          filter: function (item) { return item.datasetIndex === 0; },
          callbacks: {
            label: function (context) {
              return "Brier " + fmtBrier(context.parsed.y) + ". Lower is better.";
            }
          }
        }
      },
      scales: {
        x: {title: {display: true, text: "Who made the forecast"}},
        y: {beginAtZero: true, suggestedMax: 0.3, title: {display: true, text: "Brier score (lower is better)"}}
      }
    })
  });
}

// --- Calibration ---

function calibrationPoints(buckets) {
  return buckets
    .filter(function (bucket) {
      return bucket.count > 0 && !isMissing(bucket.avg_pred) && !isMissing(bucket.actual_rate);
    })
    .map(function (bucket) {
      return {x: bucket.avg_pred, y: bucket.actual_rate, count: bucket.count, range: bucket.range};
    });
}

// Square root so 4x the estimates looks 2x as wide. The cap keeps a big bucket on the chart.
function bucketRadius(count) {
  return Math.min(6 + Math.sqrt(count) * 3, 20);
}

function renderCalibrationInsight(points) {
  if (points.length === 0) {
    setInsight("calibration-insight", "");
    return;
  }
  // Weighting by count stops a single lucky or unlucky estimate from being called the biggest miss.
  var worst = points.reduce(function (far, point) {
    return Math.abs(point.x - point.y) * point.count > Math.abs(far.x - far.y) * far.count ? point : far;
  });
  setInsight("calibration-insight", "Right now: the group that misses most overall is " + worst.range +
    " (" + plural(worst.count, "estimate") + "). Jev said about " + fmtProb(worst.x) +
    " and YES happened " + fmtProb(worst.y) + " of the time.");
}

function drawCalibration() {
  var card = selectedScorecard();
  var points = card === null ? [] : calibrationPoints(card.jev_calibration);
  setChartVisible("calibration-box", "calibration-chart", points.length > 0);
  byId("calibration-empty").hidden = points.length > 0;
  renderCalibrationInsight(points);
  if (points.length === 0) {
    return;
  }
  var radii = points.map(function (point) { return bucketRadius(point.count); });
  drawChart("calibration-chart", {
    type: "scatter",
    data: {
      datasets: [
        {
          label: "Jev (bigger dot = more estimates)",
          data: points,
          backgroundColor: COLOR.accent,
          pointRadius: radii,
          pointHoverRadius: radii,
          clip: false
        },
        {
          label: "Perfect calibration",
          data: [{x: 0, y: 0}, {x: 1, y: 1}],
          showLine: true,
          borderColor: COLOR.muted,
          borderDash: [6, 4],
          pointStyle: "line",
          pointRadius: 0,
          pointHoverRadius: 0
        }
      ]
    },
    options: chartOptions({
      layout: {padding: 14},
      plugins: {
        tooltip: {
          filter: function (item) { return item.datasetIndex === 0; },
          callbacks: {
            label: function (context) {
              var point = context.raw;
              return point.range + ": said " + fmtProb(point.x) + ", happened " + fmtProb(point.y) +
                ", " + plural(point.count, "estimate");
            }
          }
        }
      },
      scales: {
        x: unitAxis("What Jev said (average chance of YES)"),
        y: unitAxis("What happened (share that resolved YES)")
      }
    })
  });
}

function fillBuckets(bodyId, emptyId, buckets) {
  var body = byId(bodyId);
  clearBody(bodyId);
  byId(emptyId).hidden = buckets.length > 0;
  buckets.forEach(function (bucket) {
    var tr = document.createElement("tr");
    tr.appendChild(makeEl("td", "", bucket.range));
    tr.appendChild(makeEl("td", "num", bucket.count));
    tr.appendChild(makeEl("td", "num", fmtProb(bucket.avg_pred)));
    tr.appendChild(makeEl("td", "num", fmtProb(bucket.actual_rate)));
    body.appendChild(tr);
  });
}

// --- Equity curve (drawn in the Charts tab and again in the Portfolio tab) ---

function compareText(left, right) {
  return String(left || "").localeCompare(String(right || ""));
}

// settled_at is an ISO timestamp, so text order is time order.
function settledBets(bets) {
  return bets
    .filter(function (bet) { return !isMissing(bet.pnl); })
    .sort(function (a, b) { return compareText(a.settled_at, b.settled_at); });
}

function runningTotals(bets) {
  var total = 0;
  return bets.map(function (bet) {
    total += bet.pnl;
    return total;
  });
}

function pnlColor(pnl) {
  if (pnl > 0) {
    return COLOR.pos;
  }
  return pnl < 0 ? COLOR.neg : COLOR.muted;
}

function equityInsight(settled, totals) {
  var won = settled.filter(function (bet) { return bet.pnl > 0; }).length;
  return "Right now: " + won + " of " + settled.length + " bets won. Ended at " +
    fmtMoney(totals[totals.length - 1]) + ", with a high of " + fmtMoney(Math.max.apply(null, totals)) +
    " and a low of " + fmtMoney(Math.min.apply(null, totals)) + ".";
}

function drawEquity(ids) {
  var settled = settledBets(pairBets());
  var hasBets = settled.length > 0;
  byId(ids.empty).hidden = hasBets;
  setChartVisible(ids.box, ids.canvas, hasBets);
  if (!hasBets) {
    if (ids.insight) {
      setInsight(ids.insight, "");
    }
    return;
  }
  var totals = runningTotals(settled);
  if (ids.insight) {
    setInsight(ids.insight, equityInsight(settled, totals));
  }
  // Point 0 is the starting balance, so the first bet's result is a visible step.
  var colors = [COLOR.muted].concat(settled.map(function (bet) { return pnlColor(bet.pnl); }));
  drawChart(ids.canvas, {
    type: "line",
    data: {
      labels: ["Start"].concat(settled.map(function (bet, index) { return String(index + 1); })),
      datasets: [{
        label: "Running P&L",
        data: [0].concat(totals),
        borderColor: COLOR.accent,
        borderWidth: 3,
        fill: {target: "origin", above: "rgba(52, 211, 153, 0.10)", below: "rgba(248, 113, 113, 0.14)"},
        tension: 0.15,
        pointBackgroundColor: colors,
        pointBorderColor: colors,
        pointRadius: 6,
        pointHoverRadius: 9
      }]
    },
    options: chartOptions({
      plugins: {
        legend: {display: true},
        tooltip: {
          callbacks: {
            title: function (items) {
              return items[0].dataIndex === 0 ? "Start" : "Bet " + items[0].label + " of " + settled.length;
            },
            label: function (context) {
              if (context.dataIndex === 0) {
                return "Balance 0.00";
              }
              var bet = settled[context.dataIndex - 1];
              return [
                shorten(questionForBet(bet), 70),
                bet.side + " bet " + (bet.pnl > 0 ? "won " : "lost ") + fmtAmount(Math.abs(bet.pnl)),
                "Running total " + fmtMoney(context.parsed.y)
              ];
            }
          }
        }
      },
      scales: {
        x: {title: {display: true, text: "Bet number, in the order they settled"}},
        y: {title: {display: true, text: "Running profit / loss (paper $)"}}
      }
    })
  });
}

function drawEquityCharts() {
  drawEquity({box: "equity-box", canvas: "equity-chart", empty: "equity-empty", insight: "equity-insight"});
  drawEquity({box: "pf-equity-box", canvas: "pf-equity-chart", empty: "pf-equity-empty", insight: null});
}

// --- Edge map ---

var OUTCOME_GROUPS = [
  {label: "Resolved YES", outcome: 1, color: COLOR.pos},
  {label: "Resolved NO", outcome: 0, color: COLOR.neg},
  {label: "Not resolved", outcome: null, color: COLOR.muted}
];

function outcomeOf(row) {
  if (row.market === null || isMissing(row.market.outcome)) {
    return null;
  }
  return row.market.outcome;
}

function renderEdgeInsight(rows) {
  if (rows.length === 0) {
    setInsight("edge-insight", "");
    return;
  }
  var above = rows.filter(function (row) { return row.edge > 0; }).length;
  var below = rows.filter(function (row) { return row.edge < 0; }).length;
  var bigGap = rows.filter(function (row) { return Math.abs(row.edge) >= 0.08; }).length;
  setInsight("edge-insight", "Right now: of " + plural(rows.length, "estimate") + ", Jev was above the market on " +
    above + ", below on " + below + ", and " + bigGap + " differ by 8 points or more.");
}

function drawEdgeScatter() {
  var rows = joinedRows();
  setChartVisible("edge-box", "edge-chart", rows.length > 0);
  byId("edge-empty").hidden = rows.length > 0;
  renderEdgeInsight(rows);
  if (rows.length === 0) {
    return;
  }
  var datasets = OUTCOME_GROUPS.map(function (group) {
    return {
      label: group.label,
      backgroundColor: group.color,
      borderColor: group.color,
      pointRadius: 6,
      pointHoverRadius: 9,
      data: rows
        .filter(function (row) { return outcomeOf(row) === group.outcome; })
        .map(function (row) {
          return {x: row.estimate.market_price, y: row.estimate.jev_prob, question: row.estimate.question};
        })
    };
  });
  datasets.push({
    label: "Jev agrees with the market",
    data: [{x: 0, y: 0}, {x: 1, y: 1}],
    showLine: true,
    borderColor: COLOR.muted,
    borderDash: [6, 4],
    borderWidth: 2,
    pointStyle: "line",
    pointRadius: 0,
    pointHoverRadius: 0
  });
  drawChart("edge-chart", {
    type: "scatter",
    data: {datasets: datasets},
    options: chartOptions({
      plugins: {
        tooltip: {
          filter: function (item) { return item.datasetIndex < OUTCOME_GROUPS.length; },
          callbacks: {
            label: function (context) {
              var point = context.raw;
              return shorten(point.question, 60) + ": market " + fmtProb(point.x) + ", Jev " + fmtProb(point.y);
            }
          }
        }
      },
      scales: {
        x: unitAxis("Market's chance of YES"),
        y: unitAxis("Jev's chance of YES")
      }
    })
  });
}

// ---------- Markets ----------

// One row per estimate of the active pair, joined to its market and its bet.
function joinedRows() {
  var marketById = new Map();
  state.markets.forEach(function (market) {
    marketById.set(market.id, market);
  });
  var betByEstimate = new Map();
  pairBets().forEach(function (bet) {
    if (!betByEstimate.has(bet.estimate_id)) {
      betByEstimate.set(bet.estimate_id, bet);
    }
  });
  return pairEstimates().map(function (estimate) {
    return {
      estimate: estimate,
      market: marketById.get(estimate.market_id) || null,
      bet: betByEstimate.get(estimate.estimate_id) || null,
      edge: estimate.jev_prob - estimate.market_price
    };
  });
}

function categoryOf(row) {
  return row.market ? row.market.category : null;
}

function makeOption(value, text) {
  var option = makeEl("option", "", text);
  option.value = value;
  return option;
}

// Options are rebuilt from fresh data, but the reader's current pick is kept if it still exists.
function fillCategoryOptions() {
  var select = byId("filter-category");
  var current = select.value;
  var seen = new Set();
  joinedRows().forEach(function (row) {
    if (!isMissing(categoryOf(row))) {
      seen.add(String(categoryOf(row)));
    }
  });
  var values = Array.from(seen).sort();
  select.replaceChildren(makeOption("", "All"));
  values.forEach(function (value) {
    select.appendChild(makeOption(value, value));
  });
  select.value = values.indexOf(current) >= 0 ? current : "";
  select.disabled = values.length === 0;
  select.title = values.length === 0 ? "No market in this data has a category." : "";
}

function outcomeKey(row) {
  var outcome = outcomeOf(row);
  if (outcome === 1) {
    return "yes";
  }
  return outcome === 0 ? "no" : "open";
}

function filterRows(rows) {
  var query = byId("market-search").value.trim().toLowerCase();
  var category = byId("filter-category").value;
  var outcome = byId("filter-outcome").value;
  return rows.filter(function (row) {
    if (query && String(row.estimate.question).toLowerCase().indexOf(query) < 0) {
      return false;
    }
    if (category && String(categoryOf(row)) !== category) {
      return false;
    }
    return outcome === "" || outcomeKey(row) === outcome;
  });
}

var SORTS = {
  edge: function (a, b) { return Math.abs(b.edge) - Math.abs(a.edge); },
  price: function (a, b) { return b.estimate.market_price - a.estimate.market_price; },
  name: function (a, b) { return compareText(a.estimate.question, b.estimate.question); }
};

function sortRows(rows) {
  return rows.slice().sort(SORTS[byId("sort-by").value]);
}

// A bad price outside 0..1 must not push a marker or bar out of its track.
function clampPercent(value) {
  if (isMissing(value)) {
    return 0;
  }
  return Math.min(100, Math.max(0, value * 100));
}

function marker(className, at, title) {
  var dot = makeEl("span", className);
  dot.style.left = at + "%";
  dot.title = title;
  return dot;
}

// The shaded strip between the two markers is the gap, so its width is the edge.
function gapTrack(market, jev) {
  var marketAt = clampPercent(market);
  var jevAt = clampPercent(jev);
  var track = makeEl("div", "track");
  var gap = makeEl("div", "track-gap " + signClass(jev - market));
  gap.style.left = Math.min(marketAt, jevAt) + "%";
  gap.style.width = Math.abs(jevAt - marketAt) + "%";
  track.appendChild(gap);
  track.appendChild(marker("marker marker-market", marketAt, "Market " + fmtProb(market)));
  track.appendChild(marker("marker marker-jev", jevAt, "Jev " + fmtProb(jev)));
  return track;
}

function pill(text, kind) {
  return makeEl("span", "pill pill-" + kind, text);
}

function outcomeBadge(outcome) {
  if (outcome === 1) {
    return pill("YES", "yes");
  }
  return outcome === 0 ? pill("NO", "no") : null;
}

// Cards fade in one after another, but only when the pair changes or data reloads.
// Typing in the search box must not replay it on every keystroke.
var staggerNext = false;

function marketCard(row, index) {
  var estimate = row.estimate;
  var card = makeEl("article", "market-card");
  if (staggerNext) {
    card.classList.add("enter");
    card.style.setProperty("--i", Math.min(index, 14));
  }
  card.tabIndex = 0;
  var top = makeEl("div", "card-top");
  if (categoryOf(row)) {
    top.appendChild(makeEl("span", "tag-cat", categoryOf(row)));
  }
  top.appendChild(makeEl("span", "tag-pair", estimate.decider + " · " + estimate.context_level));
  var badge = outcomeBadge(outcomeOf(row));
  if (badge) {
    badge.classList.add("push");
    top.appendChild(badge);
  }
  card.appendChild(top);
  var question = makeEl("p", "question clamp", estimate.question);
  question.title = estimate.question;
  card.appendChild(question);
  card.appendChild(gapTrack(estimate.market_price, estimate.jev_prob));
  var labels = makeEl("div", "track-labels");
  labels.appendChild(makeEl("span", "", "Market " + fmtProb(estimate.market_price)));
  labels.appendChild(makeEl("span", "", "Jev " + fmtProb(estimate.jev_prob)));
  card.appendChild(labels);
  var meta = makeEl("div", "card-meta");
  meta.appendChild(makeEl("span", "edge " + signClass(row.edge), "Edge " + fmtEdge(row.edge)));
  card.appendChild(meta);
  card.appendChild(makeEl("p", "fineprint",
    "confidence " + fmtPrice(estimate.confidence) + ", info " + fmtPrice(estimate.info_score)));
  card.addEventListener("click", function () {
    openDetail(row);
  });
  card.addEventListener("keydown", function (event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openDetail(row);
    }
  });
  return card;
}

function renderMarkets() {
  var all = joinedRows();
  var rows = sortRows(filterRows(all));
  clearBody("markets-body");
  var empty = byId("markets-empty");
  empty.hidden = rows.length > 0;
  empty.textContent = all.length === 0
    ? "No estimates for this pair yet. Run steps 1 to 3."
    : "No markets match these filters.";
  setText("markets-showing", "Showing " + rows.length + " of " + all.length);
  var body = byId("markets-body");
  rows.forEach(function (row, index) {
    body.appendChild(marketCard(row, index));
  });
  staggerNext = false;
}

function addFact(list, label, value, className) {
  list.appendChild(makeEl("dt", "", label));
  list.appendChild(makeEl("dd", className || "", value));
}

function openDetail(row) {
  var estimate = row.estimate;
  setText("detail-question", estimate.question);
  setText("detail-rules", row.market && row.market.rules ? row.market.rules : "No rules on file.");
  var facts = byId("detail-facts");
  facts.replaceChildren();
  addFact(facts, "Pair", estimate.decider + " + " + estimate.context_level);
  addFact(facts, "Market chance", fmtProb(estimate.market_price));
  addFact(facts, "Jev chance", fmtProb(estimate.jev_prob));
  addFact(facts, "Edge", fmtEdge(row.edge), signClass(row.edge));
  addFact(facts, "Confidence", fmtPrice(estimate.confidence));
  addFact(facts, "Info score", fmtPrice(estimate.info_score));
  if (row.bet === null) {
    addFact(facts, "Bet", "No bet on this estimate.");
  } else {
    addFact(facts, "Side", row.bet.side);
    addFact(facts, "Entry price", fmtPrice(row.bet.entry_price));
    addFact(facts, "Stake", fmtAmount(row.bet.stake));
    addFact(facts, "Status", row.bet.status);
    addFact(facts, "P&L", fmtMoney(row.bet.pnl), signClass(row.bet.pnl));
  }
  byId("detail").showModal();
  loadHeadlines(row);
}

// ---------- Headlines Jev could read (GET /markets/{id}/news) ----------

var headlineRequest = 0;

function headlineNote(body, row) {
  var count = body.items.length;
  if (count === 0) {
    return "No headlines saved for this market. Run step 2, Fetch news.";
  }
  var before = body.items.every(function (item) { return item.published_at < body.cutoff; });
  var guard = before
    ? "All published before the price was taken (" + body.cutoff.slice(0, 10) + "). Nothing from the future."
    : "Warning: some headlines are newer than the price date.";
  var used = row.estimate.context_level === "news"
    ? "This estimate used them."
    : "This estimate was basic context, so Jev was not shown them.";
  return plural(count, "headline") + " saved. " + guard + " " + used;
}

function headlineItem(item) {
  var li = makeEl("li", "headline");
  li.appendChild(makeEl("span", "headline-date", item.published_at.slice(0, 10)));
  li.appendChild(makeEl("span", "headline-title", item.title));
  if (item.description) {
    li.appendChild(makeEl("span", "headline-desc", shorten(item.description, 160)));
  }
  return li;
}

// A newer click bumps headlineRequest, so a slow older reply cannot overwrite the dialog.
async function loadHeadlines(row) {
  var request = ++headlineRequest;
  var list = byId("detail-news");
  list.replaceChildren();
  setText("detail-news-note", "Loading headlines...");
  try {
    var body = await getJson("/markets/" + encodeURIComponent(row.estimate.market_id) + "/news");
    if (request !== headlineRequest) {
      return;
    }
    setText("detail-news-note", headlineNote(body, row));
    body.items.forEach(function (item) {
      list.appendChild(headlineItem(item));
    });
  } catch (error) {
    if (request === headlineRequest) {
      setText("detail-news-note", "Could not load headlines.");
    }
  }
}

// ---------- Portfolio ----------

function questionForBet(bet) {
  var match = null;
  state.estimates.forEach(function (estimate) {
    if (estimate.estimate_id === bet.estimate_id) {
      match = estimate.question;
    }
  });
  if (match) {
    return match;
  }
  state.markets.forEach(function (market) {
    if (market.id === bet.market_id && match === null) {
      match = market.question;
    }
  });
  return match || bet.market_id;
}

function betMatches(bet, query) {
  if (query === "") {
    return true;
  }
  var haystack = (questionForBet(bet) + " " + bet.side + " " + bet.status).toLowerCase();
  return haystack.indexOf(query) >= 0;
}

function renderPortfolioSummary(bets) {
  var counts = winLossCounts(bets);
  animateNumber("pf-bets", bets.length, formatCount);
  animateNumber("pf-won", counts.won, formatCount);
  animateNumber("pf-lost", counts.lost, formatCount);
  animateNumber("pf-open", counts.open, formatCount);
  setSigned("pf-pnl", totalPnl(bets));
}

function betRow(bet) {
  var tr = document.createElement("tr");
  var question = questionForBet(bet);
  var q = makeEl("td", "q", question);
  q.title = question;
  tr.appendChild(q);
  tr.appendChild(makeEl("td", "", bet.decider));
  tr.appendChild(makeEl("td", "", bet.context_level));
  var sideCell = document.createElement("td");
  sideCell.appendChild(pill(bet.side, bet.side === "YES" ? "yes" : "no"));
  tr.appendChild(sideCell);
  var entry = makeEl("td", "num", fmtPrice(bet.entry_price));
  entry.title = "Exact chance paid: " + fmtProb(bet.entry_price);
  tr.appendChild(entry);
  tr.appendChild(makeEl("td", "num", fmtAmount(bet.stake)));
  var statusCell = document.createElement("td");
  var done = bet.status === "won" || bet.status === "lost";
  statusCell.appendChild(pill(bet.status, done ? bet.status : "open"));
  tr.appendChild(statusCell);
  tr.appendChild(makeEl("td", "num pnl " + signClass(bet.pnl), isMissing(bet.pnl) ? "" : fmtMoney(bet.pnl)));
  return tr;
}

function renderPortfolio() {
  var bets = pairBets();
  renderPortfolioSummary(bets);
  clearBody("bets-body");
  var query = byId("bet-search").value.trim().toLowerCase();
  var shown = bets.filter(function (bet) { return betMatches(bet, query); });
  var empty = byId("bets-empty");
  empty.hidden = shown.length > 0;
  empty.textContent = bets.length === 0
    ? "No bets for this pair yet. Run steps 1 to 4."
    : "No bets match this search.";
  setText("bets-showing", "Showing " + shown.length + " of " + bets.length);
  var body = byId("bets-body");
  shown.forEach(function (bet) {
    body.appendChild(betRow(bet));
  });
}

// ---------- Render everything for the active pair ----------

function renderAll() {
  staggerNext = true;
  renderChip();
  renderOverview();
  renderScorecard();
  drawBrierChart();
  drawCalibration();
  drawEquityCharts();
  drawEdgeScatter();
  fillCategoryOptions();
  renderMarkets();
  renderPortfolio();
}

// ---------- Pipeline buttons ----------

var PIPELINE_IDS = ["sync", "fetch-news", "run-estimates", "auto-bet", "settle"];

var PIPELINE_ROUTES = {
  "sync": "/markets/sync",
  "fetch-news": "/news/fetch",
  "auto-bet": "/pipeline/auto-bet",
  "settle": "/pipeline/settle"
};

function hasCounts(body) {
  if (body === null || typeof body !== "object") {
    return false;
  }
  return "processed" in body && "skipped" in body && "failed" in body;
}

// Batch routes return the failed markets as a list, so the sentence shows how many.
function failedCount(failed) {
  return Array.isArray(failed) ? failed.length : failed;
}

function describeResult(body) {
  if (!hasCounts(body)) {
    return JSON.stringify(body);
  }
  return "Processed " + body.processed + ", skipped " + body.skipped +
    ", failed " + failedCount(body.failed) + ".";
}

function setPipelineBusy(busy, activeId) {
  PIPELINE_IDS.forEach(function (id) {
    var button = byId(id);
    button.disabled = busy;
    button.classList.toggle("working", busy && id === activeId);
  });
}

function runFailureText(error) {
  if (error.status === 401) {
    return "Wrong or missing admin token. Open \"Admin token\" under the pipeline buttons and enter the token the server was started with.";
  }
  return error.message;
}

// Every button is disabled while one request runs, so a double click cannot send it twice.
async function runButton(id, path) {
  setPipelineBusy(true, id);
  try {
    var body = await getJson(path, {method: "POST", headers: adminHeaders()});
    var text = describeResult(body);
    showStatus(text);
    toast(text, "ok");
    await refresh();
  } catch (error) {
    var message = runFailureText(error);
    showStatus(message);
    toast(message, "error");
  } finally {
    setPipelineBusy(false, id);
  }
}

PIPELINE_IDS.forEach(function (id) {
  byId(id).addEventListener("click", function () {
    if (id === "run-estimates") {
      runButton(id, "/estimates/run?context=" + encodeURIComponent(byId("context").value));
    } else {
      runButton(id, PIPELINE_ROUTES[id]);
    }
  });
});

// ---------- Wiring ----------

// All four scorecards are already loaded, so changing the pair only redraws.
byId("decider").addEventListener("change", renderAll);
byId("context").addEventListener("change", renderAll);

["filter-category", "filter-outcome", "sort-by"].forEach(function (id) {
  byId(id).addEventListener("change", renderMarkets);
});
byId("market-search").addEventListener("input", renderMarkets);
byId("bet-search").addEventListener("input", renderPortfolio);

window.addEventListener("hashchange", function () {
  showTab(tabFromHash());
});
window.addEventListener("resize", measureHeader);

// A click on the dark backdrop lands on the dialog itself, not on its content.
byId("detail").addEventListener("click", function (event) {
  if (event.target === event.currentTarget) {
    event.currentTarget.close();
  }
});

// Numbers show a shimmer until the first data arrives.
document.body.classList.add("loading");
measureHeader();
showTab(tabFromHash());
refresh()
  .then(loadFooter)
  .catch(reportError);
