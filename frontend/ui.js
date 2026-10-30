// Presentational behaviour only. Nothing here calls the API or changes the check flow in app.js.
// Pieces: theme toggle, nav (menu, active link, read progress), hero slideshow, photo wall, how-it-works stepper,
// before/after slider, AQI + "how sure" playground, one-minute tour, latest-data band + status list
// (read from the result app.js already rendered), About-the-data modal, reveal-on-scroll.
// Every block checks its elements exist, so the same file serves index.html and help.html.
(function () {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = {  // browser storage can be blocked; never let that break the page
    get(area, k) { try { return window[area].getItem(k); } catch (_) { return null; } },
    set(area, k, v) { try { window[area].setItem(k, v); } catch (_) { /* ignore */ } },
  };

  // --- Theme toggle (system default; a saved choice wins) --------------------------
  const root = document.documentElement;
  const sysDark = window.matchMedia("(prefers-color-scheme: dark)");
  const isDark = () => root.dataset.theme === "dark" || (!root.dataset.theme && sysDark.matches);
  const syncToggle = () => $$("[data-theme-toggle]").forEach((b) => {
    b.setAttribute("aria-label", isDark() ? "Switch to light theme" : "Switch to dark theme");
    b.classList.toggle("is-dark", isDark());
  });
  $$("[data-theme-toggle]").forEach((b) => b.addEventListener("click", () => {
    const next = isDark() ? "light" : "dark";
    root.dataset.theme = next;
    store.set("localStorage", "hb-theme", next);
    syncToggle();
  }));
  sysDark.addEventListener?.("change", syncToggle);
  syncToggle();

  // --- Mobile nav --------------------------------------------------------------------
  const toggle = $(".nav-toggle");
  const links = $("#nav-links");
  if (toggle && links) {
    const setOpen = (open) => {
      toggle.setAttribute("aria-expanded", String(open));
      links.classList.toggle("open", open);
    };
    toggle.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
    links.addEventListener("click", (e) => { if (e.target.closest("a")) setOpen(false); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });
  }

  // --- Read progress bar + active section link -----------------------------------------
  const bar = $("[data-read-progress]");
  if (bar) {
    let ticking = false;
    const paint = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.transform = `scaleX(${max > 0 ? Math.min(1, window.scrollY / max) : 0})`;
      ticking = false;
    };
    window.addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(paint); } }, { passive: true });
    paint();
  }
  const navAnchors = $$('#nav-links a[href^="#"]');
  if (navAnchors.length && "IntersectionObserver" in window) {
    const byId = new Map(navAnchors.map((a) => [a.getAttribute("href").slice(1), a]));
    const io = new IntersectionObserver((entries) => entries.forEach((en) => {
      const a = byId.get(en.target.id);
      if (a && en.isIntersecting) {
        navAnchors.forEach((x) => x.removeAttribute("aria-current"));
        a.setAttribute("aria-current", "true");
      }
    }), { rootMargin: "-45% 0px -50% 0px" });
    byId.forEach((_, id) => { const el = document.getElementById(id); if (el) io.observe(el); });
  }

  // --- Images: real photo if credits.js names a file, else original SVG art ----------------
  const credits = window.HB_CREDITS || { hero: [], gallery: [] };
  const creditLine = (c) => (c.file && c.credit
    ? `${esc(c.credit)}${c.source ? `, ${esc(c.source)}` : ""}${c.license ? ` (${esc(c.license)})` : ""}`
    : "Illustration: HazeBusters");
  const media = (c, eager) => (c.file
    ? `<img src="${esc(c.file)}" alt="${esc(c.alt)}" ${eager ? 'fetchpriority="high"' : 'loading="lazy"'} decoding="async">`
    : `<div class="art" role="img" aria-label="${esc(c.alt)}">${window.hbArt ? window.hbArt(c.art) : ""}</div>`);

  // Hero slideshow (crossfade). The CSS background stays as the no-JS fallback.
  const slidesEl = $("[data-hero-slides]");
  if (slidesEl && credits.hero.length) {
    slidesEl.innerHTML = credits.hero.map((c, i) => `<div class="slide${i === 0 ? " on" : ""}">${media(c, i === 0)}</div>`).join("");
    const slides = $$(".slide", slidesEl);
    const cap = $("[data-hero-caption]");
    const dots = $("[data-hero-dots]");
    dots.innerHTML = credits.hero.map((c, i) =>
      `<button type="button" aria-label="Show image ${i + 1}: ${esc(c.caption)}" aria-pressed="${i === 0}"></button>`).join("");
    let i = 0, timer = null;
    const show = (n) => {
      slides[i].classList.remove("on");
      i = (n + slides.length) % slides.length;
      slides[i].classList.add("on");
      $$("button", dots).forEach((d, k) => d.setAttribute("aria-pressed", String(k === i)));
      const c = credits.hero[i];
      cap.innerHTML = `${esc(c.caption)} <span>· ${creditLine(c)}</span>`;
    };
    const play = () => { if (!reduceMotion) { clearInterval(timer); timer = setInterval(() => show(i + 1), 6000); } };
    $$("button", dots).forEach((d, k) => d.addEventListener("click", () => { show(k); play(); }));
    document.addEventListener("visibilitychange", () => (document.hidden ? clearInterval(timer) : play()));
    show(0);
    play();
  }

  // Photo wall: one set of cards, duplicated (hidden from screen readers) for a seamless loop.
  const track = $("[data-gallery-track]");
  if (track && credits.gallery.length) {
    const card = (c, dup) => `<figure class="shot"${dup ? ' aria-hidden="true"' : ""}>
        <div class="shot-media">${media(c, false)}</div>
        <figcaption><b>${esc(c.caption)}</b><span>${creditLine(c)}</span></figcaption></figure>`;
    track.innerHTML = credits.gallery.map((c) => card(c, false)).join("") + credits.gallery.map((c) => card(c, true)).join("");
    if (reduceMotion) track.classList.add("still");
  }

  // --- Intent cards: pre-select the matching profile (same as tapping the radio) ----------
  $$(".intent[data-profile]").forEach((c) => c.addEventListener("click", () => {
    const radio = $(`input[name="profile"][value="${c.dataset.profile}"]`);
    if (radio) radio.checked = true;
  }));

  // --- How-it-works stepper ----------------------------------------------------------------
  const stepper = $("[data-stepper]");
  if (stepper) {
    const tabs = $$('[role="tab"]', stepper);
    const panels = $$('[role="tabpanel"]', stepper);
    const now = $("[data-step-now]", stepper);
    const prog = $("[data-step-bar]", stepper);
    let i = 0;
    const go = (n, focus) => {
      i = (n + tabs.length) % tabs.length;
      tabs.forEach((t, k) => { t.setAttribute("aria-selected", String(k === i)); t.tabIndex = k === i ? 0 : -1; });
      panels.forEach((p, k) => { p.hidden = k !== i; });
      now.textContent = String(i + 1);
      if (prog) prog.style.transform = `scaleX(${(i + 1) / tabs.length})`;
      const strip = tabs[i].parentElement;  // keep the active tab visible inside the tab strip only
      strip.scrollTo({ left: tabs[i].offsetLeft - 12, behavior: reduceMotion ? "auto" : "smooth" });
      if (focus) tabs[i].focus({ preventScroll: true });
    };
    stepper.classList.add("is-tabs");
    tabs.forEach((t, k) => t.addEventListener("click", () => go(k)));
    $(".step-tabs", stepper).addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") go(i + 1, true);
      else if (e.key === "ArrowLeft") go(i - 1, true);
    });
    $("[data-step-prev]", stepper).addEventListener("click", () => go(i - 1));
    $("[data-step-next]", stepper).addEventListener("click", () => go(i + 1));
    go(0);
  }

  // --- Before / after slider --------------------------------------------------------------
  const compare = $("[data-compare]");
  if (compare) {
    const range = $("[data-compare-range]", compare);
    const set = () => compare.style.setProperty("--pos", `${range.value}%`);
    range.addEventListener("input", set);
    set();
  }

  // --- Playground: AQI scale + "how sure" (same thresholds as the app; illustrative) ---------
  const explorer = $("[data-explorer]");
  if (explorer && window.fmt) {
    const range = $("#aqi-range");
    const out = $("#aqi-out");
    const pill = $("[data-explore-cat]", explorer);
    const verdict = $("[data-explore-verdict]", explorer);
    const band = $("[data-explore-band]", explorer);
    const dot = $("[data-meter-dot]", explorer);
    // Decision thresholds as in result.js REASONS (aqi_le_100 / aqi_101_200 / aqi_gt_200).
    const call = (aqi) => (aqi <= 100 ? ["Outdoors OK", "yes"] : aqi <= 200 ? ["Limit outdoor time", "limit"] : ["Avoid outdoors", "no"]);
    const bandIdx = (aqi) => (aqi <= 100 ? 0 : aqi <= 300 ? 1 : 2);  // format.js BANDS
    const update = () => {
      const aqi = +range.value;
      const cat = window.fmt.category(aqi);
      const [word, cls] = call(aqi);
      out.textContent = String(aqi);
      pill.textContent = cat;
      pill.className = `pill c-${cat.toLowerCase().replace(" ", "-")}`;
      verdict.textContent = word;
      verdict.dataset.state = cls;
      band.textContent = `Band: ${window.fmt.BANDS[bandIdx(aqi)]}`;
      dot.style.left = `${(aqi / 500) * 100}%`;
      $$(".chip[data-aqi]").forEach((c) => c.setAttribute("aria-pressed", String(+c.dataset.aqi === aqi)));
    };
    range.addEventListener("input", update);
    $$(".chip[data-aqi]").forEach((c) => c.addEventListener("click", () => { range.value = c.dataset.aqi; update(); }));
    update();
  }

  const sure = $("[data-sure]");
  if (sure) {
    const st = $("[data-sure-station]", sure), dist = $("[data-sure-dist]", sure), age = $("[data-sure-age]", sure), agree = $("[data-sure-agree]", sure);
    const badge = $("[data-sure-badge]", sure), src = $("[data-sure-source]", sure), why = $("[data-sure-reason]", sure);
    // Mirrors backend/src/air/combine.py: source = station if <= 25 km and < 3 h old, else CAMS x1.25;
    // confidence = high (near and bands agree), medium (one of those), low (neither, or model only).
    const update = () => {
      const on = st.checked, km = +dist.value, h = +age.value;
      $("[data-sure-dist-out]", sure).textContent = `${km} km`;
      $("[data-sure-age-out]", sure).textContent = h === 0 ? "just now" : `${h} h ago`;
      [dist, age, agree].forEach((el) => { el.disabled = !on; });
      sure.classList.toggle("no-station", !on);
      let level, reason;
      const near = km <= 25, same = agree.checked;
      if (!on) [level, reason] = ["low", "No station reading; CAMS model value only (~45 km grid)."];
      else if (near && same) [level, reason] = ["high", `Station and CAMS agree on the band; station ${km} km away.`];
      else if (near) [level, reason] = ["medium", `Station and CAMS disagree on the band; station ${km} km away.`];
      else if (same) [level, reason] = ["medium", `Station and CAMS agree on the band, but the station is ${km} km away.`];
      else [level, reason] = ["low", `Station is ${km} km away and disagrees with CAMS on the band.`];
      const useStation = on && near && h < 3;
      badge.className = `badge conf-${level}`;
      badge.textContent = `Confidence: ${level}`;
      src.textContent = useStation ? "Uses the station reading." : "Uses the CAMS model, scaled ×1.25 (it reads low against ground stations).";
      why.textContent = reason;
    };
    [st, dist, age, agree].forEach((el) => el.addEventListener("input", update));
    update();
  }

  // --- One-minute tour -------------------------------------------------------------------
  const tour = $("[data-tour]");
  if (tour) {
    const frames = $$("[data-tour-frame]", tour);
    const now = $("[data-tour-now]", tour);
    const prog = $("[data-tour-progress]", tour);
    const btn = $("[data-tour-toggle]", tour);
    const STEP_MS = 7000;
    let i = 0, t0 = 0, raf = 0, playing = !reduceMotion, elapsed = 0;
    const show = (n) => {
      frames[i].hidden = true;
      i = (n + frames.length) % frames.length;
      frames[i].hidden = false;
      now.textContent = String(i + 1);
    };
    const tick = (ts) => {
      if (!t0) t0 = ts - elapsed;
      elapsed = ts - t0;
      if (elapsed >= STEP_MS) { show(i + 1); t0 = ts; elapsed = 0; }
      prog.style.transform = `scaleX(${(i + elapsed / STEP_MS) / frames.length})`;
      raf = requestAnimationFrame(tick);
    };
    const setPlaying = (p) => {
      playing = p;
      cancelAnimationFrame(raf);
      t0 = 0;
      if (p) raf = requestAnimationFrame(tick);
      btn.textContent = p ? "❚❚" : "▶";
      btn.setAttribute("aria-label", p ? "Pause walkthrough" : "Play walkthrough");
    };
    btn.addEventListener("click", () => setPlaying(!playing));
    // Only run while visible on screen.
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(([en]) => { if (playing) { cancelAnimationFrame(raf); t0 = 0; if (en.isIntersecting) raf = requestAnimationFrame(tick); } })
        .observe(tour);
    }
    prog.style.transform = `scaleX(${1 / frames.length})`;
    setPlaying(playing);
  }

  // --- Latest data band + "Air quality now" list ----------------------------------------------
  // Reads the result that result.js renders into #result (no extra requests) and keeps it for this tab session.
  const live = $("[data-live]");
  const statusEl = $("[data-status]");
  const resultEl = $("#result");
  if (live || statusEl) {
    const CPCB = [["Good", "0–50", "Outdoors OK"], ["Satisfactory", "51–100", "Outdoors OK"], ["Moderate", "101–200", "Limit outdoor time"],
      ["Poor", "201–300", "Avoid outdoors"], ["Very Poor", "301–400", "Avoid outdoors"], ["Severe", "401–500", "Avoid outdoors"]];
    const cls = (cat) => `c-${String(cat).toLowerCase().replace(" ", "-")}`;
    const txt = (sel) => ((resultEl && $(sel, resultEl)) ? $(sel, resultEl).textContent.trim().replace(/\s+/g, " ") : "");

    const read = () => {
      if (!resultEl || !resultEl.children.length) return null;
      const dec = $(".decision", resultEl);
      const conf = $(".badge[class*='conf-']", resultEl);
      const days = $$(".strip-day", resultEl).map((d) => ({
        title: $("h3", d).textContent.trim(),
        slots: $$(".slot", d).map((s) => {
          const m = /^(.*?): AQI (\d+) \((.+)\)$/.exec(s.getAttribute("title") || "");
          return m ? { time: m[1], aqi: +m[2], cat: m[3] } : null;
        }).filter(Boolean),
      }));
      return {
        at: Date.now(),
        place: txt(".meta"),
        aqi: txt(".aqi-num"),
        cat: txt(".aqi-head .pill"),
        verdict: txt(".decision .verdict"),
        state: dec ? (["yes", "limit", "no"].find((k) => dec.classList.contains(k)) || "") : "",
        windowLine: txt(".decision .window"),
        conf: conf ? (conf.className.match(/conf-(\w+)/) || [])[1] || "" : "",
        source: txt(".kv p"),
        days,
      };
    };

    const ago = (t) => { const m = Math.round((Date.now() - t) / 60000); return m < 1 ? "just now" : m < 60 ? `${m} min ago` : `${Math.round(m / 60)} h ago`; };

    const paint = (d) => {
      if (live) {
        const set = (k, main, sub) => { $(`[data-live-${k}]`, live).innerHTML = main; $(`[data-live-${k}-sub]`, live).textContent = sub; };
        if (d && d.aqi) {
          set("aqi", `<span class="pill-dot ${cls(d.cat)}"></span>${esc(d.aqi)}`, `${d.cat} · ${d.place || "your check"} · ${ago(d.at)}`);
          set("verdict", esc(d.verdict || "—"), d.windowLine || "");
          set("conf", esc(d.conf ? d.conf[0].toUpperCase() + d.conf.slice(1) : "—"), d.source || "");
        } else {
          set("aqi", "—", "No check yet in this session.");
          set("verdict", "—", "Run a check to fill this in.");
          set("conf", "—", "Shown with every result.");
        }
      }
      if (statusEl) {
        const lede = $("[data-status-lede]");
        const slots = d && d.days ? d.days.flatMap((day) => day.slots.map((s) => ({ ...s, day: day.title }))) : [];
        if (d && slots.length) {
          lede.textContent = `From your check${d.place ? ` for ${d.place}` : ""}, ${ago(d.at)}. Each row is a 3-hour forecast slot.`;
          statusEl.innerHTML = `<ul class="status-rows">${slots.map((s) => `<li>
              <span class="st-time"><b>${esc(s.time)}</b><span>${esc(s.day)}</span></span>
              <span class="st-aqi">${esc(s.aqi)}</span>
              <span class="pill ${cls(s.cat)}">${esc(s.cat)}</span></li>`).join("")}</ul>`;
        } else {
          lede.textContent = "No check yet in this session. Until then, here's the CPCB scale the app uses for every reading.";
          statusEl.innerHTML = `<ul class="status-rows">${CPCB.map(([c, r, v]) => `<li>
              <span class="st-time"><b>${c}</b><span>AQI ${r}</span></span>
              <span class="st-call">${v}</span>
              <span class="pill ${cls(c)}">${c}</span></li>`).join("")}</ul>
            <a class="btn primary btn-auto status-cta" href="#check">Check your place</a>`;
        }
      }
    };

    let saved = null;
    try { saved = JSON.parse(store.get("sessionStorage", "hb-latest") || "null"); } catch (_) { saved = null; }
    paint(saved);
    if (resultEl) {
      new MutationObserver(() => {
        const d = read();
        if (d && d.aqi) { store.set("sessionStorage", "hb-latest", JSON.stringify(d)); paint(d); }
      }).observe(resultEl, { childList: true });
    }
  }

  // --- About the data modal ----------------------------------------------------------------
  const dialog = $("#about-data");
  if (dialog) {
    let opener = null;
    const open = (e) => {
      opener = e.currentTarget;
      if (typeof dialog.showModal === "function") dialog.showModal(); else dialog.setAttribute("open", "");
    };
    const close = () => { if (typeof dialog.close === "function") dialog.close(); else dialog.removeAttribute("open"); };
    $$("[data-open-about]").forEach((b) => b.addEventListener("click", open));
    $("[data-close-about]", dialog).addEventListener("click", close);
    dialog.addEventListener("click", (e) => { if (e.target === dialog) close(); });  // backdrop click
    dialog.addEventListener("close", () => { if (opener) opener.focus(); });
  }

  // --- Reveal on scroll ----------------------------------------------------------------------
  const items = $$(".reveal");
  if (!("IntersectionObserver" in window) || reduceMotion) {
    items.forEach((el) => el.classList.add("in"));
  } else {
    const io = new IntersectionObserver((entries) => entries.forEach((en) => {
      if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
    }), { rootMargin: "0px 0px -8% 0px" });
    items.forEach((el) => io.observe(el));
  }
})();
