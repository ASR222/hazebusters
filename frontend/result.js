// Result screen, built from backend/contract.json (`result`) plus GET /jobs' presigned `audio_urls` / `gradcam_url`.
(function () {
  const { BANDS, category, esc, parts, clock, ago } = window.fmt;

  const PROFILES = { school: "School", worker: "Outdoor worker", general: "General" };
  const PROFILE_HOURS = { school: [7, 17], worker: [6, 19], general: [6, 21] };  // backend combine.PROFILE_WINDOWS
  const VERDICT = { yes: "Outdoors OK", limit: "Limit outdoor time", no: "Avoid outdoors" };
  const REASONS = {
    aqi_le_100: "AQI stays at or below 100 (Good/Satisfactory) through these hours.",
    aqi_101_200: "AQI reaches 101–200 (Moderate) in these hours: keep outdoor time short and light, especially for children and people with asthma.",
    aqi_gt_200: "AQI goes above 200 (Poor or worse) in these hours.",
    no_window_today: "No 3-hour slot with AQI at or below 100 is left in these hours today.",
    no_window_tomorrow: "No 3-hour slot with AQI at or below 100 in these hours tomorrow.",
  };

  const hourText = (h) => clock(`2000-01-01T${String(h).padStart(2, "0")}:00`);
  const bandClass = (b) => (b === 0 || b === 1 || b === 2 ? `b${b}` : "");

  function decisionCard(r) {
    const d = r.decision;
    if (!d) return "";
    const day = d.for === "tomorrow" ? "Tomorrow" : "Today";
    const [h0, h1] = PROFILE_HOURS[r.profile] || [];
    const hours = h0 != null ? ` · ${PROFILES[r.profile]} hours ${hourText(h0)}–${hourText(h1)}` : "";
    let windowLine = `No good window ${day.toLowerCase()}`;
    if (d.outdoor === "yes" && h1 != null) {
      // "yes" = every slot left in the hours is fine, so the first-slot best_window would undersell it.
      windowLine = d.for === "tomorrow" ? `Fine all day, ${hourText(h0)}–${hourText(h1)}` : `Fine from now until ${hourText(h1)}`;
    } else if (d.best_window) {
      const start = parts(d.best_window.start), end = parts(d.best_window.end);
      // The backend clips today's first slot to the current time (e.g. 11:17); show that as "now".
      const from = d.for === "today" && start && start.min !== 0 ? "now" : clock(d.best_window.start);
      windowLine = end && end.h === h1 && end.min === 0
        ? (from === "now" ? `Outdoors fine from now` : `Outdoors after ${from}`)
        : `Best window: ${from}–${clock(d.best_window.end)}`;
    }
    return `
      <div class="card decision ${esc(d.outdoor)}">
        <p class="when">${day}${esc(hours)}</p>
        <p class="verdict"><strong>${esc(VERDICT[d.outdoor] || d.outdoor)}</strong></p>
        <p class="window">${esc(windowLine)}</p>
        <p class="reason">${esc(REASONS[d.reason_code] || d.reason_code || "")}</p>
      </div>`;
  }

  function sourceLine(air) {
    if (air.used === "measured" && air.measured) {
      const m = air.measured;
      return `Measured: ${esc(m.station)} · ${esc(m.dist_km)} km away · updated ${esc(ago(m.updated_at))}`;
    }
    if (air.modelled) return `Modelled: CAMS model, ~${esc(air.modelled.grid_km ?? 45)} km grid`;
    return "";
  }

  function otherLine(air) {
    const o = air.used === "measured" ? air.modelled : air.measured;
    if (!o || o.aqi_cpcb == null) return "";
    const what = air.used === "measured"
      ? "CAMS model for this area"
      : `Nearest station (${esc(o.station)}, ${esc(o.dist_km)} km, updated ${esc(ago(o.updated_at))})`;
    return `<p class="muted">${what}: AQI ${esc(o.aqi_cpcb)} (${esc(category(o.aqi_cpcb))})</p>`;
  }

  function aqiCard(r) {
    const air = r.air;
    if (!air || air.aqi_cpcb == null) return "";
    const chosen = air.used === "measured" ? air.measured : air.modelled;
    const pm = chosen
      ? [chosen.pm25 != null && `PM2.5 ${esc(chosen.pm25)}`, chosen.pm10 != null && `PM10 ${esc(chosen.pm10)}`].filter(Boolean).join(" · ")
      : "";
    const caveats = (r.caveats || []).filter(Boolean);
    return `
      <div class="card">
        <h2>Air now</h2>
        <div class="aqi-head">
          <span class="aqi-num">${esc(air.aqi_cpcb)}</span>
          <span class="pill ${bandClass(air.band)}">${esc(category(air.aqi_cpcb))}</span>
          <span class="muted">CPCB-style AQI</span>
        </div>
        <div class="kv">
          <p>${sourceLine(air)}</p>
          ${pm ? `<p class="muted">${pm} µg/m³</p>` : ""}
          <p><strong class="conf-${esc(air.confidence)}">Confidence: ${esc(air.confidence)}</strong>
            ${air.confidence_reason ? `— ${esc(air.confidence_reason)}` : ""}</p>
          ${otherLine(air)}
          ${r.seasonal_line ? `<p>${esc(r.seasonal_line)}</p>` : ""}
        </div>
        ${caveats.length ? `<p class="caveat">${esc(caveats[0])}</p>` : ""}
        ${caveats.length > 1 ? `<details class="caveats"><summary>Details (${caveats.length - 1})</summary>
          <ul>${caveats.slice(1).map((c) => `<li>${esc(c)}</li>`).join("")}</ul></details>` : ""}
      </div>`;
  }

  function strip(title, slots, scale) {
    if (!slots || !slots.length) return "";
    const bars = slots.map((s) => {
      const pct = Math.max(4, Math.min(100, (s.aqi_cpcb / scale) * 100));
      return `<div class="slot" title="${esc(clock(s.time))}: AQI ${esc(s.aqi_cpcb)} (${esc(category(s.aqi_cpcb))})">
          <span class="val">${esc(s.aqi_cpcb)}</span>
          <div class="bar ${bandClass(s.band)}" style="height:${pct}%"></div>
        </div>`;
    }).join("");
    const labels = slots.map((s) => `<span>${esc(clock(s.time).replace(":00", ""))}</span>`).join("");
    return `<div class="strip-day"><h3>${title}</h3>
        <div class="strip" role="img" aria-label="${title} AQI every 3 hours">${bars}</div>
        <div class="strip-labels">${labels}</div></div>`;
  }

  function forecastCard(r) {
    const today = r.forecast_today || [];
    const tomorrow = r.forecast_tomorrow || [];
    if (!today.length && !tomorrow.length) return "";
    const scale = Math.max(200, ...today.concat(tomorrow).map((s) => s.aqi_cpcb || 0));
    const legend = BANDS.map((b, i) => `<span><i class="b${i}"></i>${esc(b)}</span>`).join("");
    return `
      <div class="card">
        <h2>Forecast (3-hour slots)</h2>
        ${strip("Today", today, scale)}
        ${strip("Tomorrow", tomorrow, scale)}
        <div class="legend">${legend}</div>
      </div>`;
  }

  function causeRow(name, c) {
    if (!c) return "";
    // Classifier output, not a confirmed detection: >= 0.6 "Likely", present below that "Possible".
    const [label, cls] = c.present && c.prob >= 0.6 ? ["Likely", "likely"] : c.present ? ["Possible", "possible"] : ["Not seen", "muted"];
    const score = c.prob != null ? ` (model score ${Math.round(c.prob * 100)}%)` : "";
    return `<div class="cause"><span>${name}</span>
      <span class="${cls}">${label}${score}</span></div>`;
  }

  // Quality-gate reject codes in plain words (gate checks: CLAUDE.md §4); unknown codes are shown with spaces.
  const REJECT_WORDS = {
    night: "too dark", dark: "too dark", too_dark: "too dark", low_light: "too dark",
    blur: "too blurry", blurry: "too blurry", too_blurry: "too blurry", shaky: "too shaky",
    no_sky: "no sky or street in view", sky: "no sky or street in view",
    indoor: "looks like indoors", indoors: "looks like indoors",
  };
  const plainReason = (code) => REJECT_WORDS[String(code).toLowerCase()] || String(code).replace(/_/g, " ");

  // The gate rejected the whole clip: every frame rejected, or a quality-gate caveat.
  function gateBlocked(r) {
    const c = r.causes;
    if (c.frames_rejected > 0 && c.frames_used === 0) return true;
    return (r.caveats || []).some((t) => /quality gate/i.test(String(t)));
  }

  function causesCard(r, camUrl) {
    const c = r.causes;
    if (!c) return "";
    const reasons = (c.reject_reasons || []).filter(Boolean);
    if (gateBlocked(r)) {
      const words = [...new Set(reasons.map(plainReason))];
      return `
      <div class="card">
        <h2>What's in your video</h2>
        <p>Couldn't check this clip${words.length ? `: ${esc(words.join(", "))}` : ""}. Point the camera at the sky or street outdoors.</p>
      </div>`;
    }
    const frames = c.frames_used != null
      ? `<p class="muted">Frames analysed: ${esc(c.frames_used)}${c.frames_rejected ? `, rejected ${esc(c.frames_rejected)}` : ""}${reasons.length ? ` (${esc(reasons.join(", "))})` : ""}</p>`
      : "";
    const vehicles = c.vehicle_count != null
      ? `<div class="cause"><span>Vehicles in view</span><span>${esc(c.vehicle_count)}</span></div>` : "";
    const cam = camUrl
      ? `<img class="cam" src="${esc(camUrl)}" alt="Heatmap of where the model saw smoke or fire" loading="lazy">
         <p class="muted">Highlighted: where the model saw it (CAM).</p>` : "";
    return `
      <div class="card">
        <h2>What's in your video</h2>
        ${causeRow("Smoke", c.smoke)}
        ${causeRow("Fire", c.fire)}
        ${vehicles}
        ${cam}
        ${frames}
        <p class="muted">This only shows possible sources. It never changes the AQI.</p>
      </div>`;
  }

  function adviceCard(r, audio) {
    const a = r.advice;
    if (!a || (!a.en && !a.hi)) return "";
    const langs = [["en", "English", a.en], ["hi", "हिन्दी", a.hi]].filter(([, , text]) => text);
    const tabs = langs.map(([k, label], i) =>
      `<button type="button" role="tab" id="tab-${k}" aria-controls="panel-${k}" aria-selected="${i === 0}" lang="${k}">${label}</button>`).join("");
    const panels = langs.map(([k, , text], i) => {
      const url = audio && audio[k];
      return `<div role="tabpanel" id="panel-${k}" aria-labelledby="tab-${k}" ${i === 0 ? "" : "hidden"}>
          <p class="advice-text" lang="${k}">${esc(text)}</p>
          ${url ? `<audio controls preload="none" src="${esc(url)}"></audio>` : ""}
        </div>`;
    }).join("");
    const source = a.source === "bedrock" ? "Written by Amazon Bedrock from the numbers above." : "Template advice from the numbers above.";
    return `
      <div class="card advice">
        <h2>What to do</h2>
        <div class="tabs" role="tablist">${tabs}</div>
        ${panels}
        <p class="muted">${source}</p>
      </div>`;
  }

  // `picked`: {city} from the dropdown or {gps: true} (app.js); absent for mock results.
  function header(r, picked) {
    const loc = r.location || {};
    const coords = loc.lat != null ? `${(+loc.lat).toFixed(3)}, ${(+loc.lon).toFixed(3)}` : "";
    const place = loc.place || (picked && picked.city)
      || (picked && picked.gps ? `Your location${coords ? ` (${coords})` : ""}` : coords);
    return `<p class="muted">${esc(place)}${place ? " · " : ""}${esc(PROFILES[r.profile] || "")}</p>`;
  }

  function bindTabs(root) {
    root.querySelectorAll('[role="tab"]').forEach((tab) => {
      tab.addEventListener("click", () => {
        root.querySelectorAll('[role="tab"]').forEach((t) => {
          const on = t === tab;
          t.setAttribute("aria-selected", String(on));
          root.querySelector(`#${t.getAttribute("aria-controls")}`).hidden = !on;
          if (!on) root.querySelectorAll(`#${t.getAttribute("aria-controls")} audio`).forEach((el) => el.pause());
        });
      });
    });
  }

  // `job` = GET /jobs/{id} body {result, audio_urls, gradcam_url}, or a bare contract result (mock).
  function render(root, job, picked) {
    const r = job.result || job;
    root.innerHTML = header(r, picked) + decisionCard(r) + aqiCard(r) + forecastCard(r)
      + causesCard(r, job.gradcam_url) + adviceCard(r, job.audio_urls);
    bindTabs(root);
  }

  window.renderResult = render;
})();
