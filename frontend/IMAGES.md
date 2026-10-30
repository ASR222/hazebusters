# Images

Photo sites (Unsplash, Pexels, Pixabay, Wikimedia Commons) were not reachable from the environment that built this UI, so every slot currently shows original SVG art from `art.js`. Nothing is broken meanwhile: a slot only switches to a photo once you fill in its entry in `credits.js`.

## Add a photo

1. Download a free-to-use photo from Unsplash, Pexels, Pixabay or Wikimedia Commons (check the licence; avoid photos of identifiable public figures).
2. Resize and convert to WebP, about 200 KB:
   - hero: 1920×1080 (landscape), quality ~70
   - gallery: 960×720 (4:3), quality ~70
   ```bash
   python -c "from PIL import Image; im=Image.open('in.jpg').convert('RGB'); im.thumbnail((1920,1080)); im.save('img/hero-2-winter-haze.webp', quality=70)"
   ```
3. Save it in `frontend/img/` with the file name below.
4. In `credits.js`, set `file` (e.g. `"img/hero-2-winter-haze.webp"`), `credit` (photographer), `source` (site) and `license`.
5. Bump `CACHE_VERSION` in `sw.js` before deploying.

## Slots

| Slot | File name | Search keywords | Size | Alt text |
|---|---|---|---|---|
| Hero 1: A clear day | `bg/bg.webp (already in the repo)` | clear sky city skyline | 1920×1080 | Clear blue sky with clouds over a flower meadow |
| Hero 2: Winter haze over the city | `img/hero-2-winter-haze-over-the-city.webp` | hazy city skyline, smog India city | 1920×1080 | City skyline fading into thick winter haze |
| Hero 3: Rush-hour traffic | `img/hero-3-rush-hour-traffic.webp` | traffic pollution India, vehicle exhaust | 1920×1080 | Rush-hour traffic under a hazy sky |
| Hero 4: Crop-residue burning | `img/hero-4-crop-residue-burning.webp` | stubble burning Punjab, crop residue burning | 1920×1080 | Smoke rising from crop-residue burning in a field at dusk |
| Hero 5: Clean air over a forest | `img/hero-5-clean-air-over-a-forest.webp` | forest clean air, green forest morning | 1920×1080 | Green forest under a clean morning sky |
| Hero 6: An air-quality monitor | `img/hero-6-an-air-quality-monitor.webp` | air quality monitoring station | 1920×1080 | Air-quality monitoring station with sensors on a pole |
| Gallery 1: Haze hides the skyline | `img/gallery-01-haze-hides-the-skyline.webp` | hazy city skyline, smog India city | 960×720 | Hazy city skyline |
| Gallery 2: Where a measured AQI comes from | `img/gallery-02-where-a-measured-aqi-comes-from.webp` | air quality monitoring station | 960×720 | Monitoring station sensors |
| Gallery 3: Models like CAMS use satellite data | `img/gallery-03-models-like-cams-use-satellite-data.webp` | Sentinel satellite, Earth from space | 960×720 | Satellite over Earth at night |
| Gallery 4: Vehicle exhaust | `img/gallery-04-vehicle-exhaust.webp` | traffic pollution India, vehicle exhaust | 960×720 | Traffic emissions on a busy road |
| Gallery 5: Industrial smoke | `img/gallery-05-industrial-smoke.webp` | factory chimney smoke | 960×720 | Factory chimneys releasing smoke |
| Gallery 6: Biomass burning | `img/gallery-06-biomass-burning.webp` | stubble burning Punjab, crop residue burning | 960×720 | Crop-residue fire in a field |
| Gallery 7: Living with bad-air days | `img/gallery-07-living-with-bad-air-days.webp` | people wearing masks smog | 960×720 | People wearing masks on a hazy street |
| Gallery 8: Can PE be outdoors today? | `img/gallery-08-can-pe-be-outdoors-today.webp` | school children outdoors India | 960×720 | School building with children outside |
| Gallery 9: Smog on a still evening | `img/gallery-09-smog-on-a-still-evening.webp` | Delhi smog, dense smog city | 960×720 | Dense smog over a city |
| Gallery 10: The best window to go out | `img/gallery-10-the-best-window-to-go-out.webp` | family in park green | 960×720 | Family in a green park |
| Gallery 11: Trees and cleaner air | `img/gallery-11-trees-and-cleaner-air.webp` | forest clean air, green forest morning | 960×720 | Pine forest at dawn |
| Gallery 12: A clear-sky day | `img/gallery-12-a-clear-sky-day.webp` | river valley clear sky | 960×720 | River valley under a clear sky |

The before/after slider uses `bg/bg.webp` on both sides; the hazy side is a CSS filter (labelled as an illustration on the page).
