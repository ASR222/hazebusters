// Screens and flow: input -> progress (create, upload, analyse) -> result.
(function () {
  const $ = (sel) => document.querySelector(sel);
  const screens = { input: $("#screen-input"), progress: $("#screen-progress"), result: $("#screen-result") };
  let coords = null;     // {lat, lon} from geolocation
  let lastJob = null;    // inputs of the last submit, for Retry

  function show(name) {
    Object.entries(screens).forEach(([k, el]) => { el.hidden = k !== name; });
    window.scrollTo(0, 0);
  }

  // --- Input ---------------------------------------------------------------

  $("#btn-locate").addEventListener("click", () => {
    const status = $("#loc-status");
    if (!navigator.geolocation) {
      status.textContent = "Location isn't available here. Pick a city below.";
      return;
    }
    status.textContent = "Finding you…";
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        coords = { lat: +pos.coords.latitude.toFixed(5), lon: +pos.coords.longitude.toFixed(5) };
        $("#city").value = "";
        status.textContent = `Using your location (${coords.lat.toFixed(3)}, ${coords.lon.toFixed(3)}, ±${Math.round(pos.coords.accuracy)} m).`;
      },
      (err) => {
        coords = null;
        status.textContent = (err.code === err.PERMISSION_DENIED ? "Location permission denied." : "Couldn't get your location.")
          + " Pick a city below.";
      },
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 },
    );
  });

  $("#city").addEventListener("change", (e) => {
    if (e.target.value) {
      coords = null;
      $("#loc-status").textContent = "";
    }
  });

  $("#video").addEventListener("change", (e) => {
    const file = e.target.files[0];
    $("#video-label").textContent = file ? `${file.name} (${(file.size / 1e6).toFixed(1)} MB)` : "Record or choose a clip";
  });

  function pickedLocation() {
    if (coords) return coords;
    const v = $("#city").value;
    if (!v) return null;
    const [lat, lon] = v.split(",").map(Number);
    return { lat, lon };
  }

  function formError(msg) {
    const el = $("#form-error");
    el.textContent = msg || "";
    el.hidden = !msg;
  }

  $("#job-form").addEventListener("submit", (e) => {
    e.preventDefault();
    formError("");
    const loc = pickedLocation();
    const file = $("#video").files[0];
    if (!loc) return formError("Allow location or pick a city.");
    if (!file) return formError("Record or choose a video.");
    const type = window.api.contentType(file);
    if (!type) return formError("Unsupported video type. Use MP4, WebM or MOV.");
    const profile = document.querySelector('input[name="profile"]:checked').value;
    lastJob = { lat: loc.lat, lon: loc.lon, profile, file, type };
    run(lastJob);
  });

  // --- Progress ------------------------------------------------------------

  function step(name, state) {
    const li = document.querySelector(`.steps [data-step="${name}"]`);
    li.classList.remove("active", "done", "failed");
    if (state) li.classList.add(state);
  }

  function resetSteps() {
    ["create", "upload", "analyse", "done"].forEach((s) => step(s, null));
    $("#upload-bar").value = 0;
    $("#upload-pct").textContent = "";
    $("#progress-error").hidden = true;
  }

  function friendly(err) {
    if (err instanceof TypeError) return "Network error. Check your connection and try again.";
    return err.message || "Something went wrong.";
  }

  async function run(job) {
    show("progress");
    resetSteps();
    let current = "create";
    try {
      step("create", "active");
      const { job_id, upload_url } = await window.api.createJob({
        lat: job.lat, lon: job.lon, profile: job.profile, content_type: job.type,
      });
      step("create", "done");

      current = "upload";
      step("upload", "active");
      await window.api.upload(upload_url, job.file, job.type, (f) => {
        $("#upload-bar").value = Math.round(f * 100);
        $("#upload-pct").textContent = `${Math.round(f * 100)}%`;
      });
      step("upload", "done");

      current = "analyse";
      step("analyse", "active");
      const body = await window.api.poll(job_id, () => {});
      step("analyse", "done");
      step("done", "done");
      showResult(body);
    } catch (err) {
      step(current, "failed");
      $("#progress-error-msg").textContent = friendly(err);
      $("#progress-error").hidden = false;
    }
  }

  $("#btn-retry").addEventListener("click", () => { if (lastJob) run(lastJob); });

  document.querySelectorAll(".js-restart").forEach((b) => b.addEventListener("click", () => {
    if (new URLSearchParams(window.location.search).has("mock")) {
      window.location.href = window.location.pathname;
      return;
    }
    show("input");
  }));

  // --- Result --------------------------------------------------------------

  function showResult(body) {
    window.renderResult($("#result"), body);
    show("result");
  }

  async function loadMock() {
    show("progress");
    resetSteps();
    step("analyse", "active");
    try {
      const res = await fetch("mock/result.json", { cache: "no-store" });
      if (!res.ok) throw new Error(`mock/result.json: ${res.status}`);
      showResult(await res.json());
    } catch (err) {
      step("analyse", "failed");
      $("#progress-error-msg").textContent = `Couldn't load the mock result (${friendly(err)}).`;
      $("#progress-error").hidden = false;
      $("#btn-retry").onclick = loadMock;
    }
  }

  if (new URLSearchParams(window.location.search).get("mock") === "1") loadMock();
})();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}
