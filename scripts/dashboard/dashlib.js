/* dashlib.js - tiny dependency-free SVG chart kit used by the HTML dashboards.
   Works offline in any modern browser on macOS or Windows. */
const Dash = (() => {
  const NS = "http://www.w3.org/2000/svg";
  let tip = null;

  function svgEl(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function text(parent, x, y, str, attrs = {}) {
    const t = svgEl("text", { x, y, "font-size": 12, fill: "var(--text-secondary)", ...attrs }, parent);
    t.textContent = str;
    return t;
  }

  /* ---------- tooltip ---------- */
  function ensureTip() {
    if (!tip) { tip = document.createElement("div"); tip.className = "tooltip"; document.body.appendChild(tip); }
    return tip;
  }
  function showTip(evt, title, rows) {
    const t = ensureTip();
    t.replaceChildren();
    const h = document.createElement("div"); h.className = "t-title"; h.textContent = title; t.appendChild(h);
    for (const [k, v] of rows) {
      const r = document.createElement("div"); r.className = "t-row";
      r.append(k + ": ");
      const b = document.createElement("b"); b.textContent = v; r.appendChild(b);
      t.appendChild(r);
    }
    t.style.opacity = 1;
    const pad = 14, w = t.offsetWidth, hgt = t.offsetHeight;
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + w > window.innerWidth - 8) x = evt.clientX - w - pad;
    if (y + hgt > window.innerHeight - 8) y = evt.clientY - hgt - pad;
    t.style.left = Math.max(8, x) + "px"; t.style.top = Math.max(8, y) + "px";
  }
  function hideTip() { if (tip) tip.style.opacity = 0; }

  /* ---------- number helpers ---------- */
  function niceStep(raw) {
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const m = raw / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
  }
  function ticks(max, n = 4) {
    if (!(max > 0)) return [0, 1];
    const step = niceStep(max / n);
    const out = [];
    for (let v = 0; v <= max + step * 0.999; v += step) out.push(+v.toFixed(10));
    return out;
  }
  function compact(v, prefix = "", decimals) {
    const a = Math.abs(v);
    const d = (x, def) => (decimals ?? def);
    if (a >= 1e9) return prefix + (v / 1e9).toFixed(d(v, 1)).replace(/\.0$/, "") + "B";
    if (a >= 1e6) return prefix + (v / 1e6).toFixed(d(v, 2)).replace(/\.?0+$/, "") + "M";
    if (a >= 1e4) return prefix + (v / 1e3).toFixed(d(v, 0)) + "K";
    return prefix + v.toLocaleString("en-US", { maximumFractionDigits: 0 });
  }
  const fmt = {
    int: v => Math.round(v).toLocaleString("en-US"),
    money: (v, cur = "R$") => cur + v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    moneyCompact: (v, cur = "R$") => compact(v, cur),
    pct: (v, d = 1) => v.toFixed(d) + "%",
    dec: (v, d = 2) => v.toFixed(d),
    compact,
  };
  function truncate(s, maxChars) { return s.length > maxChars ? s.slice(0, maxChars - 1) + "…" : s; }

  /* ---------- card with chart/table toggle ---------- */
  function card(container, { title, subtitle = "", wide = false }) {
    const root = document.createElement("section");
    root.className = "card" + (wide ? " wide" : "");
    root.innerHTML = '<div class="head"><div><h2></h2><div class="subtitle"></div></div>' +
      '<button class="toggle" type="button" aria-pressed="false">Table</button></div>' +
      '<div class="chart"></div><div class="tbl-wrap" hidden></div>';
    root.querySelector("h2").textContent = title;
    root.querySelector(".subtitle").textContent = subtitle;
    container.appendChild(root);
    const chartEl = root.querySelector(".chart"), tblEl = root.querySelector(".tbl-wrap");
    const btn = root.querySelector(".toggle");
    let last = null, showTable = false, lastW = 0;
    btn.addEventListener("click", () => {
      showTable = !showTable;
      btn.textContent = showTable ? "Chart" : "Table";
      btn.setAttribute("aria-pressed", String(showTable));
      chartEl.hidden = showTable; tblEl.hidden = !showTable;
      if (!showTable) redraw();
    });
    function redraw() {
      if (!last || showTable) return;
      chartEl.replaceChildren();
      const w = chartEl.clientWidth || 600;
      lastW = w;
      if (!last.spec.rows.length) { chartEl.innerHTML = '<div class="empty">No data for the current filters</div>'; return; }
      last.draw(chartEl, w, last.spec);
    }
    new ResizeObserver(() => { if (Math.abs((chartEl.clientWidth || 0) - lastW) > 2) redraw(); }).observe(chartEl);
    return {
      set subtitle(s) { root.querySelector(".subtitle").textContent = s; },
      render(draw, spec, table) {
        last = { draw, spec };
        renderTable(tblEl, table.columns, table.rows);
        redraw();
      },
    };
  }

  function renderTable(el, columns, rows) {
    const t = document.createElement("table"); t.className = "data";
    const hr = t.createTHead().insertRow();
    for (const c of columns) { const th = document.createElement("th"); th.textContent = c.label; if (c.num) th.className = "num"; hr.appendChild(th); }
    const tb = t.createTBody();
    for (const r of rows) {
      const tr = tb.insertRow();
      for (const c of columns) {
        const td = tr.insertCell(); const v = r[c.key];
        td.textContent = v == null || (typeof v === "number" && isNaN(v)) ? "-" : c.fmt ? c.fmt(v) : v;
        if (c.num) td.className = "num";
      }
    }
    el.replaceChildren(t);
  }

  /* ---------- horizontal bar ---------- */
  function hbar(el, width, spec) {
    const { rows, format, selected = null, onClick = null } = spec;
    const rowH = 28, barH = 16, top = 4;
    const labelW = Math.min(spec.labelWidth || 150, Math.max(70, width * 0.34));
    const valueW = 70;
    const plotW = Math.max(40, width - labelW - valueW - 8);
    const max = Math.max(...rows.map(r => r.value), 0) || 1;
    const h = top + rows.length * rowH + 4;
    const svg = svgEl("svg", { viewBox: `0 0 ${width} ${h}`, role: "img", "aria-label": spec.aria || "bar chart" }, el);
    const x0 = labelW + 8;
    svgEl("line", { x1: x0, x2: x0, y1: top, y2: h - 4, stroke: "var(--axis)", "stroke-width": 1 }, svg);
    rows.forEach((r, i) => {
      const y = top + i * rowH, cy = y + rowH / 2;
      const g = svgEl("g", { style: onClick ? "cursor:pointer" : "" }, svg);
      const hit = svgEl("rect", { x: 0, y, width, height: rowH, fill: "transparent", rx: 4 }, g);
      text(g, 0, cy + 4, truncate(r.label, Math.floor(labelW / 6.6)), { fill: "var(--text-primary)" });
      const bw = Math.max(1, (r.value / max) * plotW);
      const rr = Math.min(4, bw / 2, barH / 2), x1 = x0 + bw, yb = cy - barH / 2;
      const dim = selected != null && r.key !== selected;
      svgEl("path", {
        d: `M${x0},${yb} H${x1 - rr} A${rr},${rr} 0 0 1 ${x1},${yb + rr} V${yb + barH - rr} A${rr},${rr} 0 0 1 ${x1 - rr},${yb + barH} H${x0} Z`,
        fill: dim ? "var(--series-1-soft)" : "var(--series-1)",
      }, g);
      text(g, x1 + 6, cy + 4, format(r.value), { fill: "var(--text-primary)", "font-weight": 500 });
      g.addEventListener("mousemove", e => { hit.setAttribute("fill", "var(--hover-wash)"); showTip(e, r.label, r.tip || [["Value", format(r.value)]]); });
      g.addEventListener("mouseleave", () => { hit.setAttribute("fill", "transparent"); hideTip(); });
      if (onClick) g.addEventListener("click", () => { hideTip(); onClick(r.key); });
    });
  }

  /* ---------- column ---------- */
  function col(el, width, spec) {
    const { rows, format, axisFormat = format } = spec;
    const h = spec.height || 230, padL = 44, padB = 34, padT = 22, padR = 8;
    const plotW = width - padL - padR, plotH = h - padT - padB;
    const max = spec.max ?? Math.max(...rows.map(r => r.value), 0);
    const tk = spec.tickValues || ticks(max, 4), top = tk[tk.length - 1];
    const svg = svgEl("svg", { viewBox: `0 0 ${width} ${h}`, role: "img", "aria-label": spec.aria || "column chart" }, el);
    tk.forEach(v => {
      const y = padT + plotH - (v / top) * plotH;
      svgEl("line", { x1: padL, x2: width - padR, y1: y, y2: y, stroke: v === 0 ? "var(--axis)" : "var(--grid)", "stroke-width": 1 }, svg);
      text(svg, padL - 6, y + 4, axisFormat(v), { "text-anchor": "end", fill: "var(--text-muted)", "font-size": 11 });
    });
    const band = plotW / rows.length, bw = Math.min(24, band * 0.6);
    rows.forEach((r, i) => {
      const cx = padL + band * (i + 0.5);
      const bh = Math.max(1, (r.value / top) * plotH), yb = padT + plotH - bh, x = cx - bw / 2, rr = Math.min(4, bh);
      const g = svgEl("g", {}, svg);
      const hit = svgEl("rect", { x: padL + band * i + 2, y: padT, width: band - 4, height: plotH, fill: "transparent", rx: 4 }, g);
      svgEl("path", {
        d: `M${x},${padT + plotH} V${yb + rr} A${rr},${rr} 0 0 1 ${x + rr},${yb} H${x + bw - rr} A${rr},${rr} 0 0 1 ${x + bw},${yb + rr} V${padT + plotH} Z`,
        fill: r.color || "var(--series-1)",
      }, g);
      text(g, cx, yb - 6, format(r.value), { "text-anchor": "middle", fill: "var(--text-primary)", "font-weight": 500 });
      const maxChars = Math.max(4, Math.floor(band / 6.2));
      text(g, cx, h - padB + 16, truncate(r.label, maxChars), { "text-anchor": "middle", "font-size": 11.5 });
      g.addEventListener("mousemove", e => { hit.setAttribute("fill", "var(--hover-wash)"); showTip(e, r.label, r.tip || [["Value", format(r.value)]]); });
      g.addEventListener("mouseleave", () => { hit.setAttribute("fill", "transparent"); hideTip(); });
    });
  }

  /* ---------- line with crosshair ---------- */
  function line(el, width, spec) {
    const { rows, format, axisFormat = format } = spec;
    const h = spec.height || 260, padL = 52, padR = 64, padT = 16, padB = 28;
    const plotW = width - padL - padR, plotH = h - padT - padB;
    const max = Math.max(...rows.map(r => r.value), 0);
    const tk = ticks(max, 4), top = tk[tk.length - 1];
    const n = rows.length;
    const X = i => padL + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);
    const Y = v => padT + plotH - (v / top) * plotH;
    const svg = svgEl("svg", { viewBox: `0 0 ${width} ${h}`, role: "img", "aria-label": spec.aria || "line chart" }, el);
    tk.forEach(v => {
      svgEl("line", { x1: padL, x2: width - padR, y1: Y(v), y2: Y(v), stroke: v === 0 ? "var(--axis)" : "var(--grid)", "stroke-width": 1 }, svg);
      text(svg, padL - 8, Y(v) + 4, axisFormat(v), { "text-anchor": "end", fill: "var(--text-muted)", "font-size": 11 });
    });
    const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(plotW / 70))));
    rows.forEach((r, i) => {
      if (i % every === 0 || i === n - 1) {
        if (i === n - 1 && i % every !== 0 && (i % every) < every / 2) return;
        text(svg, X(i), h - 8, r.short || r.label, { "text-anchor": "middle", fill: "var(--text-muted)", "font-size": 11 });
      }
    });
    const pts = rows.map((r, i) => `${X(i)},${Y(r.value)}`);
    svgEl("path", { d: `M${X(0)},${Y(0)} L${pts.join(" L")} L${X(n - 1)},${Y(0)} Z`, fill: "var(--series-1)", opacity: 0.1 }, svg);
    svgEl("path", { d: `M${pts.join(" L")}`, fill: "none", stroke: "var(--series-1)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    const last = rows[n - 1];
    svgEl("circle", { cx: X(n - 1), cy: Y(last.value), r: 4, fill: "var(--series-1)", stroke: "var(--surface-1)", "stroke-width": 2 }, svg);
    text(svg, X(n - 1) + 8, Y(last.value) + 4, format(last.value), { fill: "var(--text-primary)", "font-weight": 500 });
    // peak marker
    if (spec.markPeak) {
      let pi = 0; rows.forEach((r, i) => { if (r.value > rows[pi].value) pi = i; });
      if (pi !== n - 1) {
        svgEl("circle", { cx: X(pi), cy: Y(rows[pi].value), r: 4, fill: "var(--series-1)", stroke: "var(--surface-1)", "stroke-width": 2 }, svg);
        text(svg, X(pi), Y(rows[pi].value) - 10, "Peak " + format(rows[pi].value), { "text-anchor": "middle", fill: "var(--text-primary)", "font-size": 11.5 });
      }
    }
    const cross = svgEl("line", { y1: padT, y2: padT + plotH, stroke: "var(--axis)", "stroke-width": 1, opacity: 0 }, svg);
    const dot = svgEl("circle", { r: 5, fill: "var(--series-1)", stroke: "var(--surface-1)", "stroke-width": 2, opacity: 0 }, svg);
    const overlay = svgEl("rect", { x: padL - 10, y: padT, width: plotW + 20, height: plotH, fill: "transparent" }, svg);
    overlay.addEventListener("mousemove", e => {
      const box = svg.getBoundingClientRect();
      const px = (e.clientX - box.left) * (width / box.width);
      const i = Math.max(0, Math.min(n - 1, Math.round(((px - padL) / plotW) * (n - 1))));
      const r = rows[i];
      cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.setAttribute("opacity", 1);
      dot.setAttribute("cx", X(i)); dot.setAttribute("cy", Y(r.value)); dot.setAttribute("opacity", 1);
      showTip(e, r.label, r.tip || [["Value", format(r.value)]]);
    });
    overlay.addEventListener("mouseleave", () => { cross.setAttribute("opacity", 0); dot.setAttribute("opacity", 0); hideTip(); });
  }

  /* ---------- KPI tiles ---------- */
  function tiles(el, items) {
    el.replaceChildren();
    for (const it of items) {
      const d = document.createElement("div");
      d.className = "tile" + (it.hero ? " hero" : "");
      d.innerHTML = '<div class="label"></div><div class="value"></div><div class="sub"></div>';
      d.querySelector(".label").textContent = it.label;
      d.querySelector(".value").textContent = it.value;
      d.querySelector(".sub").textContent = it.sub || "";
      el.appendChild(d);
    }
  }

  function fillSelect(sel, options, allLabel) {
    sel.replaceChildren();
    if (allLabel) { const o = document.createElement("option"); o.value = ""; o.textContent = allLabel; sel.appendChild(o); }
    for (const [value, label] of options) { const o = document.createElement("option"); o.value = value; o.textContent = label; sel.appendChild(o); }
  }

  return { card, hbar, col, line, tiles, fmt, fillSelect, renderTable };
})();
