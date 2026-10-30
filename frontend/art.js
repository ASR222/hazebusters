// Original SVG scene art for image slots that don't have a licensed photo yet (see credits.js / IMAGES.md).
// window.hbArt(kind) -> SVG markup string. Deterministic (seeded) so scenes look the same every load.
(function () {
  const W = 400, H = 260;

  function rng(seed) {
    let s = 0;
    for (const ch of seed) s = (s * 31 + ch.charCodeAt(0)) >>> 0;
    return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  }

  const SKIES = {
    clear: ["#7cc8f0", "#cdeff3", "#e8f8ef"],
    hazy: ["#b9b3a2", "#d8d0bd", "#e6dfcc"],
    smog: ["#9c8f78", "#c4b394", "#d9c9a6"],
    dusk: ["#f2a36b", "#f7cf9a", "#efe2c2"],
    night: ["#06140f", "#0b2a20", "#123a2c"],
    dawn: ["#9fd9c8", "#e0f5ea", "#f6f3e3"],
  };

  const sky = (id, k) => {
    const [a, b, c] = SKIES[k];
    return `<defs><linearGradient id="sky-${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${a}"/><stop offset=".6" stop-color="${b}"/><stop offset="1" stop-color="${c}"/></linearGradient>
      <filter id="blur-${id}"><feGaussianBlur stdDeviation="6"/></filter>
      <filter id="blur2-${id}"><feGaussianBlur stdDeviation="14"/></filter></defs>
      <rect width="${W}" height="${H}" fill="url(#sky-${id})"/>`;
  };
  const sun = (id, x, y, r, col, soft) =>
    `<circle cx="${x}" cy="${y}" r="${r}" fill="${col}" ${soft ? `filter="url(#blur-${id})" opacity=".85"` : ""}/>`;
  const hills = (y, amp, col, phase = 0) => {
    let d = `M0 ${H} L0 ${y}`;
    for (let x = 0; x <= W; x += 20) d += ` L${x} ${(y + Math.sin(x / 60 + phase) * amp).toFixed(1)}`;
    return `<path d="${d} L${W} ${H}Z" fill="${col}"/>`;
  };
  const skyline = (r, base, col, n = 16, hMax = 110) => {
    let out = "", x = -10;
    for (let i = 0; i < n && x < W; i++) {
      const w = 18 + r() * 26, h = 30 + r() * hMax;
      out += `<rect x="${x.toFixed(1)}" y="${(base - h).toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" fill="${col}"/>`;
      if (r() > .7) out += `<rect x="${(x + w / 2 - 1).toFixed(1)}" y="${(base - h - 14).toFixed(1)}" width="2" height="14" fill="${col}"/>`;
      x += w + 2 + r() * 6;
    }
    return out + `<rect x="0" y="${base}" width="${W}" height="${H - base}" fill="${col}"/>`;
  };
  const haze = (id, op, col = "#e9e1cc") =>
    `<rect y="60" width="${W}" height="${H}" fill="${col}" opacity="${op}" filter="url(#blur2-${id})"/>`;
  const tree = (x, y, s, col) =>
    `<rect x="${x - 2 * s}" y="${y - 6 * s}" width="${4 * s}" height="${12 * s}" fill="#3b2a1d"/>
     <circle cx="${x}" cy="${y - 14 * s}" r="${12 * s}" fill="${col}"/><circle cx="${x - 8 * s}" cy="${y - 8 * s}" r="${8 * s}" fill="${col}"/><circle cx="${x + 8 * s}" cy="${y - 8 * s}" r="${8 * s}" fill="${col}"/>`;
  const pine = (x, y, s, col) =>
    `<path d="M${x} ${y - 40 * s} L${x - 14 * s} ${y} L${x + 14 * s} ${y}Z" fill="${col}"/><rect x="${x - 2 * s}" y="${y}" width="${4 * s}" height="${8 * s}" fill="#2e2117"/>`;
  const plume = (id, x, y, n, col, r0 = 10) => {
    let out = "";
    for (let i = 0; i < n; i++) out += `<circle cx="${x + i * 9}" cy="${y - i * 16}" r="${r0 + i * 5}" fill="${col}" opacity="${(0.8 - i * 0.1).toFixed(2)}"/>`;
    return `<g filter="url(#blur-${id})">${out}</g>`;
  };
  const car = (x, y, col) =>
    `<rect x="${x}" y="${y - 14}" width="44" height="14" rx="4" fill="${col}"/><path d="M${x + 8} ${y - 14} l6 -9 h16 l6 9z" fill="${col}"/>
     <circle cx="${x + 10}" cy="${y}" r="5" fill="#1d1d1d"/><circle cx="${x + 34}" cy="${y}" r="5" fill="#1d1d1d"/>
     <circle cx="${x + 2}" cy="${y - 8}" r="2.5" fill="#ffd27a"/>`;
  const person = (x, y, s, col, mask) =>
    `<circle cx="${x}" cy="${y - 46 * s}" r="${9 * s}" fill="${col}"/><path d="M${x - 13 * s} ${y} v${-24 * s} q0 ${-12 * s} ${13 * s} ${-12 * s} q${13 * s} 0 ${13 * s} ${12 * s} v${24 * s}z" fill="${col}"/>
     ${mask ? `<rect x="${x - 7 * s}" y="${y - 45 * s}" width="${14 * s}" height="${7 * s}" rx="${3 * s}" fill="#f4faf6"/>` : ""}`;

  const SCENES = {
    "skyline-clear": (id, r) => sky(id, "clear") + sun(id, 320, 60, 22, "#fff6c9") + hills(190, 8, "#9dd9b5") + skyline(r, 210, "#2f6b57") + hills(232, 5, "#1f5a44", 1),
    "skyline-haze": (id, r) => sky(id, "hazy") + sun(id, 300, 80, 26, "#f6e7c1", true) + skyline(r, 205, "#8d8371") + haze(id, .55) + skyline(r, 225, "#5e5648", 12, 70) + haze(id, .25),
    "smog-night": (id, r) => sky(id, "smog") + sun(id, 90, 70, 18, "#ffd9a0", true) + skyline(r, 200, "#6f6352", 18, 120) + haze(id, .6, "#d7c7a5") + skyline(r, 228, "#3f382e", 14, 60),
    traffic: (id, r) => sky(id, "hazy") + sun(id, 330, 70, 20, "#f5e3b8", true) + skyline(r, 170, "#9a9080", 14, 70) + haze(id, .45)
      + `<rect y="200" width="${W}" height="60" fill="#4a4a46"/><rect y="226" width="${W}" height="3" fill="#e8e1c9" stroke-dasharray="18 14" stroke="#e8e1c9"/>`
      + car(30, 222, "#c0533a") + car(110, 222, "#2f6b57") + car(190, 222, "#d9a441") + car(270, 222, "#5a6f8c") + car(60, 252, "#8a8f94") + car(160, 252, "#a64f6a") + car(250, 252, "#3d5a4b")
      + plume(id, 20, 214, 3, "#8f877a", 6) + plume(id, 100, 214, 3, "#8f877a", 6) + plume(id, 180, 214, 3, "#8f877a", 6),
    factory: (id, r) => sky(id, "smog") + hills(200, 6, "#8c8270")
      + `<rect x="60" y="150" width="200" height="70" fill="#4d463b"/><path d="M60 150 l40 -20 v20 l40 -20 v20 l40 -20 v20 l40 -20 v20z" fill="#4d463b"/>`
      + `<rect x="270" y="80" width="18" height="140" fill="#5c5446"/><rect x="300" y="100" width="16" height="120" fill="#5c5446"/>`
      + plume(id, 279, 76, 6, "#8a8070", 12) + plume(id, 308, 96, 5, "#9b9180", 10) + `<rect y="220" width="${W}" height="40" fill="#3a352c"/>` + haze(id, .3),
    "crop-fire": (id, r) => sky(id, "dusk") + sun(id, 300, 90, 24, "#ffe2a8", true) + hills(170, 4, "#b08a4c")
      + Array.from({ length: 9 }, (_, i) => `<path d="M0 ${180 + i * 10} Q200 ${176 + i * 10} 400 ${182 + i * 10}" stroke="#8a6a35" stroke-width="2" fill="none"/>`).join("")
      + `<path d="M120 200 q8 -26 16 -6 q6 -22 14 -2 q8 -18 12 2z" fill="#f08a2c"/><path d="M128 200 q6 -14 10 -2 q6 -12 10 2z" fill="#ffd166"/>`
      + `<path d="M220 214 q8 -22 14 -4 q6 -18 12 0z" fill="#f08a2c"/>` + plume(id, 140, 180, 7, "#6d6255", 16) + plume(id, 236, 196, 6, "#7c7062", 12) + haze(id, .25, "#d6c09a"),
    forest: (id, r) => sky(id, "dawn") + sun(id, 300, 70, 20, "#fffbe0") + hills(170, 10, "#7fcf9f") + hills(195, 8, "#3f9a6c", 2)
      + Array.from({ length: 14 }, (_, i) => pine(15 + i * 29 + r() * 8, 215 + r() * 10, .8 + r() * .5, i % 2 ? "#1f6b4a" : "#0f553a")).join("")
      + `<rect y="232" width="${W}" height="28" fill="#0b3d2e"/>`,
    park: (id, r) => sky(id, "clear") + sun(id, 80, 60, 20, "#fff6c9") + hills(185, 10, "#8ad5a9") + `<rect y="210" width="${W}" height="50" fill="#4fae7a"/>`
      + tree(70, 214, 1.3, "#1f7a52") + tree(330, 214, 1.5, "#22895b") + tree(250, 210, 1, "#2c9c69")
      + person(150, 232, .7, "#0b3d2e") + person(185, 232, .55, "#1c5a45") + person(205, 232, .5, "#2b6e55"),
    station: (id, r) => sky(id, "clear") + hills(200, 6, "#9dd9b5") + skyline(r, 215, "#8fbfa9", 14, 50)
      + `<rect x="196" y="90" width="8" height="140" fill="#3c4a44"/><rect x="170" y="100" width="60" height="40" rx="6" fill="#f4faf6" stroke="#0b3d2e" stroke-width="3"/>`
      + `<rect x="180" y="110" width="40" height="8" rx="3" fill="#10b981"/><rect x="180" y="124" width="26" height="6" rx="3" fill="#0b3d2e"/>`
      + `<path d="M200 90 v-24" stroke="#3c4a44" stroke-width="3"/><circle cx="200" cy="64" r="5" fill="#10b981"/>`
      + `<path d="M180 54 a28 28 0 0 1 40 0 M172 44 a40 40 0 0 1 56 0" stroke="#10b981" stroke-width="3" fill="none" opacity=".7"/>`
      + `<rect y="230" width="${W}" height="30" fill="#2f6b57"/>`,
    satellite: (id, r) => sky(id, "night") + Array.from({ length: 40 }, () => `<circle cx="${(r() * W).toFixed(0)}" cy="${(r() * 160).toFixed(0)}" r="${(r() * 1.4 + .3).toFixed(1)}" fill="#d1fae5" opacity="${(r() * .7 + .3).toFixed(2)}"/>`).join("")
      + `<circle cx="200" cy="560" r="380" fill="#0f5a40"/><circle cx="200" cy="560" r="380" fill="none" stroke="#34d399" stroke-width="3" opacity=".5"/>`
      + `<g transform="translate(250 80) rotate(-18)"><rect x="-14" y="-10" width="28" height="20" rx="3" fill="#d1fae5"/><rect x="-64" y="-8" width="44" height="16" fill="#10b981"/><rect x="20" y="-8" width="44" height="16" fill="#10b981"/>
        <path d="M-64 0 h128" stroke="#0b3d2e" stroke-width="1"/><path d="M0 10 v10" stroke="#d1fae5" stroke-width="2"/></g>
        <path d="M250 104 L170 210 L330 210Z" fill="#34d399" opacity=".12"/>`,
    mask: (id, r) => sky(id, "hazy") + skyline(r, 200, "#a39886", 14, 70) + haze(id, .5)
      + person(140, 260, 1.6, "#2e3b35", true) + person(250, 262, 1.3, "#46524c", true) + person(330, 262, 1.1, "#5c6862", true),
    school: (id, r) => sky(id, "clear") + sun(id, 340, 50, 18, "#fff6c9")
      + `<rect x="90" y="120" width="220" height="100" fill="#f1e6d0"/><path d="M80 122 L200 70 L320 122Z" fill="#b4473c"/>`
      + Array.from({ length: 6 }, (_, i) => `<rect x="${108 + i * 32}" y="140" width="18" height="22" fill="#7cc8f0" stroke="#5a4a36" stroke-width="2"/>`).join("")
      + `<rect x="186" y="180" width="28" height="40" fill="#6b4a2f"/><path d="M200 70 v-34" stroke="#3c3c3c" stroke-width="2"/><rect x="200" y="36" width="22" height="14" fill="#10b981"/>`
      + `<rect y="220" width="${W}" height="40" fill="#79c99b"/>` + person(60, 248, .55, "#0b3d2e") + person(340, 248, .5, "#1f5a44") + person(360, 248, .45, "#2f6b57"),
    river: (id, r) => sky(id, "dawn") + sun(id, 200, 110, 26, "#fff3c4", true) + hills(150, 12, "#8fd1ae") + hills(170, 8, "#4ea57a", 1.4)
      + `<path d="M0 260 C120 210 160 200 200 186 C240 200 290 220 400 260Z" fill="#7cc8e0"/><path d="M180 200 C200 196 220 200 230 206" stroke="#f4faf6" stroke-width="2" fill="none"/>`
      + tree(50, 214, 1.2, "#1f7a52") + tree(360, 220, 1.4, "#1a6a47"),
  };

  window.hbArt = function (kind) {
    const make = SCENES[kind] || SCENES["skyline-clear"];
    const id = kind.replace(/[^a-z]/g, "") + Math.floor(Math.random() * 1e6);  // unique ids per instance
    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" role="presentation" focusable="false">${make(id, rng(kind))}</svg>`;
  };
})();
