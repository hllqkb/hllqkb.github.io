"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const all = (selector) => [...document.querySelectorAll(selector)];
  const num = (id) => Number($(id).value);
  const fmt = (n, digits = 2) => (Math.abs(n) < 1e-9 ? 0 : n).toLocaleString("zh-CN", {minimumFractionDigits: digits, maximumFractionDigits: digits});
  const signed = (n, digits = 2) => `${n > 1e-9 ? "+" : ""}${fmt(n, digits)}`;
  const element = (tag, text, className = "") => {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  function label(id, digits = 0, suffix = "") {
    $(`${id}-label`).textContent = `${fmt(num(id), digits)}${suffix}`;
  }
  function result(kind, title, amount, lines, formula = "", tone = "") {
    const root = $(`${kind}-result`);
    root.replaceChildren(element("span", title, "result-label"), element("strong", amount, tone));
    for (const line of lines) root.append(element("p", line));
    if (formula) root.append(element("p", formula, "formula"));
  }
  const signColor = (n) => n < -1e-9 ? "negative" : "positive";
  const labs = {
    pnl() {
      const cash = num("pnl-cash"), move = num("pnl-move"), profit = cash * move / 100;
      label("pnl-cash"); label("pnl-move", 0, "%");
      result("pnl", "毛盈亏 / USDT", signed(profit), [`现在持仓价值：${fmt(cash + profit)} USDT。`, "只看涨跌还不够，扣掉成本后才是净结果。"], `${fmt(cash, 0)} × ${signed(move, 0)}% = ${signed(profit)}`, signColor(profit));
    },
    fees() {
      const change = num("fees-move") / 100, fee = num("fees-rate") / 100, slip = $("fees-slip").checked ? .0005 : 0;
      const sell = 1000 * (1 + change) * (1 - slip) / (1 + slip);
      const totalFees = (1000 + sell) * fee;
      const net = sell - 1000 - totalFees;
      const breakEven = ((1 + fee) * (1 + slip) / ((1 - fee) * (1 - slip)) - 1) * 100;
      label("fees-move", 1, "%"); label("fees-rate", 2, "%");
      result("fees", "净盈亏 / USDT", signed(net), [`卖出成交额：${fmt(sell)}；买卖手续费合计：${fmt(totalFees)}。`, `市场价格需约涨 ${fmt(breakEven, 3)}% 才能回本。`], `卖出额 = 1,000 × (1 + 涨跌幅) × (1 − 卖出滑点) ÷ (1 + 买入滑点)。净结果 = 卖出额 − 1,000 − 双边手续费。显示值已四舍五入。`, signColor(net));
    },
    candle() {
      const close = num("candle-close"), y = 20 + (110 - close) * 6.5;
      label("candle-close");
      $("candle-body").setAttribute("y", String(Math.min(85, y)));
      $("candle-body").setAttribute("height", String(Math.max(1, Math.abs(85 - y))));
      $("candle-body").setAttribute("fill", close < 100 ? "#a83d2c" : "#285a43");
      $("candle-chart").setAttribute("aria-label", `假设开盘100，最高110，最低90，收盘${close}。`);
      result("candle", "相对开盘", `${signed(close - 100, 0)}%`, [`开盘 100，收盘 ${close}。本图用绿表示涨、红表示跌；平台配色可以不同。`, "无论收盘在哪里，都不能从这根线知道 110 和 90 哪个先出现。"], `涨跌幅 = (${close} − 100) ÷ 100 × 100%`, signColor(close - 100));
    },
    order() {
      const price = num("order-limit");
      label("order-limit");
      if (price < 100) result("order", "本例的即时成交", "暂未成交", [`你的上限为 ${price}，最低卖价是 100。`, "买单等待有合适的卖家，不保证之后一定成交。"]);
      else if (price < 101) result("order", "本例的即时成交", "成交 0.4 枚", ["以 100 买入 0.4 枚，支付 40。", "剩余 0.6 枚继续等待；101 超过你的上限。"]);
      else result("order", "本例的即时成交", "成交 1 枚", ["先吃掉 100 的 0.4 枚，再吃掉 101 的 0.6 枚。", `平均价格 100.60，不会因为你愿意付 ${price} 就全部按 ${price} 成交。`], "0.4 × 100 + 0.6 × 101 = 100.60");
    },
    leverage() {
      const leverage = num("lev-times"), move = num("lev-move"), gross = 1000 * leverage * move / 100;
      label("lev-times", 0, " 倍"); label("lev-move", 1, "%");
      const warning = gross <= -1000 ? "算术亏损已达到或超过本金。实际仓位通常更早强平，不能当作真实最终余额。" : "它是理论结果，未模拟途中强平；放大仓位不会提高判断正确率。";
      result("leverage", "理论毛盈亏 / USDT", signed(gross), [`${fmt(1000 * leverage, 0)} USDT 仓位；盈亏相当于本金的 ${signed(leverage * move, 1)}%。`, warning], `同样波动，1 倍仓位的毛盈亏是 ${signed(10 * move)} USDT。`, signColor(gross));
    },
    sizing() {
      const equity = num("size-equity"), risk = num("size-risk"), stop = num("size-stop"), budget = equity * risk / 100, position = budget / (stop / 100);
      label("size-equity"); label("size-risk", 1, "%"); label("size-stop", 1, "%");
      result("sizing", "理论仓位金额 / USDT", fmt(position), [`计划亏损预算 ${fmt(budget)}，不是保证最大只亏这些。`, position > equity ? "算出的仓位超过账户资金。普通无借款现货买不起，应减少仓位或跳过，不默认加杠杆。" : `仓位约占账户 ${fmt(position / equity * 100, 1)}%。实际仍要预留成本。`], `${fmt(equity, 0)} × ${fmt(risk, 1)}% ÷ ${fmt(stop, 1)}% = ${fmt(position)}`);
    },
    recovery() {
      const loss = num("rec-loss"), remaining = 1000 * (1 - loss / 100), recovery = (1000 / remaining - 1) * 100;
      label("rec-loss", 0, "%");
      result("recovery", "之后需要上涨", `${fmt(recovery, 1)}%`, [`从 1,000 剩到 ${fmt(remaining, 0)} USDT，还要赚回 ${fmt(1000 - remaining, 0)}。`, "亏损的分母和回本的分母不一样。"], `(${fmt(1000 - remaining, 0)} ÷ ${fmt(remaining, 0)}) × 100% = ${fmt(recovery, 1)}%`);
    },
    expectancy() {
      const win = num("exp-win"), gain = num("exp-gain"), loss = num("exp-loss"), fee = num("exp-fee"), expected = win / 100 * gain - (1 - win / 100) * loss - fee;
      label("exp-win", 0, "%"); for (const id of ["exp-gain", "exp-loss", "exp-fee"]) label(id);
      result("expectancy", "每笔交易的数学期望 / USDT", signed(expected), ["这是给定假设下的平均值，不是下一笔一定赚或亏的金额。", "样本少或市场改变时，估算的胜率和盈亏比可能不可靠。"], `${win}% × ${gain} − ${100 - win}% × ${loss} − ${fee} = ${signed(expected)}`, signColor(expected));
    },
    signal() {
      const price = num("signal-price"), fires = price > 102;
      label("signal-price");
      result("signal", "规则判断", fires ? "发出买入信号" : "继续等待", [fires ? `${price} 严格大于此前最高收盘价 102。` : `${price} 没有严格超过 102，等于也不算。`, "发出信号只是一个条件，还要过仓位、风险与成交检查；下一天涨跌仍未知。"]);
    },
    bias() {
      result("bias", "先判断信息出现的时间", "选一个做法", ["左边两种做法，哪一种能在现实里执行？点击后看解释。"]);
    }
  };
  all("[data-lab]").forEach((root) => {
    const update = labs[root.dataset.lab];
    root.querySelectorAll("input").forEach((input) => input.addEventListener("input", update));
    update();
  });
  all("[data-bias]").forEach((button) => button.addEventListener("click", () => {
    const causal = button.dataset.bias === "causal";
    all("[data-bias]").forEach((item) => { delete item.dataset.state; item.setAttribute("aria-pressed", "false"); });
    button.dataset.state = causal ? "correct" : "wrong";
    button.setAttribute("aria-pressed", "true");
    result("bias", causal ? "时序合理" : "用到了未来信息", causal ? "先知道，再行动" : "开盘时还不知道", [causal ? "收盘后信号才形成，之后的成交价格是另一个需要模拟的环节。" : "当天开盘时，你并不知道今天最终会涨。用收盘结果倒填开盘买入，就是前视偏差。", "时序合理只是底线，不能据此证明策略会赚钱。"], "", causal ? "positive" : "negative");
  }));

  const links = all(".nav-lesson");
  const valid = new Set(links.map((link) => link.dataset.course));
  const key = "quant-academy-progress-v1";
  let state = {completed: [], last: ""};
  let undo = null;
  let storageWorks = true;
  function readProgress() {
    try {
      const completed = [...valid].filter((slug) => localStorage.getItem(`${key}:${slug}`) === "complete");
      const last = localStorage.getItem(`${key}:last`) || "";
      storageWorks = true;
      return {completed, last: valid.has(last) ? last : ""};
    } catch { storageWorks = false; return state; }
  }
  state = readProgress();
  const current = document.body.dataset.page;
  if (valid.has(current)) {
    state.last = current;
    try { localStorage.setItem(`${key}:last`, current); }
    catch { storageWorks = false; }
  }
  function renderProgress() {
    $("learning-progress").value = state.completed.length;
    $("progress-text").textContent = `${state.completed.length} / ${valid.size}`;
    all("[data-course]").forEach((link) => {
      link.querySelector(".done-label").hidden = !state.completed.includes(link.dataset.course);
      if (link.dataset.course === current) link.setAttribute("aria-current", "page");
    });
    $("storage-note").textContent = storageWorks ? "答对每课自测，进度保存在此浏览器。" : "浏览器不允许保存，进度仅在当前页面有效。";
    const resume = $("continue-learning");
    if (resume && state.last) {
      const link = links.find((item) => item.dataset.course === state.last);
      resume.href = `${document.body.dataset.basePath || ""}/learn/${state.last}/`;
      resume.textContent = `继续：${link.querySelector("b").textContent}`;
    } else if (resume) {
      resume.href = `${document.body.dataset.basePath || ""}/learn/money/`;
      resume.textContent = "从第一课开始";
    }
  }
  all("[data-quiz]").forEach((quiz) => {
    const feedback = quiz.querySelector(".quiz-feedback");
    if (state.completed.includes(quiz.dataset.quiz)) feedback.textContent = "这课已经完成，可以再练一次。";
    quiz.querySelectorAll("[data-answer]").forEach((button) => button.addEventListener("click", () => {
      const correct = button.dataset.answer === quiz.dataset.correct;
      quiz.querySelectorAll("[data-answer]").forEach((item) => { delete item.dataset.state; item.setAttribute("aria-pressed", "false"); });
      button.dataset.state = correct ? "correct" : "wrong";
      button.setAttribute("aria-pressed", "true");
      feedback.textContent = `${correct ? "答对了。" : "再想一下。"}${quiz.dataset.explanation}`;
      if (correct) {
        state = readProgress();
        if (!state.completed.includes(quiz.dataset.quiz)) state.completed.push(quiz.dataset.quiz);
        try { localStorage.setItem(`${key}:${quiz.dataset.quiz}`, "complete"); storageWorks = true; }
        catch { storageWorks = false; }
        renderProgress();
      }
    }));
  });
  $("clear-progress").addEventListener("click", () => {
    state = readProgress();
    undo = {completed: [...state.completed], last: state.last};
    state = {completed: [], last: ""};
    try {
      for (const slug of valid) localStorage.removeItem(`${key}:${slug}`);
      localStorage.removeItem(`${key}:last`);
    } catch { storageWorks = false; }
    $("undo-progress").hidden = false;
    all(".quiz-feedback").forEach((node) => { node.textContent = "进度已清除，可重新答题。"; });
    all("[data-answer]").forEach((button) => { delete button.dataset.state; button.setAttribute("aria-pressed", "false"); });
    renderProgress();
  });
  $("undo-progress").addEventListener("click", () => {
    if (undo) {
      state = readProgress();
      state = {completed: [...new Set([...state.completed, ...undo.completed])], last: state.last || undo.last};
      try {
        for (const slug of state.completed) localStorage.setItem(`${key}:${slug}`, "complete");
        localStorage.setItem(`${key}:last`, state.last);
      } catch { storageWorks = false; }
    }
    undo = null;
    $("undo-progress").hidden = true;
    all("[data-quiz]").forEach((quiz) => { quiz.querySelector(".quiz-feedback").textContent = state.completed.includes(quiz.dataset.quiz) ? "本课进度已恢复，可以再练一次。" : "进度已恢复，答对后记录本课。"; });
    renderProgress();
  });
  window.addEventListener("storage", (event) => {
    if (event.key !== null && !event.key.startsWith(`${key}:`)) return;
    state = readProgress();
    renderProgress();
    all("[data-quiz]").forEach((quiz) => {
      const done = state.completed.includes(quiz.dataset.quiz);
      quiz.querySelector(".quiz-feedback").textContent = done ? "已同步其他页面的进度，本课已完成。" : "学习进度已同步，答对后记录本课。";
      if (!done) quiz.querySelectorAll("[data-answer]").forEach((button) => { delete button.dataset.state; button.setAttribute("aria-pressed", "false"); });
    });
  });
  renderProgress();

  if ($("course-query")) {
    let stage = "all";
    $("course-query").value = new URLSearchParams(location.search).get("q") || "";
    function filterCourses() {
      const tokens = $("course-query").value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
      let count = 0;
      all(".curriculum-stage").forEach((section) => {
        let shown = 0;
        section.querySelectorAll(".course-row").forEach((row) => {
          const matches = (stage === "all" || stage === section.dataset.stage) && tokens.every((token) => row.dataset.search.toLocaleLowerCase().includes(token));
          row.hidden = !matches;
          if (matches) { shown++; count++; }
        });
        section.hidden = shown === 0;
      });
      $("search-status").textContent = `找到 ${count} 节课程`;
      $("search-empty").hidden = count !== 0;
    }
    $("course-query").addEventListener("input", filterCourses);
    all("[data-filter]").forEach((button) => button.addEventListener("click", () => {
      stage = button.dataset.filter;
      all("[data-filter]").forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
      filterCourses();
    }));
    filterCourses();
  }
  if ($("term-query")) {
    function filterTerms() {
      const query = $("term-query").value.toLocaleLowerCase().trim();
      let count = 0;
      all("[data-term]").forEach((term) => { term.hidden = !term.dataset.term.toLocaleLowerCase().includes(query); if (!term.hidden) count++; });
      $("term-status").textContent = `找到 ${count} 个术语`;
      $("term-empty").hidden = count !== 0;
    }
    $("term-query").addEventListener("input", filterTerms);
    filterTerms();
  }
  const readerTools = document.querySelector(".reader-tools");
  if (readerTools) {
    readerTools.hidden = false;
    let large = false;
    try { large = localStorage.getItem("quant-academy-large-text") === "true"; } catch { /* Reading works without storage. */ }
    document.body.classList.toggle("reading-large", large);
    const sizeButton = readerTools.querySelector('[data-reading-toggle="large"]');
    sizeButton.setAttribute("aria-pressed", String(large));
    sizeButton.textContent = large ? "标准字号" : "大字阅读";
    readerTools.addEventListener("click", (event) => {
      const button = event.target.closest("[data-reading-toggle]");
      if (!button) return;
      const focus = button.dataset.readingToggle === "focus";
      const enabled = document.body.classList.toggle(focus ? "reading-focus" : "reading-large");
      button.setAttribute("aria-pressed", String(enabled));
      button.textContent = focus ? (enabled ? "显示目录" : "专注阅读") : (enabled ? "标准字号" : "大字阅读");
      if (!focus) {
        try { localStorage.setItem("quant-academy-large-text", String(enabled)); } catch { /* Keep the current-page preference. */ }
      }
    });
  }
  const librarySite = $("library-site");
  librarySite?.addEventListener("change", () => librarySite.form.requestSubmit());
  const tocLinks = all(".page-toc a[href^='#']");
  if (tocLinks.length && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) if (entry.isIntersecting) {
        for (const link of tocLinks) {
          if (link.hash === `#${entry.target.id}`) link.setAttribute("aria-current", "location");
          else link.removeAttribute("aria-current");
        }
      }
    }, {rootMargin: "-85px 0px -65% 0px", threshold: 0});
    for (const link of tocLinks) {
      const target = document.getElementById(link.hash.slice(1));
      if (target) observer.observe(target);
    }
  }
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      const search = $("library-query") || $("nav-q");
      if (search) {
        if (search.id === "nav-q") {
          document.body.classList.remove("reading-focus");
          const button = document.querySelector('[data-reading-toggle="focus"]');
          if (button) { button.setAttribute("aria-pressed", "false"); button.textContent = "专注阅读"; }
          document.querySelector(".mobile-directory").open = true;
        }
        search.focus();
      }
    }
  });
  const mobile = matchMedia("(max-width: 760px)");
  function adaptDirectory() { document.querySelector(".mobile-directory").open = !mobile.matches; }
  mobile.addEventListener("change", adaptDirectory);
  adaptDirectory();
})();
