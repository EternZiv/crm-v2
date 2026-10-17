function finloMultiSort(event, anchor) {
  event.preventDefault();

  const field = anchor.dataset.sortField;
  const mainUrl = anchor.dataset.mainUrl || "";
  const searchUrl = anchor.dataset.searchUrl || mainUrl;
  const sortingTarget = anchor.dataset.sortTarget;
  const viewId = anchor.dataset.viewId;

  const searchUrlParts = searchUrl.split("?");
  const mainUrlParts = mainUrl.split("?");
  const params = new URLSearchParams(mainUrlParts[1] || "");

  new URLSearchParams(searchUrlParts[1] || "").forEach(function (value, key) {
    params.set(key, value);
  });
  new URLSearchParams(window.location.search).forEach(function (value, key) {
    params.set(key, value);
  });

  const currentSortKeys = anchor.dataset.sortKeys || "";
  const pairs = [];
  if (currentSortKeys) {
    currentSortKeys.split(",").forEach(function (token) {
      token = token.trim();
      if (!token) return;
      const idx = token.lastIndexOf(":");
      if (idx > 0) {
        pairs.push({ field: token.substring(0, idx), dir: token.substring(idx + 1) });
      } else {
        pairs.push({ field: token, dir: "asc" });
      }
    });
  }

  const existingIdx = pairs.findIndex(function (pair) {
    return pair.field === field;
  });

  if (event.shiftKey) {
    if (existingIdx === -1) {
      pairs.push({ field: field, dir: "asc" });
    } else if (pairs[existingIdx].dir === "asc") {
      pairs[existingIdx].dir = "desc";
    } else {
      pairs.splice(existingIdx, 1);
    }
  } else if (existingIdx === -1 || pairs.length > 1) {
    pairs.splice(0, pairs.length, { field: field, dir: "asc" });
  } else if (pairs[0].dir === "asc") {
    pairs.splice(0, pairs.length, { field: field, dir: "desc" });
  } else {
    pairs.splice(0, pairs.length);
  }

  params.delete("sort");
  params.delete("direction");
  params.delete("sort_keys");
  if (pairs.length > 0) {
    params.set(
      "sort_keys",
      pairs.map(function (pair) {
        return pair.field + ":" + pair.dir;
      }).join(",")
    );
  }

  const query = params.toString();
  const url = searchUrlParts[0] + (query ? "?" + query : "");
  const target = sortingTarget || "#" + viewId;

  htmx.ajax("GET", url, {
    target: target,
    select: target,
    swap: "outerHTML",
  });
}
