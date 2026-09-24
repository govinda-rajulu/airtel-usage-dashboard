/* My Broadband Meter. Renders data/usage.json only; no external calls. */
(function () {
  "use strict";

  function fmtGB(v) {
    if (v === null || v === undefined || isNaN(v)) return "–";
    return (Math.round(v * 10) / 10).toFixed(1);
  }
  function el(id) { return document.getElementById(id); }

  function setDial(pct) {
    var arc = el("arc");
    var len = arc.getTotalLength();
    var p = Math.max(0, Math.min(1, pct));
    arc.setAttribute("stroke-dasharray", (len * p) + " " + len);
    arc.style.stroke = p >= 0.95 ? "var(--brand)" : (p >= 0.8 ? "var(--amber)" : "var(--brand)");
  }

  function drawDaily(canvas, daily, unit) {
    var ctx = canvas.getContext("2d");
    var W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    var padL = 46, padR = 10, padT = 14, padB = 34;
    var plotW = W - padL - padR, plotH = H - padT - padB;
    if (!daily || !daily.length) {
      ctx.fillStyle = "#8b95a6"; ctx.font = "13px Inter";
      ctx.fillText("No daily breakdown in usage.json yet.", padL, padT + 24);
      return;
    }
    var max = 0, i;
    for (i = 0; i < daily.length; i++) { if (daily[i].used > max) max = daily[i].used; }
    if (max <= 0) max = 1;
    var steps = 4, s;
    ctx.strokeStyle = "#2a3342"; ctx.fillStyle = "#8b95a6"; ctx.font = "11px Inter";
    for (s = 0; s <= steps; s++) {
      var y = padT + plotH - (plotH * s / steps);
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
      ctx.fillText((max * s / steps).toFixed(1), 6, y + 4);
    }
    var bw = Math.max(3, plotW / daily.length - 4);
    for (i = 0; i < daily.length; i++) {
      var x = padL + (plotW * i / daily.length) + 2;
      var h = plotH * daily[i].used / max;
      var y2 = padT + plotH - h;
      ctx.fillStyle = "#e0202c";
      ctx.fillRect(x, y2, bw, h);
      if (daily.length <= 31 && i % Math.ceil(daily.length / 10) === 0) {
        ctx.fillStyle = "#8b95a6";
        var lbl = (daily[i].date || "").slice(8);
        ctx.fillText(lbl, x, H - 12);
        ctx.fillStyle = "#e0202c";
      }
    }
  }


  function fillTable(id, rows, emptyMsg) {
    var tb = document.querySelector("#" + id + " tbody");
    if (!tb) return;
    tb.innerHTML = "";
    if (!rows || !rows.length) {
      var tr0 = document.createElement("tr");
      var td0 = document.createElement("td");
      td0.colSpan = 2;
      td0.className = "muted";
      td0.textContent = emptyMsg;
      tr0.appendChild(td0);
      tb.appendChild(tr0);
      return;
    }
    rows.forEach(function (r) {
      var tr = document.createElement("tr");
      var k = document.createElement("td");
      k.textContent = r.field;
      k.title = r.section || "";
      var v = document.createElement("td");
      v.textContent = r.value;
      tr.appendChild(k); tr.appendChild(v);
      tb.appendChild(tr);
    });
  }

  function render(data) {
    var cur = data.current || {};
    el("usedNow").textContent = fmtGB(cur.usedGB);
    el("unitNow").textContent = cur.unit || "GB";
    el("remainNow").textContent = fmtGB(cur.remainingGB);
    el("totalNow").textContent = fmtGB(cur.totalGB);
    el("cycleNow").textContent = cur.cycleLabel || "–";

    var pct = (cur.usedGB !== null && cur.totalGB) ? cur.usedGB / cur.totalGB : 0;
    setDial(pct);

    var pace = el("paceNow");
    if (cur.daysTotal && cur.daysElapsed) {
      var expected = cur.daysElapsed / cur.daysTotal;
      var ratio = cur.totalGB ? pct / expected : 0;
      if (ratio < 0.9) { pace.textContent = "Under pace"; pace.className = "ok"; }
      else if (ratio <= 1.15) { pace.textContent = "On pace"; pace.className = "warn"; }
      else { pace.textContent = "Burning fast"; pace.className = "bad"; }
    } else { pace.textContent = "–"; }

    el("lastFetched").textContent = data.fetchedAt
      ? "updated " + data.fetchedAt : "no data yet";

    drawDaily(el("dailyChart"), data.daily || []);
    el("dailyNote").textContent = (data.daily && data.daily.length)
      ? "Units: " + (cur.unit || "GB") + " per day" : "";

    var tb = document.querySelector("#monthTable tbody");
    tb.innerHTML = "";
    (data.history || []).slice().reverse().forEach(function (h) {
      var tr = document.createElement("tr");
      var p = h.totalGB ? Math.round(100 * h.usedGB / h.totalGB) : null;
      [h.cycleLabel || "–", fmtGB(h.usedGB), fmtGB(h.totalGB), p === null ? "–" : p + "%"]
        .forEach(function (v) {
          var td = document.createElement("td"); td.textContent = v; tr.appendChild(td);
        });
      tb.appendChild(tr);
    });

    fillTable("planTable", data.plan || [], "No plan fields captured yet. Run scripts/collect.py.");
    fillTable("billTable", data.bills || [], "No bill fields captured yet.");
    fillTable("serviceTable", data.services || [], "No linked-service fields captured yet.");

    var ul = el("fetchLog");
    ul.innerHTML = "";
    (data.fetchLog || []).slice().reverse().forEach(function (f) {
      var li = document.createElement("li");
      var cls = f.status === "ok" ? "ok" : (f.status === "failed" ? "bad" : "");
      li.innerHTML = '<span class="' + cls + '">' + (f.status || "?").toUpperCase() +
        "</span> · " + (f.at || "?") + " · " + (f.note || "");
      ul.appendChild(li);
    });
  }

  fetch("data/usage.json", { cache: "no-store" })
    .then(function (r) { if (!r.ok) throw new Error("usage.json HTTP " + r.status); return r.json(); })
    .then(render)
    .catch(function (e) {
      el("lastFetched").textContent = "could not load data/usage.json (" + e.message + ")";
    });
})();
