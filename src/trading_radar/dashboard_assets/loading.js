/* The private page stays small; one authenticated, complete snapshot follows. */
const radarLoading = (() => {
  "use strict";
  async function load(data, place, transport = fetch, timeoutMs = 180000) {
    const editing = data?.editing;
    if (data?.status !== "loading" || data?.live !== true || data?.format_version !== 1 ||
        editing?.enabled !== true || editing?.mode !== "private" ||
        place?.protocol !== "https:" || editing.origin !== place.origin ||
        !/^[a-f0-9]{64}$/.test(editing.token || "") ||
        !/^\/[A-Za-z0-9_-]{32,128}\/api\/applications$/.test(editing.api_base || "") ||
        ![editing.api_base.replace(/api\/applications$/, ""),
          editing.api_base.replace(/api\/applications$/, "index.html")].includes(place.pathname)) {
      throw new Error("invalid_private_snapshot");
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await transport(editing.api_base.replace(/applications$/, "snapshot"), {
        headers: {"X-Radar-Token": editing.token}, credentials: "same-origin",
        cache: "no-store", redirect: "error", referrerPolicy: "no-referrer",
        signal: controller.signal
      });
      if (!response.ok || response.redirected ||
          response.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") {
        throw new Error("snapshot_unavailable");
      }
      const snapshot = await response.json();
      if (!snapshot || snapshot.status !== "ok" || snapshot.format_version !== 1 ||
          !Array.isArray(snapshot.jobs) || snapshot.jobs.length > 5000) {
        throw new Error("snapshot_unavailable");
      }
      const ids = snapshot.jobs.map((job) => job?.id);
      if (ids.some((id) => typeof id !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(id)) ||
          new Set(ids).size !== ids.length) throw new Error("snapshot_unavailable");
      // The page establishes the session; data cannot replace its credentials.
      return {...snapshot, live: true, editing};
    } finally { clearTimeout(timer); }
  }
  return {load};
})();
if (typeof module !== "undefined" && module.exports) module.exports = radarLoading;
