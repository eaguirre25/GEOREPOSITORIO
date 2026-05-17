const state = {
  rows: [],
  query: "",
  category: "all",
  sort: "date",
  savedOnly: false,
  saved: new Set(JSON.parse(localStorage.getItem("georepositorio:saved") || "[]")),
};

const els = {
  search: document.querySelector("#search"),
  category: document.querySelector("#category"),
  sort: document.querySelector("#sort"),
  savedOnly: document.querySelector("#savedOnly"),
  cards: document.querySelector("#cards"),
  total: document.querySelector("#total"),
  shown: document.querySelector("#shown"),
  savedCount: document.querySelector("#savedCount"),
  updated: document.querySelector("#updated"),
  categoryList: document.querySelector("#categoryList"),
  template: document.querySelector("#cardTemplate"),
};

function saveState() {
  localStorage.setItem("georepositorio:saved", JSON.stringify([...state.saved]));
}

function fmtDate(value) {
  if (!value) return "-";
  return String(value).slice(0, 10);
}

function textFor(row) {
  return [
    row.repo, row.description, row.category, row.language,
    row.license, ...(row.topics || [])
  ].join(" ").toLowerCase();
}

function filteredRows() {
  let rows = state.rows.filter(row => {
    if (state.savedOnly && !state.saved.has(row.repo)) return false;
    if (state.category !== "all" && row.category !== state.category) return false;
    if (state.query && !textFor(row).includes(state.query.toLowerCase())) return false;
    return true;
  });
  rows.sort((a, b) => {
    if (state.sort === "score") return (b.score || 0) - (a.score || 0);
    if (state.sort === "stars") return (b.stars || 0) - (a.stars || 0);
    if (state.sort === "name") return a.repo.localeCompare(b.repo);
    return String(b.magi_date || "").localeCompare(String(a.magi_date || ""));
  });
  return rows;
}

function renderCategoryOptions() {
  const categories = ["all", ...new Set(state.rows.map(row => row.category).filter(Boolean).sort())];
  els.category.innerHTML = "";
  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category === "all" ? "Todas las categorías" : category;
    els.category.append(option);
  }
}

function renderCategoryList() {
  const counts = new Map();
  for (const row of state.rows) counts.set(row.category, (counts.get(row.category) || 0) + 1);
  els.categoryList.innerHTML = "";
  [...counts.entries()].sort((a, b) => b[1] - a[1]).forEach(([category, count]) => {
    const div = document.createElement("div");
    div.className = "cat-row";
    div.innerHTML = `<span>${category}</span><b>${count}</b>`;
    els.categoryList.append(div);
  });
}

function renderCards() {
  const rows = filteredRows();
  els.cards.innerHTML = "";
  for (const row of rows) {
    const node = els.template.content.cloneNode(true);
    const card = node.querySelector(".card");
    const avatar = node.querySelector(".avatar");
    const title = node.querySelector("h3");
    const desc = node.querySelector(".desc");
    const meta = node.querySelector(".meta");
    const topics = node.querySelector(".topics");
    const github = node.querySelector(".github");
    const magi = node.querySelector(".magi");
    const save = node.querySelector(".save");

    card.classList.toggle("saved", state.saved.has(row.repo));
    avatar.src = row.avatar_url || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='88' height='88'%3E%3Crect width='88' height='88' fill='%23222b36'/%3E%3Cpath d='M18 56 44 20l26 36z' fill='%2353c7a2'/%3E%3C/svg%3E";
    title.textContent = row.repo || "Repositorio";
    desc.textContent = row.description || "Sin descripción disponible.";
    meta.innerHTML = [
      `<span class="pill category">${row.category}</span>`,
      `<span class="pill">${row.language || "n/d"}</span>`,
      `<span class="pill">★ ${row.stars || 0}</span>`,
      `<span class="pill">⑂ ${row.forks || 0}</span>`,
      `<span class="pill">${fmtDate(row.magi_date)}</span>`,
    ].join("");
    (row.topics || []).slice(0, 6).forEach(topic => {
      const span = document.createElement("span");
      span.className = "topic";
      span.textContent = topic;
      topics.append(span);
    });
    github.href = row.github_url || "#";
    magi.href = row.magi_url || "#";
    save.classList.toggle("on", state.saved.has(row.repo));
    save.textContent = state.saved.has(row.repo) ? "Guardado" : "Guardar";
    save.addEventListener("click", () => {
      if (state.saved.has(row.repo)) state.saved.delete(row.repo);
      else state.saved.add(row.repo);
      saveState();
      render();
    });
    els.cards.append(node);
  }
  els.shown.textContent = rows.length;
  els.savedCount.textContent = state.saved.size;
}

function render() {
  renderCards();
}

async function boot() {
  const response = await fetch("data/magi_repos.json", { cache: "no-store" });
  const payload = await response.json();
  state.rows = payload.rows || [];
  els.total.textContent = state.rows.length;
  els.updated.textContent = fmtDate(payload.generated_at);
  renderCategoryOptions();
  renderCategoryList();
  render();
}

els.search.addEventListener("input", event => { state.query = event.target.value; render(); });
els.category.addEventListener("change", event => { state.category = event.target.value; render(); });
els.sort.addEventListener("change", event => { state.sort = event.target.value; render(); });
els.savedOnly.addEventListener("change", event => { state.savedOnly = event.target.checked; render(); });

boot().catch(error => {
  els.cards.innerHTML = `<p>No se pudo cargar el dataset: ${error.message}</p>`;
});
