"use strict";
(() => {
  const data = document.getElementById("library-data");
  if (!data) return;
  const {entries, categories} = JSON.parse(data.textContent);
  const query = new URLSearchParams(location.search);
  const get = (key) => (query.get(key) || "").slice(0, 200).trim();
  const scope = ["learn", "archive", "all"].includes(get("scope")) ? get("scope") : "learn";
  const category = categories.includes(get("category")) ? get("category") : "";
  const siteSelect = document.getElementById("library-site");
  const site = siteSelect && entries.some((item) => item.site === get("site")) ? get("site") : "";
  const text = get("q");
  const params = {q: text, scope, category, site};
  const tokens = text.toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const matching = entries.filter((item) => (!site || item.site === site) && tokens.every((token) => item.search.toLocaleLowerCase().includes(token)));
  const scoped = matching.filter((item) => scope === "all" || item.archived === (scope === "archive"));
  const filtered = scoped.filter((item) => !category || item.category === category)
    .sort((a, b) => Number(a.archived) - Number(b.archived) || a.rank - b.rank || Number(a.advanced) - Number(b.advanced));
  const pages = Math.max(1, Math.ceil(filtered.length / 12));
  const rawPage = (query.get("page") || "1").slice(0, 8);
  const page = Math.min(pages, Math.max(1, /^\d+$/.test(rawPage) ? Number(rawPage) : 1));
  const node = (tag, textContent, className = "") => {
    const result = document.createElement(tag);
    result.textContent = textContent;
    if (className) result.className = className;
    return result;
  };
  const url = (changes = {}, anchor = "") => {
    const values = {...params, ...changes};
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(values)) {
      if (value && !(key === "scope" && value === "learn") && !(key === "page" && String(value) === "1")) search.set(key, value);
    }
    return location.pathname + (search.size ? `?${search}` : "") + anchor;
  };
  const link = (label, changes, current = false, count = null) => {
    const result = node("a", label);
    result.href = url(changes);
    if (current) result.setAttribute("aria-current", "page");
    if (count !== null) result.append(node("small", String(count)));
    return result;
  };
  const form = document.querySelector("[data-library-search]");
  form.elements.q.value = text;
  for (const key of ["scope", "category"]) {
    let input = form.elements.namedItem(key);
    if (!input) {
      input = document.createElement("input");
      input.type = "hidden";
      input.name = key;
      form.append(input);
    }
    input.value = params[key];
  }
  if (siteSelect) siteSelect.value = site;
  const trail = document.querySelector(".library-trail");
  if (trail) trail.hidden = Boolean(text || category || site || scope !== "learn" || page > 1);
  const archived = matching.filter((item) => item.archived).length;
  document.querySelector(".library-tabs").replaceChildren(
    ...[["learn", "教程与解读", matching.length - archived], ["archive", "历史资料", archived], ["all", "全部资料", matching.length]]
      .map(([value, label, count]) => link(label, {scope: value, category: "", page: 1}, scope === value, count))
  );
  const navigation = document.querySelector(".library-nav");
  navigation.replaceChildren(link("全部主题", {category: "", page: 1}, !category, scoped.length));
  for (const name of categories) {
    const count = scoped.filter((item) => item.category === name).length;
    if (count || category === name) navigation.append(link(name, {category: name, page: 1}, category === name, count));
  }
  const context = document.querySelector(".library-context");
  const heading = text ? `“${text}”的搜索结果` : category || {learn: "教程与解读", archive: "历史资料", all: "全部资料"}[scope];
  context.querySelector("h2").textContent = heading;
  const count = filtered.length;
  context.querySelector("span").textContent = count ? `第 ${(page - 1) * 12 + 1}–${Math.min(page * 12, count)} 篇 / 共 ${count} 篇` : "0 篇";
  context.setAttribute("role", "status");
  const articles = document.getElementById("articles");
  articles.querySelectorAll(".reading-list, .empty, .library-pagination, .article-notice").forEach((item) => item.remove());
  if (scope === "archive") articles.append(node("p", "旧活动、旧产品和历史比较，仅作学习案例。原文中的资格、收益和操作入口可能已失效。", "article-notice"));
  if (count) {
    const list = node("div", "", "reading-list");
    for (const item of filtered.slice((page - 1) * 12, page * 12)) {
      const template = document.createElement("template");
      // HTML is escaped by the exporter; URL query values never become HTML.
      template.innerHTML = item.html;
      list.append(template.content.cloneNode(true));
    }
    articles.append(list);
  } else {
    const empty = node("div", "", "empty");
    empty.append(node("h2", "没有找到这类文章"), node("p", "试试“订单”“手续费”等短词，或扩大搜索范围。"),
      link("在全部资料中搜索", {scope: "all", category: "", site: "", page: 1}),
      link("清除筛选", {q: "", scope: "learn", category: "", site: "", page: 1}));
    articles.append(empty);
  }
  if (pages > 1) {
    const pagination = node("nav", "", "library-pagination");
    pagination.setAttribute("aria-label", "文章分页");
    for (const [label, destination, relation] of [["上一页", page - 1, "prev"], ["下一页", page + 1, "next"]]) {
      if (relation === "next") pagination.append(node("span", `第 ${page} / ${pages} 页`));
      if (destination > 0 && destination <= pages) {
        const item = link(label, {page: destination});
        item.href += "#articles";
        item.rel = relation;
        pagination.append(item);
      } else {
        const item = node("span", label);
        item.setAttribute("aria-disabled", "true");
        pagination.append(item);
      }
    }
    articles.append(pagination);
  }
})();
