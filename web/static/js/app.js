/* Maze Solver frontend: talks to web/server.py and animates everything with GSAP. */

(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const hasGsap = typeof window.gsap !== "undefined";

  if (!hasGsap) {
    document.body.classList.remove("is-loading");
    const loader = $("#loader");
    if (loader) loader.remove();
    console.error("GSAP did not load. Check the internet connection for the CDN scripts.");
    return;
  }

  gsap.registerPlugin(ScrollTrigger);
  if (reduceMotion) gsap.globalTimeline.timeScale(20);

  /* ------------------------------------------------------------------ */
  /* API                                                                 */
  /* ------------------------------------------------------------------ */
  async function api(path, { method = "GET", body } = {}) {
    const res = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = {};
    try { data = await res.json(); } catch (_) { /* empty body */ }
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }

  /* ------------------------------------------------------------------ */
  /* Smooth scroll (Lenis) synced with ScrollTrigger                     */
  /* ------------------------------------------------------------------ */
  let lenis = null;
  if (!reduceMotion && typeof window.Lenis !== "undefined") {
    lenis = new Lenis({ lerp: 0.09, smoothWheel: true });
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
  }
  function scrollToTarget(target) {
    if (lenis) lenis.scrollTo(target, { duration: 1.6, easing: (t) => 1 - Math.pow(1 - t, 4) });
    else document.querySelector(target)?.scrollIntoView({ behavior: "smooth" });
  }
  $$("[data-scroll]").forEach((a) =>
    a.addEventListener("click", (e) => {
      const href = a.getAttribute("href");
      if (!href || !href.startsWith("#")) return;
      e.preventDefault();
      scrollToTarget(href === "#top" ? 0 : href);
    })
  );

  /* ------------------------------------------------------------------ */
  /* Text splitting                                                      */
  /* ------------------------------------------------------------------ */
  function splitChars(el) {
    const text = el.textContent;
    el.textContent = "";
    for (const ch of text) {
      const span = document.createElement("span");
      span.className = "ch";
      span.textContent = ch === " " ? " " : ch;
      el.appendChild(span);
    }
    return $$(".ch", el);
  }

  /* ------------------------------------------------------------------ */
  /* Render loop: every MazeView redraws on the GSAP ticker while visible */
  /* ------------------------------------------------------------------ */
  const views = new Set();
  const visible = new WeakMap();
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => visible.set(e.target, e.isIntersecting));
  }, { rootMargin: "120px" });
  function track(view) {
    views.add(view);
    visible.set(view.canvas, true);
    io.observe(view.canvas);
    return view;
  }
  gsap.ticker.add((time) => {
    views.forEach((v) => { if (visible.get(v.canvas)) v.draw(time); });
  });
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      views.forEach((v) => v.resize());
      ScrollTrigger.refresh();
    }, 120);
  });

  /* ------------------------------------------------------------------ */
  /* Toast on the board                                                  */
  /* ------------------------------------------------------------------ */
  const toastEl = $("#board-toast");
  function toast(msg) {
    toastEl.textContent = msg;
    gsap.killTweensOf(toastEl);
    gsap.timeline()
      .fromTo(toastEl, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.3, ease: "power3.out" })
      .to(toastEl, { opacity: 0, y: -4, duration: 0.4, delay: 1.8 });
  }

  /* ------------------------------------------------------------------ */
  /* Hero: date, demo maze solved in a loop                              */
  /* ------------------------------------------------------------------ */
  const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const now = new Date();
  $("#hero-date").textContent = `${days[now.getDay()]} - ${now.getDate()} ${months[now.getMonth()]}`;

  const heroView = track(new MazeView($("#hero-canvas"), {
    maxCell: 18, wallRatio: 0.08, minWall: 1.2, pathRatio: 0.36,
  }));
  heroView.showMarkers = false;
  heroView.exploredStyle = "rgba(255,255,255,0.12)";
  const heroProgress = $("#hero-progress");

  async function heroCycle() {
    let data;
    try {
      data = await api("/api/demo?rows=5&cols=20");
    } catch (err) {
      heroProgress.textContent = "offline";
      return;
    }
    heroView.setMaze(data.maze);
    heroView.explored = data.search.explored_order;
    const path = { cells: data.search.path, progress: 0 };
    heroView.paths = [path];
    heroView.build = 0;
    const counter = { v: 0 };
    const exploredDur = Math.min(3.2, data.search.explored_count / 45);
    gsap.timeline({ onComplete: () => gsap.delayedCall(2.2, heroOut) })
      .to(heroView, { build: 1, duration: 1.1, ease: "power2.inOut" })
      .to(heroView, { exploredIndex: data.search.explored_count, duration: exploredDur, ease: "none" })
      .to(path, { progress: 1, duration: 2.2, ease: "power1.inOut" }, "-=0.2")
      .to(counter, {
        v: 100, duration: exploredDur + 2.0, ease: "none",
        onUpdate: () => { heroProgress.textContent = Math.round(counter.v); },
      }, 1.1);
  }
  function heroOut() {
    gsap.timeline({ onComplete: heroCycle })
      .to(heroView, { exploredIndex: 0, duration: 0.5, ease: "power2.in" })
      .to(heroView.paths[0], { progress: 0, duration: 0.6, ease: "power2.in" }, 0)
      .to(heroView, { build: 0, duration: 0.6, ease: "power2.in" }, 0.2);
  }

  /* ------------------------------------------------------------------ */
  /* Intro: loader, then hero entrance                                   */
  /* ------------------------------------------------------------------ */
  const titleChars = $$(".hero__title [data-split]").map(splitChars);

  function intro() {
    const loader = $("#loader");
    const count = { v: 0 };
    const tl = gsap.timeline({
      defaults: { ease: "expo.out" },
      onComplete: () => {
        loader.remove();
        document.body.classList.remove("is-loading");
      },
    });
    tl.from(".loader__frame .corner", { scale: 0, opacity: 0, duration: 0.6, stagger: 0.05 })
      .to(count, {
        v: 100, duration: 1.3, ease: "power2.inOut",
        onUpdate: () => { $("#loader-count").textContent = Math.round(count.v); },
      }, 0)
      .to(".loader__frame", { scale: 1.6, opacity: 0, duration: 0.7, ease: "power3.in" }, 1.4)
      .to(loader, { clipPath: "inset(0 0 100% 0)", duration: 1.0, ease: "expo.inOut" }, 1.7)
      .from("#hero-device .device", {
        y: 140, rotateX: 18, rotateY: -14, opacity: 0, duration: 1.8,
      }, 2.0)
      .from(titleChars.flat(), { yPercent: 115, duration: 1.2, stagger: 0.045 }, 2.15)
      .from("[data-hero-fade]", { y: 30, opacity: 0, duration: 1.1, stagger: 0.12 }, 2.6)
      .from(".nav", { y: -30, opacity: 0, duration: 1 }, 2.6)
      .add(heroCycle, 2.4);
    loader.style.clipPath = "inset(0 0 0% 0)";
  }

  // Device tilts gently with the pointer and drifts on scroll.
  const device = $("#hero-device .device");
  if (!reduceMotion && window.matchMedia("(pointer: fine)").matches) {
    const rx = gsap.quickTo(device, "rotateX", { duration: 0.9, ease: "power3.out" });
    const ry = gsap.quickTo(device, "rotateY", { duration: 0.9, ease: "power3.out" });
    $(".hero").addEventListener("pointermove", (e) => {
      const x = e.clientX / window.innerWidth - 0.5;
      const y = e.clientY / window.innerHeight - 0.5;
      rx(-y * 8);
      ry(x * 10);
    });
  }
  gsap.to("#hero-device", {
    yPercent: -12, ease: "none",
    scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true },
  });
  gsap.to(".hero__copy", {
    yPercent: -22, opacity: 0.2, ease: "none",
    scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true },
  });
  // Marble surfaces drift slowly.
  $$(".device .marble").forEach((m, i) => {
    gsap.to(m, { xPercent: i % 2 ? -4 : 4, yPercent: i % 2 ? 3 : -3, duration: 14 + i * 2, ease: "sine.inOut", yoyo: true, repeat: -1 });
  });

  /* ------------------------------------------------------------------ */
  /* Scroll reveals                                                      */
  /* ------------------------------------------------------------------ */
  $$("[data-split-scroll]").forEach((el) => {
    const chars = splitChars(el);
    el.style.overflow = "hidden";
    gsap.from(chars, {
      yPercent: 110, duration: 1.1, ease: "expo.out", stagger: 0.04,
      scrollTrigger: { trigger: el, start: "top 85%" },
    });
  });
  gsap.set("[data-reveal]", { opacity: 0 });
  ScrollTrigger.batch("[data-reveal]", {
    start: "top 88%",
    once: true,
    onEnter: (batch) => gsap.fromTo(batch,
      { y: 50, opacity: 0, clipPath: "inset(12% 0 0 0)" },
      { y: 0, opacity: 1, clipPath: "inset(0% 0 0 0)", duration: 1.1, ease: "expo.out", stagger: 0.09, overwrite: true,
        onComplete() { batch.forEach((el) => { el.style.clipPath = ""; }); } }),
  });

  // Nav: hide on scroll down, show on scroll up, highlight the current section.
  const nav = $("#nav");
  ScrollTrigger.create({
    start: 120,
    onUpdate: (self) => gsap.to(nav, { yPercent: self.direction === 1 ? -100 : 0, duration: 0.45, ease: "power3.out", overwrite: true }),
  });
  ["play", "race", "graph", "method"].forEach((id) => {
    const link = $(`.nav__links a[href="#${id}"]`);
    ScrollTrigger.create({
      trigger: `#${id}`, start: "top 55%", end: "bottom 45%",
      onToggle: (self) => link.classList.toggle("is-current", self.isActive),
    });
  });

  /* ------------------------------------------------------------------ */
  /* Game                                                                */
  /* ------------------------------------------------------------------ */
  const boardCanvas = $("#board-canvas");
  const boardFrame = $("#board-frame");
  const board = track(new MazeView(boardCanvas, { maxCell: 46, fit: boardFrame }));
  const settings = { difficulty: "easy", algorithm: "dfs", mode: "corners" };
  const game = {
    id: null,
    maze: null,
    pos: null,
    optimal: 0,
    finished: false,
    locked: false,       // true while the solution animation plays
    startedAt: null,
    queue: Promise.resolve(),
    analysis: null,
  };
  const S = {
    moves: $("#s-moves"), time: $("#s-time"), optimal: $("#s-optimal"),
    remaining: $("#s-remaining"), hints: $("#s-hints"), backtracks: $("#s-backtracks"),
    progress: $("#s-progress"),
  };

  // settings toggles
  $$(".toggle-group").forEach((group) => {
    group.addEventListener("click", (e) => {
      const btn = e.target.closest(".chip");
      if (!btn) return;
      $$(".chip", group).forEach((b) => b.classList.toggle("is-active", b === btn));
      settings[group.dataset.group] = btn.dataset.value;
      if (group.dataset.group === "difficulty") toggleCustom(btn.dataset.value === "custom");
    });
  });
  const customFields = $("#custom-fields");
  function toggleCustom(show) {
    if (show) {
      customFields.hidden = false;
      gsap.fromTo(customFields, { height: 0, opacity: 0 }, { height: "auto", opacity: 1, duration: 0.5, ease: "power3.out" });
    } else if (!customFields.hidden) {
      gsap.to(customFields, { height: 0, opacity: 0, duration: 0.35, ease: "power3.in", onComplete: () => { customFields.hidden = true; } });
    }
  }
  for (const [id, digits] of [["rows", 0], ["cols", 0], ["braid", 2]]) {
    const input = $("#" + id);
    const out = $(`#${id}-out`);
    input.addEventListener("input", () => { out.textContent = Number(input.value).toFixed(digits); });
  }

  function setStat(el, value) {
    if (el.textContent === String(value)) return;
    el.textContent = value;
    gsap.fromTo(el, { yPercent: 40, opacity: 0.2 }, { yPercent: 0, opacity: 1, duration: 0.35, ease: "power3.out" });
  }

  function updatePlayerStats(player) {
    setStat(S.moves, player.moves);
    setStat(S.hints, player.hints_used);
    setStat(S.backtracks, player.backtracks);
  }

  function updateRemaining() {
    if (!game.maze || !game.pos) return;
    const left = board.distance(game.pos, game.maze.goal);
    setStat(S.remaining, left);
    const pct = game.optimal ? Math.max(0, 1 - left / game.optimal) : 1;
    gsap.to(S.progress, { width: `${pct * 100}%`, duration: 0.4, ease: "power2.out" });
  }

  async function newGame() {
    const body = { ...settings };
    if (settings.difficulty === "custom") {
      body.rows = Number($("#rows").value);
      body.cols = Number($("#cols").value);
      body.braid = Number($("#braid").value);
    }
    const seed = $("#seed").value.trim();
    if (seed) body.seed = seed;
    let data;
    try {
      data = await api("/api/games", { method: "POST", body });
    } catch (err) {
      toast(err.message);
      return;
    }
    closeModal(true);
    game.id = data.id;
    game.maze = data.maze;
    game.pos = data.maze.start.slice();
    game.optimal = data.optimal_moves;
    game.finished = false;
    game.locked = false;
    game.startedAt = null;
    game.queue = Promise.resolve();
    game.analysis = data.analysis;

    board.setMaze(data.maze);
    board.player = { x: game.pos[1], y: game.pos[0] };
    board.trail = [game.pos.slice()];
    board.build = 0;
    gsap.to(board, { build: 1, duration: reduceMotion ? 0 : 1.2, ease: "power2.inOut" });
    gsap.fromTo(boardFrame, { scale: 0.97 }, { scale: 1, duration: 0.9, ease: "expo.out" });

    setStat(S.optimal, data.optimal_moves);
    updatePlayerStats(data.player);
    S.time.textContent = "0.0s";
    updateRemaining();
    renderAnalysis(data.analysis, data.maze);
    resetRace();
    toast(`Seed ${data.settings.seed} / ${data.maze.rows} x ${data.maze.cols} / ${data.settings.algorithm.toUpperCase()}`);
  }

  // Elapsed time readout, local clock started on the first move.
  gsap.ticker.add(() => {
    if (game.startedAt && !game.finished) {
      S.time.textContent = ((performance.now() - game.startedAt) / 1000).toFixed(1) + "s";
    }
  });

  const DELTA = { up: [-1, 0], down: [1, 0], left: [0, -1], right: [0, 1] };

  function move(dir) {
    if (!game.id || game.finished || game.locked) return;
    if (!board.canMove(game.pos, dir)) {
      gsap.fromTo(boardCanvas, { x: DELTA[dir][1] * 5, y: DELTA[dir][0] * 5 }, { x: 0, y: 0, duration: 0.45, ease: "elastic.out(1, 0.35)" });
      return;
    }
    // Move optimistically for instant feedback; the server confirms every step.
    if (!game.startedAt) game.startedAt = performance.now();
    game.pos = [game.pos[0] + DELTA[dir][0], game.pos[1] + DELTA[dir][1]];
    board.hint = null;
    board.trail.push(game.pos.slice());
    gsap.to(board.player, { x: game.pos[1], y: game.pos[0], duration: 0.12, ease: "power2.out", overwrite: true });
    updateRemaining();

    const id = game.id;
    game.queue = game.queue.then(async () => {
      if (id !== game.id) return;
      try {
        const res = await api(`/api/games/${id}/move`, { method: "POST", body: { direction: dir } });
        if (id !== game.id) return;
        updatePlayerStats(res.player);
        if (!res.moved && !res.player.finished) {
          const [sr, sc] = res.player.current;  // resync if the server disagreed
          game.pos = [sr, sc];
          gsap.to(board.player, { x: sc, y: sr, duration: 0.2 });
          updateRemaining();
        }
        if (res.result) finish(res.result);
      } catch (err) {
        toast(err.message);
      }
    });
  }

  function finish(result) {
    game.finished = true;
    S.time.textContent = result.elapsed_seconds.toFixed(1) + "s";
    board.trail = null;
    const mine = { cells: result.player_path, progress: 0, color: "rgba(255,255,255,0.55)", width: Math.max(1.5, board.cell * 0.14) };
    const best = { cells: result.optimal_path, progress: 0, width: Math.max(2, board.cell * 0.3) };
    board.paths = [mine, best];
    gsap.timeline()
      .to(mine, { progress: 1, duration: 0.9, ease: "power2.inOut" })
      .to(best, { progress: 1, duration: 1.1, ease: "power2.inOut" }, 0.3)
      .add(() => openModal(result), 1.1);
  }

  async function hint() {
    if (!game.id || game.finished || game.locked) return;
    await game.queue;
    try {
      const res = await api(`/api/games/${game.id}/hint`, { method: "POST" });
      board.hint = res.hint;
      updatePlayerStats(res.player);
      if (res.hint) toast("Hint costs 0.05 of your score");
    } catch (err) { toast(err.message); }
  }

  async function solve() {
    if (!game.id || game.locked) return;
    try {
      const res = await api(`/api/games/${game.id}/solve?algorithm=bfs`);
      game.locked = true;
      board.explored = res.explored_order;
      board.exploredIndex = 0;
      const path = { cells: res.path, progress: 0 };
      board.paths = [path];
      const dur = Math.min(4, res.explored_count / 120);
      gsap.timeline({ onComplete: () => { game.locked = false; } })
        .to(board, { exploredIndex: res.explored_count, duration: dur, ease: "none" })
        .to(path, { progress: 1, duration: 1.2, ease: "power2.inOut" });
      toast(`BFS explored ${res.explored_count} cells, path ${res.path_length} moves`);
    } catch (err) { toast(err.message); }
  }

  async function restart() {
    if (!game.id) return;
    await game.queue;
    try {
      const res = await api(`/api/games/${game.id}/restart`, { method: "POST" });
      closeModal(true);
      game.pos = res.player.current;
      game.finished = false;
      game.locked = false;
      game.startedAt = null;
      board.paths = [];
      board.explored = [];
      board.hint = null;
      board.trail = [game.pos.slice()];
      gsap.to(board.player, { x: game.pos[1], y: game.pos[0], duration: 0.5, ease: "expo.out" });
      updatePlayerStats(res.player);
      S.time.textContent = "0.0s";
      updateRemaining();
    } catch (err) { toast(err.message); }
  }

  $("#generate").addEventListener("click", newGame);
  $("#new-btn").addEventListener("click", newGame);
  $("#hint-btn").addEventListener("click", hint);
  $("#solve-btn").addEventListener("click", solve);
  $("#restart-btn").addEventListener("click", restart);
  $$(".dpad__btn").forEach((b) => b.addEventListener("click", () => move(b.dataset.dir)));

  // Keyboard is active while the board is on screen.
  let playInView = false;
  ScrollTrigger.create({
    trigger: "#board-frame", start: "top 85%", end: "bottom 15%",
    onToggle: (self) => {
      playInView = self.isActive;
      boardFrame.classList.toggle("is-focused", self.isActive);
    },
  });
  const KEYS = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right" };
  window.addEventListener("keydown", (e) => {
    const typing = e.target instanceof Element && e.target.closest("input, textarea");
    if (!playInView || typing || !$("#result-modal").hidden) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const dir = KEYS[e.key];
    const key = e.key.toLowerCase();
    if (dir) {
      e.preventDefault();
      move(dir);
    } else if (key === "h") { hint(); }
    else if (key === "s") { solve(); }
    else if (key === "r") { newGame(); }
  });

  // Swipe on touch screens.
  let touchStart = null;
  boardCanvas.addEventListener("pointerdown", (e) => { touchStart = [e.clientX, e.clientY]; boardCanvas.focus({ preventScroll: true }); });
  boardCanvas.addEventListener("pointerup", (e) => {
    if (!touchStart) return;
    const dx = e.clientX - touchStart[0];
    const dy = e.clientY - touchStart[1];
    touchStart = null;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < 24) return;
    move(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "down" : "up"));
  });

  /* ------------------------------------------------------------------ */
  /* Result modal                                                        */
  /* ------------------------------------------------------------------ */
  const modal = $("#result-modal");
  function openModal(r) {
    $("#result-rating").textContent = r.rating;
    $("#r-moves").textContent = r.player_moves;
    $("#r-optimal").textContent = r.optimal_moves;
    $("#r-time").textContent = r.elapsed_seconds.toFixed(1) + "s";
    $("#r-hints").textContent = r.hints_used;
    $("#r-backtracks").textContent = r.backtracks;
    $("#r-note").textContent = r.solution_revealed
      ? "You looked at the solution before finishing."
      : r.score === 1 ? "You walked a shortest path." : `${r.player_moves - r.optimal_moves} moves more than the shortest path.`;
    modal.hidden = false;
    if (lenis) lenis.stop();
    const score = { v: 0 };
    const chars = splitChars($("#result-rating"));
    gsap.timeline()
      .fromTo(".modal__backdrop", { opacity: 0 }, { opacity: 1, duration: 0.4 })
      .fromTo(".modal__card", { y: 60, opacity: 0, clipPath: "inset(0 0 100% 0)" },
        { y: 0, opacity: 1, clipPath: "inset(0 0 0% 0)", duration: 0.9, ease: "expo.out" }, 0.1)
      .from(".modal__card .corner", { scale: 0, duration: 0.5, stagger: 0.06, ease: "back.out(2)" }, 0.4)
      .from(chars, { yPercent: 100, opacity: 0, duration: 0.7, stagger: 0.04, ease: "expo.out" }, 0.35)
      .to(score, { v: r.score * 100, duration: 1.2, ease: "power3.out", onUpdate: () => { $("#result-score").textContent = Math.round(score.v); } }, 0.45)
      .from(".modal__rows > div", { y: 16, opacity: 0, duration: 0.5, stagger: 0.06, ease: "power3.out" }, 0.6);
    $("#r-next").focus({ preventScroll: true });
  }
  function closeModal(instant) {
    if (modal.hidden) return;
    const done = () => { modal.hidden = true; if (lenis) lenis.start(); };
    if (instant) return done();
    gsap.timeline({ onComplete: done })
      .to(".modal__card", { y: 30, opacity: 0, duration: 0.35, ease: "power3.in" })
      .to(".modal__backdrop", { opacity: 0, duration: 0.3 }, 0.1);
  }
  $$("[data-close]", modal).forEach((el) => el.addEventListener("click", () => closeModal()));
  $("#r-next").addEventListener("click", newGame);
  $("#r-replay").addEventListener("click", restart);
  window.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

  /* ------------------------------------------------------------------ */
  /* Race                                                                */
  /* ------------------------------------------------------------------ */
  const racers = $$(".racer").map((el) => ({
    el,
    algo: el.dataset.algo,
    view: track(new MazeView($("canvas", el), { maxCell: 40, fit: $(".racer__board", el), fitHeight: true })),
    stats: Object.fromEntries($$("[data-k]", el).map((d) => [d.dataset.k, d])),
  }));
  racers.forEach((r) => {
    if (r.algo === "dfs") r.view.exploredStyle = "rgba(225,236,245,0.26)";
    if (r.algo === "a_star") r.view.exploredStyle = "rgba(40,60,80,0.28)";
  });
  const speedInput = $("#speed");
  speedInput.addEventListener("input", () => { $("#speed-out").textContent = speedInput.value; });
  let raceTl = null;

  function resetRace() {
    if (raceTl) raceTl.kill();
    raceTl = null;
    racers.forEach((r) => {
      r.view.setMaze(game.maze);
      r.view.build = 1;
      r.stats.explored.textContent = "0";
      r.stats.path.textContent = "-";
      r.stats.runtime.textContent = "-";
    });
    $$(".bars__fill").forEach((f) => gsap.set(f, { width: 0 }));
    $$(".bars__num").forEach((n) => { n.textContent = "0"; });
    $("#race-verdict").textContent = "Run the race to compare how many cells each search explores before it reaches the exit.";
  }

  async function runRace() {
    if (!game.id) await newGame();
    if (!game.id) return;
    let data;
    try {
      data = await api(`/api/games/${game.id}/compare`);
    } catch (err) { toast(err.message); return; }
    resetRace();
    const speed = Number(speedInput.value);
    const max = Math.max(...Object.values(data.results).map((r) => r.explored_count));
    raceTl = gsap.timeline({
      onComplete: () => {
        const verdict = $("#race-verdict");
        verdict.textContent = data.verdict;
        gsap.from(verdict, { opacity: 0, y: 14, duration: 0.8, ease: "expo.out" });
      },
    });
    racers.forEach((r) => {
      const res = data.results[r.algo];
      r.view.explored = res.explored_order;
      const path = { cells: res.path, progress: 0 };
      r.view.paths = [path];
      const dur = res.explored_count / speed;
      const fill = $(`.bars__row[data-algo="${r.algo}"] .bars__fill`);
      const num = $(`.bars__row[data-algo="${r.algo}"] .bars__num`);
      raceTl
        .to(r.view, {
          exploredIndex: res.explored_count, duration: dur, ease: "none",
          onUpdate: () => {
            const n = Math.floor(r.view.exploredIndex);
            r.stats.explored.textContent = n;
            num.textContent = n;
            fill.style.width = `${(n / max) * 100}%`;
          },
        }, 0)
        .to(path, { progress: 1, duration: 0.9, ease: "power2.inOut" }, dur)
        .add(() => {
          r.stats.path.textContent = res.path_length ?? "none";
          r.stats.runtime.textContent = `${res.runtime_ms.toFixed(2)}ms`;
          gsap.fromTo(r.el, { y: -6 }, { y: 0, duration: 0.6, ease: "elastic.out(1, 0.4)" });
        }, dur + 0.9);
    });
  }
  $("#race-btn").addEventListener("click", runRace);
  $("#race-new-btn").addEventListener("click", async () => { await newGame(); runRace(); });

  /* ------------------------------------------------------------------ */
  /* Graph analysis                                                      */
  /* ------------------------------------------------------------------ */
  const statEls = $$("[data-stat]");
  const degreeBars = $("#degree-bars");
  let graphSeen = false;

  function renderAnalysis(a) {
    statEls.forEach((el) => {
      const key = el.dataset.stat;
      const value = a[key];
      if (value === null || value === undefined) { el.textContent = "-"; return; }
      const decimals = key === "difficulty" ? 2 : 0;
      const from = { v: Number(el.dataset.v || 0) };
      el.dataset.v = value;
      if (!graphSeen) { el.textContent = Number(value).toFixed(decimals); return; }
      gsap.to(from, {
        v: value, duration: 1.4, ease: "power3.out",
        onUpdate: () => { el.textContent = from.v.toFixed(decimals); },
      });
    });
    $$("[data-check]").forEach((el) => {
      const yes = a[el.dataset.check];
      el.textContent = yes ? "Yes" : "No";
      el.className = yes ? "is-yes" : "is-no";
    });
    const dist = a.degree_distribution;
    const peak = Math.max(1, ...Object.values(dist));
    degreeBars.innerHTML = "";
    Object.entries(dist).forEach(([deg, n]) => {
      const col = document.createElement("div");
      col.className = "degree";
      col.innerHTML = `<span class="degree__num">${n}</span><span class="degree__bar" style="height:${(n / peak) * 78}%"></span><span class="degree__label">deg ${deg}</span>`;
      degreeBars.appendChild(col);
    });
    if (graphSeen) {
      gsap.from($$(".degree__bar", degreeBars), { scaleY: 0, duration: 1, ease: "expo.out", stagger: 0.08 });
    }
  }

  ScrollTrigger.create({
    trigger: "#graph",
    start: "top 70%",
    once: true,
    onEnter: () => {
      graphSeen = true;
      statEls.forEach((el) => {
        const target = Number(el.dataset.v);
        if (Number.isNaN(target)) return;
        const decimals = el.dataset.stat === "difficulty" ? 2 : 0;
        const o = { v: 0 };
        gsap.to(o, { v: target, duration: 1.8, ease: "power3.out", delay: 0.3, onUpdate: () => { el.textContent = o.v.toFixed(decimals); } });
      });
      const bars = $$(".degree__bar", degreeBars);
      if (bars.length) gsap.from(bars, { scaleY: 0, duration: 1.2, ease: "expo.out", stagger: 0.1, delay: 0.4 });
    },
  });

  // Matrix-Tree theorem calculator.
  const kRows = $("#k-rows"), kCols = $("#k-cols"), kCount = $("#k-count");
  let kTimer;
  async function updateKirchhoff() {
    $("#k-rows-out").textContent = kRows.value;
    $("#k-cols-out").textContent = kCols.value;
    $("#k-size").textContent = `${kRows.value} x ${kCols.value}`;
    clearTimeout(kTimer);
    kTimer = setTimeout(async () => {
      try {
        const res = await api(`/api/spanning-trees?rows=${kRows.value}&cols=${kCols.value}`);
        const big = BigInt(res.count);
        if (big < 1000000000000n) {
          const o = { v: Number(kCount.dataset.v || 0) };
          gsap.to(o, { v: Number(big), duration: 0.9, ease: "power3.out", onUpdate: () => { kCount.textContent = Math.round(o.v).toLocaleString("en-US"); } });
          kCount.dataset.v = Number(big);
        } else {
          kCount.textContent = big.toLocaleString("en-US");
          kCount.dataset.v = 0;
          gsap.fromTo(kCount, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.6, ease: "expo.out" });
        }
      } catch (err) { kCount.textContent = "-"; }
    }, 120);
  }
  kRows.addEventListener("input", updateKirchhoff);
  kCols.addEventListener("input", updateKirchhoff);

  /* ------------------------------------------------------------------ */
  /* Method: pinned horizontal scroll on wide screens                    */
  /* ------------------------------------------------------------------ */
  const mm = gsap.matchMedia();
  mm.add("(min-width: 901px) and (prefers-reduced-motion: no-preference)", () => {
    const track = $("#method-track");
    const distance = () => Math.max(0, track.scrollWidth - window.innerWidth);
    gsap.to(track, {
      x: () => -distance(),
      ease: "none",
      scrollTrigger: {
        trigger: "#method",
        start: "top top",
        end: () => "+=" + distance(),
        pin: ".method__pin",
        scrub: 0.8,
        invalidateOnRefresh: true,
      },
    });
    gsap.from(".step", {
      opacity: 0.25, y: 40, stagger: 0.12, duration: 1, ease: "expo.out",
      scrollTrigger: { trigger: "#method", start: "top 70%" },
    });
  });
  mm.add("(max-width: 900px)", () => {
    gsap.utils.toArray(".step").forEach((step) => {
      gsap.from(step, { y: 40, opacity: 0, duration: 1, ease: "expo.out", scrollTrigger: { trigger: step, start: "top 88%" } });
    });
  });

  // Footer word slides in.
  gsap.from(".footer__word", {
    xPercent: -12, opacity: 0, ease: "none",
    scrollTrigger: { trigger: ".footer", start: "top bottom", end: "top 40%", scrub: true },
  });

  /* ------------------------------------------------------------------ */
  /* Boot                                                                */
  /* ------------------------------------------------------------------ */
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  window.scrollTo(0, 0);
  document.body.classList.add("is-loading");
  window.addEventListener("load", () => ScrollTrigger.refresh());
  newGame();
  updateKirchhoff();
  intro();
})();
