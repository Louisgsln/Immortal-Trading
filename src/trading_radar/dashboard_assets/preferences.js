const radarPreferences = (() => {
  "use strict";
  const key = "radar-consultation-v1";
  const fields = ["search","company","programme","programme-year","country","duration","start-from","start-to","score","active","application-status","experience","education","publication-from","publication-to","sort"];
  function normalize(value, options) {
    const result = {};
    if (!value || typeof value !== "object" || Array.isArray(value)) return result;
    for (const field of fields) {
      const item = value[field];
      if (typeof item !== "string" || item.length > 500) continue;
      if (field === "search") {result[field] = item; continue;}
      if (field.startsWith("start-") || field.startsWith("publication-")) {
        if (item === "" || (/^\d{4}-\d{2}-\d{2}$/.test(item) && Number.isFinite(Date.parse(item)) && new Date(item).toISOString().slice(0,10) === item)) result[field] = item;
      } else if (options[field]?.includes(item)) result[field] = item;
    }
    for (const prefix of ["start","publication"]) {
      if (result[prefix + "-from"] && result[prefix + "-to"] && result[prefix + "-from"] > result[prefix + "-to"]) {
        delete result[prefix + "-from"]; delete result[prefix + "-to"];
      }
    }
    return result;
  }
  function views(value, options) {
    return Object.fromEntries(["jobs","applications"].filter((view) => Object.hasOwn(value || {},view)).map((view) => [view,normalize(value[view],options)]));
  }
  function load(storage, options) {
    try {
      const raw = storage.getItem(key);
      if (raw === null) return {status:"empty",views:{}};
      if (raw.length > 10000) return {status:"invalid",views:{}};
      const value = JSON.parse(raw);
      if (value?.version !== 1 || !value.views || typeof value.views !== "object" || Array.isArray(value.views)) return {status:"invalid",views:{}};
      return {status:"ok",views:views(value.views,options)};
    } catch (_) {return {status:"unavailable",views:{}};}
  }
  function save(storage, value, options) {
    try {storage.setItem(key,JSON.stringify({version:1,views:views(value,options)})); return true;}
    catch (_) {return false;}
  }
  function clear(storage) {
    try {storage.removeItem(key); return true;} catch (_) {return false;}
  }
  return {fields,load,save,clear};
})();
if (typeof module !== "undefined" && module.exports) module.exports = radarPreferences;
