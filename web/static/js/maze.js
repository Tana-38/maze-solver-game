/* MazeView: draws a maze from the API's open_right / open_down grids on a canvas.
   Layers: explored cells, walls, paths, start / exit markers, hint, player.
   Animated properties (build, exploredIndex, path progress, player x/y) are plain
   fields so GSAP can tween them; draw() is called from the GSAP ticker. */

(function () {
  "use strict";

  const WHITE = "rgba(247, 248, 246, 1)";

  class MazeView {
    constructor(canvas, options = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.opts = Object.assign(
        {
          maxCell: 34,      // largest cell size in CSS pixels
          wallRatio: 0.09,  // wall width as a share of the cell
          minWall: 1.4,
          pathRatio: 0.3,   // solution path width as a share of the cell
          fit: null,        // element whose size bounds the canvas (defaults to parent)
          fitHeight: false  // also fit the host's height (hosts with a fixed aspect ratio)
        },
        options
      );
      this.maze = null;
      this.build = 1;          // 0..1 share of walls drawn (intro animation)
      this.explored = [];
      this.exploredIndex = 0;  // fractional, tweened
      this.exploredStyle = "rgba(255,255,255,0.22)";
      this.paths = [];         // {cells, progress (0..1), color, width, dash}
      this.player = null;      // {x, y} in cell units, tweened
      this.trail = null;       // cells walked by the player
      this.hint = null;        // [r, c]
      this.showMarkers = true;
      this.time = 0;
      this.cell = 10;
      this.dirty = true;
    }

    setMaze(maze) {
      this.maze = maze;
      this.explored = [];
      this.exploredIndex = 0;
      this.paths = [];
      this.trail = null;
      this.hint = null;
      this.player = null;
      this._walls = this._buildWalls();
      this.resize();
    }

    /* Wall segments in cell units, sorted by distance from the start so the
       build animation grows outward from it. */
    _buildWalls() {
      const { rows, cols, open_right: R, open_down: D, start } = this.maze;
      const walls = [];
      const add = (x1, y1, x2, y2, r, c) => {
        const d = Math.abs(r - start[0]) + Math.abs(c - start[1]);
        walls.push({ x1, y1, x2, y2, d: d + Math.random() * 2 });
      };
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          if (r === 0) add(c, 0, c + 1, 0, r, c);
          if (c === 0) add(0, r, 0, r + 1, r, c);
          if (!R[r][c]) add(c + 1, r, c + 1, r + 1, r, c);
          if (!D[r][c]) add(c, r + 1, c + 1, r + 1, r, c);
        }
      }
      walls.sort((a, b) => a.d - b.d);
      return walls;
    }

    resize() {
      if (!this.maze) return;
      const { rows, cols } = this.maze;
      const host = this.opts.fit || this.canvas.parentElement;
      const style = getComputedStyle(host);
      const padX = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
      const padY = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
      const availW = Math.max(60, host.clientWidth - padX);
      let availH = host.clientHeight - padY;
      if (!this.opts.fitHeight || !(availH > 40)) availH = Infinity;
      const viewportCap = window.innerHeight * 0.78;
      let cell = Math.min(this.opts.maxCell, availW / cols, availH / rows, viewportCap / rows);
      cell = Math.max(4, Math.floor(cell * 2) / 2);
      this.cell = cell;
      const wall = Math.max(this.opts.minWall, cell * this.opts.wallRatio);
      this.pad = Math.ceil(wall);
      const w = cols * cell + this.pad * 2;
      const h = rows * cell + this.pad * 2;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.canvas.style.width = w + "px";
      this.canvas.style.height = h + "px";
      this.canvas.width = Math.round(w * dpr);
      this.canvas.height = Math.round(h * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.dirty = true;
    }

    center(cell) {
      return [this.pad + (cell[1] + 0.5) * this.cell, this.pad + (cell[0] + 0.5) * this.cell];
    }

    /* Which cell a CSS-pixel point on the canvas falls in, or null. */
    cellAt(x, y) {
      if (!this.maze) return null;
      const c = Math.floor((x - this.pad) / this.cell);
      const r = Math.floor((y - this.pad) / this.cell);
      if (r < 0 || c < 0 || r >= this.maze.rows || c >= this.maze.cols) return null;
      return [r, c];
    }

    canMove(cell, dir) {
      const [r, c] = cell;
      const m = this.maze;
      if (dir === "up") return r > 0 && m.open_down[r - 1][c];
      if (dir === "down") return r < m.rows - 1 && m.open_down[r][c];
      if (dir === "left") return c > 0 && m.open_right[r][c - 1];
      if (dir === "right") return c < m.cols - 1 && m.open_right[r][c];
      return false;
    }

    /* BFS distance on the client, used only for the "to exit" readout. */
    distance(from, to) {
      const m = this.maze;
      const key = (r, c) => r * m.cols + c;
      const seen = new Int32Array(m.rows * m.cols).fill(-1);
      const queue = [from];
      seen[key(from[0], from[1])] = 0;
      for (let i = 0; i < queue.length; i++) {
        const cur = queue[i];
        const d = seen[key(cur[0], cur[1])];
        if (cur[0] === to[0] && cur[1] === to[1]) return d;
        for (const [dir, dr, dc] of [["up", -1, 0], ["down", 1, 0], ["left", 0, -1], ["right", 0, 1]]) {
          if (!this.canMove(cur, dir)) continue;
          const nr = cur[0] + dr, nc = cur[1] + dc;
          if (seen[key(nr, nc)] !== -1) continue;
          seen[key(nr, nc)] = d + 1;
          queue.push([nr, nc]);
        }
      }
      return -1;
    }

    /* BFS shortest path as a list of cells, used to draw the result at once. */
    shortestPath(from, to) {
      const m = this.maze;
      const prev = new Map([[from[0] * m.cols + from[1], null]]);
      const queue = [from];
      for (let i = 0; i < queue.length; i++) {
        const cur = queue[i];
        if (cur[0] === to[0] && cur[1] === to[1]) break;
        for (const [dir, dr, dc] of [["up", -1, 0], ["down", 1, 0], ["left", 0, -1], ["right", 0, 1]]) {
          if (!this.canMove(cur, dir)) continue;
          const next = [cur[0] + dr, cur[1] + dc];
          const k = next[0] * m.cols + next[1];
          if (prev.has(k)) continue;
          prev.set(k, cur);
          queue.push(next);
        }
      }
      const path = [];
      for (let cur = to; cur; cur = prev.get(cur[0] * m.cols + cur[1])) path.unshift(cur);
      return path;
    }

    draw(time = 0) {
      if (!this.maze) return;
      this.time = time;
      const ctx = this.ctx;
      const { cell, pad } = this;
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      // explored cells, newest one brighter
      const shown = Math.min(this.explored.length, Math.floor(this.exploredIndex));
      if (shown > 0) {
        ctx.fillStyle = this.exploredStyle;
        for (let i = 0; i < shown; i++) {
          const [r, c] = this.explored[i];
          ctx.fillRect(pad + c * cell, pad + r * cell, cell, cell);
        }
        if (shown < this.explored.length) {
          const [r, c] = this.explored[shown - 1];
          ctx.fillStyle = "rgba(255,255,255,0.75)";
          ctx.fillRect(pad + c * cell, pad + r * cell, cell, cell);
        }
      }

      // hint: dashed outline that breathes
      if (this.hint) {
        const [r, c] = this.hint;
        const inset = cell * (0.12 + 0.06 * Math.sin(time * 6));
        ctx.save();
        ctx.strokeStyle = WHITE;
        ctx.lineWidth = Math.max(1.2, cell * 0.07);
        ctx.setLineDash([cell * 0.18, cell * 0.12]);
        ctx.strokeRect(pad + c * cell + inset, pad + r * cell + inset, cell - inset * 2, cell - inset * 2);
        ctx.restore();
      }

      // walls
      const wallW = Math.max(this.opts.minWall, cell * this.opts.wallRatio);
      const count = Math.floor(this._walls.length * this.build);
      ctx.strokeStyle = WHITE;
      ctx.lineWidth = wallW;
      ctx.lineCap = "square";
      ctx.beginPath();
      for (let i = 0; i < count; i++) {
        const w = this._walls[i];
        ctx.moveTo(pad + w.x1 * cell, pad + w.y1 * cell);
        ctx.lineTo(pad + w.x2 * cell, pad + w.y2 * cell);
      }
      ctx.stroke();

      // player trail
      if (this.trail && this.trail.length > 1) {
        this._polyline(this.trail, 1, "rgba(255,255,255,0.55)", Math.max(1.2, cell * 0.1), null);
      }

      // solution / comparison paths
      for (const p of this.paths) {
        this._polyline(p.cells, p.progress, p.color || WHITE, p.width || Math.max(2, cell * this.opts.pathRatio), p.dash);
      }

      if (this.showMarkers && this.build > 0.6) this._markers(time);

      // player: a diamond with a soft glow
      if (this.player) {
        const x = pad + (this.player.x + 0.5) * cell;
        const y = pad + (this.player.y + 0.5) * cell;
        const s = cell * 0.3;
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(Math.PI / 4);
        ctx.shadowColor = "rgba(255,255,255,0.9)";
        ctx.shadowBlur = cell * 0.6;
        ctx.fillStyle = WHITE;
        ctx.fillRect(-s / 2, -s / 2, s, s);
        ctx.restore();
      }
      this.dirty = false;
    }

    _polyline(cells, progress, color, width, dash) {
      if (!cells || cells.length < 2 || progress <= 0) return;
      const ctx = this.ctx;
      const segments = cells.length - 1;
      const total = segments * Math.min(1, progress);
      const whole = Math.floor(total);
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = width;
      ctx.lineJoin = "miter";
      ctx.lineCap = "square";
      if (dash) ctx.setLineDash(dash);
      ctx.beginPath();
      const [x0, y0] = this.center(cells[0]);
      ctx.moveTo(x0, y0);
      for (let i = 1; i <= whole; i++) {
        const [x, y] = this.center(cells[i]);
        ctx.lineTo(x, y);
      }
      if (whole < segments) {
        const frac = total - whole;
        const [ax, ay] = this.center(cells[whole]);
        const [bx, by] = this.center(cells[whole + 1]);
        ctx.lineTo(ax + (bx - ax) * frac, ay + (by - ay) * frac);
      }
      ctx.stroke();
      ctx.restore();
    }

    /* Start: hollow diamond. Exit: four corner ticks that pulse. */
    _markers(time) {
      const ctx = this.ctx;
      const { cell } = this;
      const lw = Math.max(1.2, cell * 0.08);
      ctx.save();
      ctx.strokeStyle = WHITE;
      ctx.lineWidth = lw;

      const [sx, sy] = this.center(this.maze.start);
      const s = cell * 0.36;
      ctx.beginPath();
      ctx.moveTo(sx, sy - s / 1.2);
      ctx.lineTo(sx + s / 1.2, sy);
      ctx.lineTo(sx, sy + s / 1.2);
      ctx.lineTo(sx - s / 1.2, sy);
      ctx.closePath();
      ctx.stroke();

      const [gx, gy] = this.center(this.maze.goal);
      const half = cell * (0.3 + 0.05 * Math.sin(time * 4));
      const t = cell * 0.16;
      ctx.beginPath();
      for (const [dx, dy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
        const cx = gx + dx * half, cy = gy + dy * half;
        ctx.moveTo(cx, cy - dy * t);
        ctx.lineTo(cx, cy);
        ctx.lineTo(cx - dx * t, cy);
      }
      ctx.stroke();
      ctx.restore();
    }
  }

  window.MazeView = MazeView;
})();
