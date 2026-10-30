// Every image slot on the landing page, with caption and credit, in one place.
// To use a real photo: save it as WebP in img/ (see IMAGES.md), then set `file`, `credit`, `source` and `license`.
// Slots with an empty `file` show the original SVG scene named in `art` (art.js), so nothing breaks meanwhile.
window.HB_CREDITS = {
  hero: [
    { file: "bg/bg.webp", art: "skyline-clear", alt: "Clear blue sky with clouds over a flower meadow",
      caption: "A clear day", credit: "HazeBusters project background", source: "", license: "Project asset" },
    { file: "", art: "skyline-haze", alt: "City skyline fading into thick winter haze",
      caption: "Winter haze over the city", credit: "", source: "", license: "" },
    { file: "", art: "traffic", alt: "Rush-hour traffic under a hazy sky",
      caption: "Rush-hour traffic", credit: "", source: "", license: "" },
    { file: "", art: "crop-fire", alt: "Smoke rising from crop-residue burning in a field at dusk",
      caption: "Crop-residue burning", credit: "", source: "", license: "" },
    { file: "", art: "forest", alt: "Green forest under a clean morning sky",
      caption: "Clean air over a forest", credit: "", source: "", license: "" },
    { file: "", art: "station", alt: "Air-quality monitoring station with sensors on a pole",
      caption: "An air-quality monitor", credit: "", source: "", license: "" },
  ],
  gallery: [
    { file: "", art: "skyline-haze", alt: "Hazy city skyline", caption: "Haze hides the skyline", credit: "", source: "", license: "" },
    { file: "", art: "station", alt: "Monitoring station sensors", caption: "Where a measured AQI comes from", credit: "", source: "", license: "" },
    { file: "", art: "satellite", alt: "Satellite over Earth at night", caption: "Models like CAMS use satellite data", credit: "", source: "", license: "" },
    { file: "", art: "traffic", alt: "Traffic emissions on a busy road", caption: "Vehicle exhaust", credit: "", source: "", license: "" },
    { file: "", art: "factory", alt: "Factory chimneys releasing smoke", caption: "Industrial smoke", credit: "", source: "", license: "" },
    { file: "", art: "crop-fire", alt: "Crop-residue fire in a field", caption: "Biomass burning", credit: "", source: "", license: "" },
    { file: "", art: "mask", alt: "People wearing masks on a hazy street", caption: "Living with bad-air days", credit: "", source: "", license: "" },
    { file: "", art: "school", alt: "School building with children outside", caption: "Can PE be outdoors today?", credit: "", source: "", license: "" },
    { file: "", art: "smog-night", alt: "Dense smog over a city", caption: "Smog on a still evening", credit: "", source: "", license: "" },
    { file: "", art: "park", alt: "Family in a green park", caption: "The best window to go out", credit: "", source: "", license: "" },
    { file: "", art: "forest", alt: "Pine forest at dawn", caption: "Trees and cleaner air", credit: "", source: "", license: "" },
    { file: "", art: "river", alt: "River valley under a clear sky", caption: "A clear-sky day", credit: "", source: "", license: "" },
  ],
};
