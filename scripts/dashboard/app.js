/* E-commerce dashboard logic. Data is embedded by scripts/05_build_dashboard.py
   as window.__DATA__ (columnar arrays, money in cents). */
(() => {
  const D = window.__DATA__;
  const { fmt } = Dash;
  const O = D.orders, I = D.items, N = O.m.length, M = I.o.length;
  const VALID = D.statuses.map(s => s !== "canceled" && s !== "unavailable");
  const monthLabel = ym => { const [y, m] = ym.split("-"); return new Date(+y, +m - 1, 1).toLocaleString("en-US", { month: "short", year: "numeric" }); };
  const monthShort = ym => { const [y, m] = ym.split("-"); return new Date(+y, +m - 1, 1).toLocaleString("en-US", { month: "short" }) + " " + y.slice(2); };
  const R = v => fmt.moneyCompact(v);
  const BUCKETS = ["On time or early", "1-3 days late", "4-7 days late", "8+ days late"];
  const bucketOf = d => d <= 0 ? 0 : d <= 3 ? 1 : d <= 7 ? 2 : 3;

  const F = { from: 0, to: D.months.length - 1, region: -1, state: -1, cat: -1 };

  /* ---------- filters ---------- */
  const $ = id => document.getElementById(id);
  const selFrom = $("f-from"), selTo = $("f-to"), selRegion = $("f-region"), selState = $("f-state"), selCat = $("f-cat");
  Dash.fillSelect(selFrom, D.months.map((m, i) => [i, monthLabel(m)]));
  Dash.fillSelect(selTo, D.months.map((m, i) => [i, monthLabel(m)]));
  Dash.fillSelect(selRegion, D.regions.map((r, i) => [i, r]).sort((a, b) => a[1].localeCompare(b[1])), "All regions");
  Dash.fillSelect(selCat, D.categories.map((c, i) => [i, c]).sort((a, b) => a[1].localeCompare(b[1])), "All categories");
  function fillStates() {
    const opts = D.states.map((s, i) => [i, s]).filter(([i]) => F.region < 0 || D.stateRegion[i] === F.region)
      .sort((a, b) => a[1].localeCompare(b[1]));
    Dash.fillSelect(selState, opts, "All states");
    selState.value = F.state < 0 ? "" : String(F.state);
  }
  function syncControls() {
    selFrom.value = F.from; selTo.value = F.to;
    selRegion.value = F.region < 0 ? "" : String(F.region);
    fillStates();
    selCat.value = F.cat < 0 ? "" : String(F.cat);
    const parts = [];
    if (F.from > 0 || F.to < D.months.length - 1) parts.push(`${monthLabel(D.months[F.from])} - ${monthLabel(D.months[F.to])}`);
    if (F.region >= 0) parts.push(D.regions[F.region]);
    if (F.state >= 0) parts.push(D.states[F.state]);
    if (F.cat >= 0) parts.push(D.categories[F.cat]);
    $("active-note").textContent = parts.length ? "Filtered: " + parts.join(" · ") : "Showing all data (Jan 2017 - Aug 2018)";
  }
  const num = v => (v === "" ? -1 : +v);
  selFrom.onchange = () => { F.from = +selFrom.value; if (F.from > F.to) F.to = F.from; update(); };
  selTo.onchange = () => { F.to = +selTo.value; if (F.to < F.from) F.from = F.to; update(); };
  selRegion.onchange = () => { F.region = num(selRegion.value); if (F.state >= 0 && D.stateRegion[F.state] !== F.region) F.state = -1; update(); };
  selState.onchange = () => { F.state = num(selState.value); if (F.state >= 0) F.region = D.stateRegion[F.state]; update(); };
  selCat.onchange = () => { F.cat = num(selCat.value); update(); };
  $("f-reset").onclick = () => { Object.assign(F, { from: 0, to: D.months.length - 1, region: -1, state: -1, cat: -1 }); update(); };

  /* ---------- masks ---------- */
  function buildMask({ ignoreState = false, ignoreRegion = false, ignoreCat = false } = {}) {
    const mask = new Uint8Array(N);
    for (let k = 0; k < N; k++) {
      const m = O.m[k];
      if (m < F.from || m > F.to) continue;
      const s = O.s[k];
      if (!ignoreRegion && F.region >= 0 && D.stateRegion[s] !== F.region) continue;
      if (!ignoreState && F.state >= 0 && s !== F.state) continue;
      mask[k] = 1;
    }
    if (ignoreCat || F.cat < 0) return mask;
    const withCat = new Uint8Array(N);
    for (let j = 0; j < M; j++) if (I.c[j] === F.cat && mask[I.o[j]]) withCat[I.o[j]] = 1;
    return withCat;
  }
  function orderRevenue() {
    if (F.cat < 0) return O.rev;
    const rev = new Float64Array(N);
    for (let j = 0; j < M; j++) if (I.c[j] === F.cat) rev[I.o[j]] += I.p[j];
    return rev;
  }

  /* ---------- cards ---------- */
  const grid = $("grid");
  const cMonthly = Dash.card(grid, { title: "Monthly revenue", subtitle: "Item revenue by purchase month, valid sales", wide: true });
  const cCats = Dash.card(grid, { title: "Top 10 categories by revenue", subtitle: "Click a bar to filter the page" });
  const cStates = Dash.card(grid, { title: "Top 10 states by revenue", subtitle: "Customer state. Click a bar to filter" });
  const cReview = Dash.card(grid, { title: "Review score by delivery timeliness", subtitle: "Delivered orders with a review" });
  const cLate = Dash.card(grid, { title: "Late delivery rate by state", subtitle: "Highest 10 states with 50+ delivered orders" });
  const cRegion = Dash.card(grid, { title: "Revenue by region", subtitle: "Brazilian macro-regions. Click a bar to filter" });
  const cStatus = Dash.card(grid, { title: "Order status", subtitle: "All orders in the selection, including canceled" });

  function update() {
    syncControls();
    const mask = buildMask();
    const rev = orderRevenue();

    // KPIs
    let revenue = 0, orders = 0, revSum = 0, revCnt = 0, late = 0, lateCnt = 0, days = 0, dayCnt = 0;
    const custSet = new Set();
    for (let k = 0; k < N; k++) {
      if (!mask[k] || !VALID[O.st[k]] || O.n[k] === 0) continue;
      revenue += rev[k]; orders++; custSet.add(O.cu[k]);
      if (O.rv[k] >= 0) { revSum += O.rv[k]; revCnt++; }
      if (O.lt[k] >= 0) { late += O.lt[k]; lateCnt++; }
      if (O.dd[k] >= 0) { days += O.dd[k]; dayCnt++; }
    }
    revenue /= 100;
    Dash.tiles($("kpis"), [
      { label: "Revenue", value: R(revenue), sub: fmt.money(revenue), hero: true },
      { label: "Orders", value: fmt.int(orders), sub: fmt.int(custSet.size) + " customers" },
      { label: "Average order value", value: orders ? fmt.money(revenue / orders) : "-", sub: "Revenue / distinct orders" },
      { label: "Average review score", value: revCnt ? fmt.dec(revSum / revCnt / 100) + " / 5" : "-", sub: fmt.int(revCnt) + " reviewed orders" },
      { label: "Delivered late", value: lateCnt ? fmt.pct(100 * late / lateCnt) : "-", sub: dayCnt ? `Avg delivery ${fmt.dec(days / dayCnt, 1)} days` : "" },
    ]);

    // Monthly revenue
    const mRev = new Float64Array(D.months.length), mOrd = new Uint32Array(D.months.length);
    for (let k = 0; k < N; k++) if (mask[k] && VALID[O.st[k]] && O.n[k] > 0) { mRev[O.m[k]] += rev[k]; mOrd[O.m[k]]++; }
    const monthRows = [];
    for (let i = F.from; i <= F.to; i++) {
      const v = mRev[i] / 100;
      monthRows.push({ label: monthLabel(D.months[i]), short: monthShort(D.months[i]), value: v, orders: mOrd[i],
        tip: [["Revenue", fmt.money(v)], ["Orders", fmt.int(mOrd[i])], ["AOV", mOrd[i] ? fmt.money(v / mOrd[i]) : "-"]] });
    }
    cMonthly.render(Dash.line, { rows: monthRows, format: R, markPeak: true, aria: "Monthly revenue line chart" }, {
      columns: [{ key: "label", label: "Month" }, { key: "value", label: "Revenue", num: true, fmt: v => fmt.money(v) },
                { key: "orders", label: "Orders", num: true, fmt: fmt.int }],
      rows: monthRows,
    });

    // Categories (ignores the category filter so all categories stay visible; selected one is highlighted)
    const mNoCat = buildMask({ ignoreCat: true });
    const cRev = new Float64Array(D.categories.length), cOrd = new Map();
    const cOrders = D.categories.map(() => new Set());
    for (let j = 0; j < M; j++) {
      const o = I.o[j];
      if (!mNoCat[o] || !VALID[O.st[o]]) continue;
      cRev[I.c[j]] += I.p[j]; cOrders[I.c[j]].add(o);
    }
    const catRowsAll = D.categories.map((c, i) => ({ key: i, label: c, value: cRev[i] / 100, orders: cOrders[i].size }))
      .filter(r => r.value > 0).sort((a, b) => b.value - a.value);
    const catTotal = catRowsAll.reduce((a, r) => a + r.value, 0);
    catRowsAll.forEach(r => { r.share = 100 * r.value / catTotal; r.aov = r.value / r.orders;
      r.tip = [["Revenue", fmt.money(r.value)], ["Orders", fmt.int(r.orders)], ["Category AOV", fmt.money(r.aov)], ["Share", fmt.pct(r.share)]]; });
    let catRows = catRowsAll.slice(0, 10);
    if (F.cat >= 0 && !catRows.some(r => r.key === F.cat)) { const s = catRowsAll.find(r => r.key === F.cat); if (s) catRows = [...catRows.slice(0, 9), s]; }
    cCats.render(Dash.hbar, { rows: catRows, format: R, selected: F.cat >= 0 ? F.cat : null, labelWidth: 170,
      onClick: k => { F.cat = F.cat === k ? -1 : k; update(); } }, {
      columns: [{ key: "label", label: "Category" }, { key: "value", label: "Revenue", num: true, fmt: v => fmt.money(v) },
                { key: "orders", label: "Orders", num: true, fmt: fmt.int }, { key: "aov", label: "AOV", num: true, fmt: v => fmt.money(v) },
                { key: "share", label: "Share", num: true, fmt: v => fmt.pct(v) }],
      rows: catRowsAll,
    });

    // States (ignores the state filter, highlights the selected state)
    const mNoState = buildMask({ ignoreState: true });
    const sRev = new Float64Array(D.states.length), sOrd = new Uint32Array(D.states.length);
    const sDel = new Uint32Array(D.states.length), sLate = new Uint32Array(D.states.length);
    for (let k = 0; k < N; k++) {
      if (!mNoState[k]) continue;
      const s = O.s[k];
      if (VALID[O.st[k]] && O.n[k] > 0) { sRev[s] += rev[k]; sOrd[s]++; }
      if (O.lt[k] >= 0) { sDel[s]++; sLate[s] += O.lt[k]; }
    }
    const stRowsAll = D.states.map((s, i) => ({ key: i, label: s, region: D.regions[D.stateRegion[i]], value: sRev[i] / 100, orders: sOrd[i] }))
      .filter(r => r.value > 0).sort((a, b) => b.value - a.value);
    stRowsAll.forEach(r => r.tip = [["Region", r.region], ["Revenue", fmt.money(r.value)], ["Orders", fmt.int(r.orders)], ["AOV", fmt.money(r.value / r.orders)]]);
    let stRows = stRowsAll.slice(0, 10);
    if (F.state >= 0 && !stRows.some(r => r.key === F.state)) { const s = stRowsAll.find(r => r.key === F.state); if (s) stRows = [...stRows.slice(0, 9), s]; }
    cStates.render(Dash.hbar, { rows: stRows, format: R, selected: F.state >= 0 ? F.state : null, labelWidth: 60,
      onClick: k => { F.state = F.state === k ? -1 : k; if (F.state >= 0) F.region = D.stateRegion[k]; update(); } }, {
      columns: [{ key: "label", label: "State" }, { key: "region", label: "Region" }, { key: "value", label: "Revenue", num: true, fmt: v => fmt.money(v) },
                { key: "orders", label: "Orders", num: true, fmt: fmt.int }],
      rows: stRowsAll,
    });

    // Late delivery rate by state
    const lateAll = D.states.map((s, i) => ({ key: i, label: s, delivered: sDel[i], late: sLate[i], value: sDel[i] ? 100 * sLate[i] / sDel[i] : 0 }))
      .filter(r => r.delivered > 0).sort((a, b) => b.value - a.value);
    lateAll.forEach(r => r.tip = [["Late", fmt.pct(r.value)], ["Late orders", fmt.int(r.late)], ["Delivered orders", fmt.int(r.delivered)]]);
    const lateRows = lateAll.filter(r => r.delivered >= 50).slice(0, 10);
    cLate.render(Dash.hbar, { rows: lateRows, format: v => fmt.pct(v), selected: F.state >= 0 ? F.state : null, labelWidth: 60,
      onClick: k => { F.state = F.state === k ? -1 : k; if (F.state >= 0) F.region = D.stateRegion[k]; update(); } }, {
      columns: [{ key: "label", label: "State" }, { key: "value", label: "Late %", num: true, fmt: v => fmt.pct(v) },
                { key: "late", label: "Late", num: true, fmt: fmt.int }, { key: "delivered", label: "Delivered", num: true, fmt: fmt.int }],
      rows: lateAll,
    });

    // Review score by delivery bucket
    const bSum = [0, 0, 0, 0], bCnt = [0, 0, 0, 0], bLow = [0, 0, 0, 0];
    for (let k = 0; k < N; k++) {
      if (!mask[k] || O.lt[k] < 0 || O.rv[k] < 0) continue;
      const b = bucketOf(O.dv[k]);
      bSum[b] += O.rv[k] / 100; bCnt[b]++; if (O.rv[k] <= 200) bLow[b]++;
    }
    const revRows = BUCKETS.map((b, i) => ({ label: b, value: bCnt[i] ? bSum[i] / bCnt[i] : 0, orders: bCnt[i], low: bCnt[i] ? 100 * bLow[i] / bCnt[i] : 0 }))
      .filter(r => r.orders > 0);
    revRows.forEach(r => r.tip = [["Average review", fmt.dec(r.value)], ["1-2 star reviews", fmt.pct(r.low)], ["Orders", fmt.int(r.orders)]]);
    cReview.render(Dash.col, { rows: revRows, format: v => fmt.dec(v), axisFormat: v => String(v), tickValues: [0, 1, 2, 3, 4, 5], aria: "Average review by delivery timeliness" }, {
      columns: [{ key: "label", label: "Delivery" }, { key: "value", label: "Avg review", num: true, fmt: v => fmt.dec(v) },
                { key: "low", label: "1-2 star share", num: true, fmt: v => fmt.pct(v) }, { key: "orders", label: "Orders", num: true, fmt: fmt.int }],
      rows: revRows,
    });

    // Regions
    const mNoGeo = buildMask({ ignoreState: true, ignoreRegion: true });
    const gRev = new Float64Array(D.regions.length), gOrd = new Uint32Array(D.regions.length);
    for (let k = 0; k < N; k++) if (mNoGeo[k] && VALID[O.st[k]] && O.n[k] > 0) { const g = D.stateRegion[O.s[k]]; gRev[g] += rev[k]; gOrd[g]++; }
    const gTotal = gRev.reduce((a, b) => a + b, 0) || 1;
    const regRows = D.regions.map((r, i) => ({ key: i, label: r, value: gRev[i] / 100, orders: gOrd[i], share: 100 * gRev[i] / gTotal }))
      .filter(r => r.value > 0).sort((a, b) => b.value - a.value);
    regRows.forEach(r => r.tip = [["Revenue", fmt.money(r.value)], ["Share", fmt.pct(r.share)], ["Orders", fmt.int(r.orders)], ["AOV", fmt.money(r.value / r.orders)]]);
    cRegion.render(Dash.hbar, { rows: regRows, format: R, selected: F.region >= 0 ? F.region : null, labelWidth: 100,
      onClick: k => { F.region = F.region === k ? -1 : k; F.state = -1; update(); } }, {
      columns: [{ key: "label", label: "Region" }, { key: "value", label: "Revenue", num: true, fmt: v => fmt.money(v) },
                { key: "share", label: "Share", num: true, fmt: v => fmt.pct(v) }, { key: "orders", label: "Orders", num: true, fmt: fmt.int }],
      rows: regRows,
    });

    // Order status
    const stCnt = new Uint32Array(D.statuses.length); let stTot = 0;
    for (let k = 0; k < N; k++) if (mask[k]) { stCnt[O.st[k]]++; stTot++; }
    const statusRows = D.statuses.map((s, i) => ({ label: s, value: stCnt[i], share: stTot ? 100 * stCnt[i] / stTot : 0 }))
      .filter(r => r.value > 0).sort((a, b) => b.value - a.value);
    statusRows.forEach(r => r.tip = [["Orders", fmt.int(r.value)], ["Share", fmt.pct(r.share, 2)]]);
    cStatus.render(Dash.hbar, { rows: statusRows, format: v => fmt.compact(v), labelWidth: 90 }, {
      columns: [{ key: "label", label: "Status" }, { key: "value", label: "Orders", num: true, fmt: fmt.int },
                { key: "share", label: "Share", num: true, fmt: v => fmt.pct(v, 2) }],
      rows: statusRows,
    });
  }

  // Optional presets from the URL hash, e.g. dashboard.html#region=Northeast&cat=watches%20gifts&theme=light
  const H = new URLSearchParams(location.hash.slice(1));
  if (H.get("theme")) document.documentElement.dataset.theme = H.get("theme");
  const find = (list, v) => list.findIndex(x => x.toLowerCase() === String(v).toLowerCase());
  if (H.get("region")) F.region = find(D.regions, H.get("region"));
  if (H.get("state")) { F.state = find(D.states, H.get("state")); if (F.state >= 0) F.region = D.stateRegion[F.state]; }
  if (H.get("cat")) F.cat = find(D.categories, H.get("cat"));
  if (H.get("from")) F.from = Math.max(0, D.months.indexOf(H.get("from")));
  if (H.get("to") && D.months.includes(H.get("to"))) F.to = D.months.indexOf(H.get("to"));

  update();
})();
