/*
 * The chart of docs/benchmark.md: the median time of one test call against the sample size n or the
 * conditioning-set size |Z|, one line per package. The data is sweep.json from benchmarks/summarize_sweep.py
 * (its docstring gives the schema); docs/conf.py copies it next to the page.
 *
 * The variables that hold parts of sweep.json are named data, lang, row, sweep, series, meta and run.
 * tests/test_docs_site.py checks that the fields read on them are fields of the schema.
 */
(function () {
  "use strict";

  // Coupling with sphinx-design (pinned in docs/requirements.txt): design-tabs.js keeps the selected tab of
  // each sync group in localStorage under <prefix><group>. The prefix comes from the
  // data-sd-tabs-storage-prefix attribute of its script tag. tests/test_docs_site.py checks this key format.
  var DEFAULT_TABS_PREFIX = "sphinx-design-tab-id-";
  var LANGUAGE_GROUP = "language"; // the :sync-group: of the language tab sets in docs/*.md

  // The palette slot (colours in sweep-chart.css) and the marker shape of each package. FastCIT is slot 1
  // and a circle in each language. The slots keep the packages that share a chart apart (dataviz palette
  // validator, all pairs, light and dark). The packages that share a chart also have different shapes, so
  // colour is never the only key. A package that is not in the list is a grey circle.
  var PACKAGES = {
    fastcit: [1, "circle"], dowhy: [2, "cross"], pgmpy: [3, "square"], "causal-learn": [4, "triangle"],
    pingouin: [5, "wedge"], tigramite: [6, "plus"], hyppo: [7, "wedge"], gcastle: [8, "diamond"],
    ppcor: [2, "wedge"], bnlearn: [3, "square"], Rfast: [4, "triangle"], dHSIC: [5, "plus"], comets: [6, "plus"],
    pcalg: [8, "diamond"]
  };
  // Marker outlines for radius 1 (about the area of the unit circle); "cross" is "plus" turned by 45 degrees.
  var SHAPES = {
    square: [[-0.9, -0.9], [0.9, -0.9], [0.9, 0.9], [-0.9, 0.9]],
    diamond: [[0, -1.25], [1.25, 0], [0, 1.25], [-1.25, 0]],
    triangle: [[0, -1.4], [1.25, 0.75], [-1.25, 0.75]],
    wedge: [[0, 1.4], [1.25, -0.75], [-1.25, -0.75]],
    plus: [[-0.4, -1.2], [0.4, -1.2], [0.4, -0.4], [1.2, -0.4], [1.2, 0.4], [0.4, 0.4], [0.4, 1.2], [-0.4, 1.2],
      [-0.4, 0.4], [-1.2, 0.4], [-1.2, -0.4], [-0.4, -0.4]]
  };
  SHAPES.cross = SHAPES.plus.map(function (p) { return [(p[0] - p[1]) * 0.7071, (p[0] + p[1]) * 0.7071]; });
  var AXES = { n: "Sample size", z: "Conditioning-set size" };
  var SYMBOLS = { n: "n", z: "|Z|" };
  var Y_TITLE = "Median time of one call (ms)";
  var SVG_NS = "http://www.w3.org/2000/svg";

  // ---------------------------------------------------------------- helpers

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function svg(parent, tag, attrs, className, text) {
    var node = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs).forEach(function (name) {
      node.setAttribute(name, attrs[name]);
    });
    if (className) node.setAttribute("class", className);
    if (text !== undefined) node.textContent = text;
    if (parent) parent.appendChild(node);
    return node;
  }

  function find(items, key) {
    return items.filter(function (item) { return item.key === key; })[0];
  }

  // 100000 -> "100 000" (no-break spaces, as in the tables of benchmarks/results).
  function grouped(value) {
    return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0");
  }

  // Milliseconds with the precision of benchmarks/summarize.py (fmt).
  function ms(value) {
    if (value >= 100) return grouped(Math.round(value));
    return value.toFixed(value >= 10 ? 1 : value >= 1 ? 2 : 3);
  }

  // Tick labels: 1K, 10K, ... on an axis that reaches 10 000.
  function tick(value, compact) {
    if (compact && value >= 1000) return grouped(value / 1000) + "K";
    return value < 1 ? String(+value.toPrecision(1)) : grouped(value);
  }

  function colour(engine) {
    return PACKAGES[engine] ? "var(--sweep-" + PACKAGES[engine][0] + ")" : "var(--sweep-other)";
  }

  // The marker of a package at (x, y). Hollow (class sweep-one): the same shape as an outline.
  function marker(parent, engine, x, y, r, className) {
    var points = SHAPES[PACKAGES[engine] && PACKAGES[engine][1]];
    if (!points) return svg(parent, "circle", { cx: x, cy: y, r: r }, className);
    var path = points.map(function (p, i) {
      return (i ? "L" : "M") + (x + p[0] * r).toFixed(1) + " " + (y + p[1] * r).toFixed(1);
    });
    return svg(parent, "path", { d: path.join(" ") + " Z" }, className);
  }

  // The key of a package in the legend and the tooltip: a short line with its marker.
  function key(engine) {
    var node = svg(null, "svg", { viewBox: "0 0 20 12", width: 20, height: 12, "aria-hidden": "true" }, "sweep-key");
    node.style.setProperty("--c", colour(engine));
    svg(node, "line", { x1: 0, x2: 20, y1: 6, y2: 6 }, "sweep-line");
    marker(node, engine, 10, 6, 3.5, "sweep-dot");
    return node;
  }

  function fixedText(sweep) {
    if (sweep.fixed.z === 0) return "Z empty";
    return sweep.fixed.z !== undefined ? "|Z| = " + sweep.fixed.z : "n = " + grouped(sweep.fixed.n);
  }

  // The language that the reader chose last in a language tab set, if the data has it.
  function storedLanguage(langs) {
    var stored = null;
    try {
      var script = document.querySelector("script[data-sd-tabs-storage-prefix]");
      var prefix = script ? script.getAttribute("data-sd-tabs-storage-prefix") : DEFAULT_TABS_PREFIX;
      if (prefix) stored = window.localStorage.getItem(prefix + LANGUAGE_GROUP);
    } catch (error) {
      stored = null; // storage blocked: start on the first language
    }
    return find(langs, stored) ? stored : langs[0].key;
  }

  // A row of toggle buttons; set() marks the current one and turns off the ones that have no data.
  function segmented(label, items, onPick) {
    var group = el("div", "sweep-segmented");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", label);
    var buttons = items.map(function (item) {
      var button = el("button", null, item[1]);
      button.type = "button";
      button.addEventListener("click", function () {
        onPick(item[0]);
      });
      group.appendChild(button);
      return { value: item[0], node: button };
    });
    return {
      node: group,
      set: function (current, available) {
        buttons.forEach(function (button) {
          button.node.setAttribute("aria-pressed", String(button.value === current));
          button.node.disabled = available ? !available(button.value) : false;
        });
      }
    };
  }

  // ------------------------------------------------------------ the parts

  // Why point i of a series has no value or a mark (for the tooltip and the notes).
  function reasons(series, i, passes) {
    if (series.values[i] === null) return ["no result (" + (series.skipped[i] || "no value") + ")"];
    var out = [];
    if (passes && series.passes[i] < passes) out.push("one pass (hollow marker)");
    var excluded = series.excluded[i];
    if (excluded) out.push(excluded + (excluded === 1 ? " query" : " queries") + " left out (error or NaN)");
    return out;
  }

  // The lines under the chart: the reasons of each package with their points, then the package notes.
  function notesOf(sweep, axis, passes) {
    var lines = [];
    var shared = []; // [note, labels]: one line per note text
    sweep.series.forEach(function (series) {
      var points = {};
      sweep.x.forEach(function (x, i) {
        reasons(series, i, passes).forEach(function (reason) {
          (points[reason] = points[reason] || []).push(grouped(x));
        });
      });
      Object.keys(points).forEach(function (reason) {
        lines.push([series.label, reason + " at " + SYMBOLS[axis] + " = " + points[reason].join(", ") + "."]);
      });
      series.notes.forEach(function (note) {
        var found = shared.filter(function (item) { return item[0] === note; })[0];
        if (found) found[1].push(series.label);
        else shared.push([note, [series.label]]);
      });
    });
    return lines.concat(shared.map(function (item) {
      return [item[1].join(", "), item[0]];
    }));
  }

  function tableOf(sweep, axis) {
    var wrap = el("div", "sweep-table-wrap");
    var table = el("table", "sweep-table");
    table.appendChild(el("caption", null, Y_TITLE));
    var head = table.createTHead().insertRow();
    head.appendChild(el("th", null, SYMBOLS[axis]));
    sweep.series.forEach(function (series) {
      head.appendChild(el("th", null, series.label));
    });
    var body = table.createTBody();
    sweep.x.forEach(function (x, i) {
      var tr = body.insertRow();
      var th = el("th", null, grouped(x));
      th.scope = "row";
      tr.appendChild(th);
      sweep.series.forEach(function (series) {
        var value = series.values[i];
        var cell = tr.insertCell();
        cell.textContent = value === null ? "—" : ms(value);
        if (value === null) cell.title = series.skipped[i] || "no value";
      });
    });
    wrap.appendChild(table);
    return wrap;
  }

  // The tooltip lines of point i: value first, then the package.
  function tipOf(tip, sweep, axis, passes, i) {
    tip.textContent = "";
    tip.appendChild(el("div", "sweep-tip-head", SYMBOLS[axis] + " = " + grouped(sweep.x[i])));
    sweep.series.forEach(function (series) {
      var value = series.values[i];
      var why = reasons(series, i, passes);
      var line = el("div", "sweep-tip-row");
      line.appendChild(key(series.engine));
      line.appendChild(el("strong", null, value === null ? "—" : ms(value) + " ms"));
      line.appendChild(el("span", null, series.label + (why.length ? ": " + why.join(", ") : "")));
      tip.appendChild(line);
    });
  }

  // ------------------------------------------------------------- the plot

  function drawPlot(figure, sweep, axis, passes) {
    figure.textContent = "";
    var xs = sweep.x;
    var all = [];
    sweep.series.forEach(function (series) {
      series.values.forEach(function (value) {
        if (value !== null) all.push(value);
      });
    });
    if (!all.length) {
      figure.appendChild(el("p", "sweep-empty", "No package has a result for this test."));
      return;
    }
    var width = Math.max(280, figure.clientWidth);
    var height = Math.round(Math.min(400, Math.max(260, width * 0.5)));
    var longest = Math.max.apply(null, sweep.series.map(function (series) {
      return series.label.length;
    }));
    var labels = width >= 560; // direct labels at the line ends on wide screens; the legend always
    var m = { top: 30, right: labels ? 18 + 7 * longest : 16, bottom: 46, left: 52 };
    var fx = axis === "n" ? Math.log10 : function (v) { return v; }; // log x for n, linear for |Z|
    var x0 = fx(xs[0]);
    var x1 = fx(xs[xs.length - 1]);
    var pad = 14;
    var sx = function (v) {
      return m.left + pad + ((fx(v) - x0) / (x1 - x0 || 1)) * (width - m.left - m.right - 2 * pad);
    };
    var lo = Math.floor(Math.log10(Math.min.apply(null, all)));
    var hi = Math.ceil(Math.log10(Math.max.apply(null, all)));
    if (hi === lo) hi += 1;
    var sy = function (v) {
      return m.top + ((hi - Math.log10(v)) / (hi - lo)) * (height - m.top - m.bottom);
    };
    var bottom = height - m.bottom;

    var chart = svg(figure, "svg", { viewBox: "0 0 " + width + " " + height, tabindex: "0", role: "img" }, "sweep-svg");
    chart.setAttribute("aria-label", "Line chart: " + Y_TITLE + " against " + AXES[axis].toLowerCase() + " " +
      SYMBOLS[axis] + ". The arrow keys move between the points. The Table button shows all values.");

    // Axes: a gridline per power of ten, a tick per point.
    for (var e = lo; e <= hi; e++) {
      var y = sy(Math.pow(10, e));
      svg(chart, "line", { x1: m.left, x2: width - m.right, y1: y, y2: y }, "sweep-grid");
      svg(chart, "text", { x: m.left - 8, y: y + 4, "text-anchor": "end" }, "sweep-tick",
        tick(Math.pow(10, e), Math.pow(10, hi) >= 10000));
    }
    svg(chart, "line", { x1: m.left, x2: width - m.right, y1: bottom, y2: bottom }, "sweep-axis");
    xs.forEach(function (x) {
      svg(chart, "text", { x: sx(x), y: bottom + 18, "text-anchor": "middle" }, "sweep-tick",
        tick(x, xs[xs.length - 1] >= 10000));
    });
    svg(chart, "text", { x: 0, y: 14 }, "sweep-title", Y_TITLE);
    svg(chart, "text", { x: m.left + (width - m.left - m.right) / 2, y: height - 6, "text-anchor": "middle" },
      "sweep-title", AXES[axis] + " " + SYMBOLS[axis] + " (" + fixedText(sweep) + ")");

    // Lines: a missing value breaks the line, so a gap never joins its neighbours.
    var ends = [];
    sweep.series.forEach(function (series) {
      var group = svg(chart, "g", {}, "sweep-series");
      group.style.setProperty("--c", colour(series.engine));
      var path = "";
      var pen = "M";
      var last = -1;
      series.values.forEach(function (value, i) {
        if (value === null) {
          pen = "M";
          return;
        }
        path += pen + sx(xs[i]).toFixed(1) + " " + sy(value).toFixed(1) + " ";
        pen = "L";
        last = i;
      });
      svg(group, "path", { d: path }, "sweep-line");
      series.values.forEach(function (value, i) {
        if (value === null) return;
        var one = passes && series.passes[i] < passes;
        marker(group, series.engine, sx(xs[i]), sy(value), one ? 5 : 4, "sweep-dot" + (one ? " sweep-one" : ""));
      });
      if (last < 0) return;
      ends.push({ x: sx(xs[last]) + 10, y: sy(series.values[last]), label: series.label, engine: series.engine });
    });

    // Direct labels, FastCIT first, then top to bottom. A label that would touch a placed one is left out
    // (the legend has it).
    var placed = [];
    if (labels) {
      ends.sort(function (a, b) {
        return (b.engine === "fastcit") - (a.engine === "fastcit") || a.y - b.y;
      }).forEach(function (end) {
        var near = placed.some(function (p) {
          return Math.abs(p.y - end.y) < 13 && Math.abs(p.x - end.x) < 7 * longest;
        });
        if (near) return;
        placed.push(end);
        svg(chart, "text", { x: end.x, y: end.y + 4 }, "sweep-label", end.label);
      });
    }

    // Hover and keyboard: a crosshair on the nearest point and one tooltip for every package.
    var cross = svg(chart, "line", { x1: 0, x2: 0, y1: m.top, y2: bottom, visibility: "hidden" }, "sweep-cross");
    var hit = svg(chart, "rect", { x: m.left, y: 0, width: width - m.left - m.right, height: bottom }, "sweep-hit");
    var tip = el("div", "sweep-tip");
    tip.hidden = true;
    tip.setAttribute("aria-live", "polite");
    figure.appendChild(tip);
    var current = 0;

    function show(i) {
      if (i === current && !tip.hidden) return; // the same point: no new announcement
      current = i;
      var x = sx(xs[i]);
      cross.setAttribute("x1", x);
      cross.setAttribute("x2", x);
      cross.setAttribute("visibility", "visible");
      tipOf(tip, sweep, axis, passes, i);
      tip.hidden = false;
      var scale = figure.clientWidth / width; // the SVG scales with the page until the next redraw
      var left = x * scale + 14;
      if (left + tip.offsetWidth > figure.clientWidth) left = Math.max(0, x * scale - 14 - tip.offsetWidth);
      tip.style.left = left + "px";
      tip.style.top = m.top * scale + "px";
    }

    function hide() {
      cross.setAttribute("visibility", "hidden");
      tip.hidden = true;
    }

    function nearest(event) {
      var box = chart.getBoundingClientRect();
      var x = ((event.clientX - box.left) / box.width) * width;
      var best = 0;
      xs.forEach(function (v, i) {
        if (Math.abs(sx(v) - x) < Math.abs(sx(xs[best]) - x)) best = i;
      });
      return best;
    }

    ["pointermove", "pointerdown"].forEach(function (type) {
      hit.addEventListener(type, function (event) {
        show(nearest(event));
      });
    });
    hit.addEventListener("pointerleave", function (event) {
      if (event.pointerType === "mouse") hide(); // a touch keeps its tooltip
    });
    chart.addEventListener("focus", function () {
      show(current);
    });
    chart.addEventListener("blur", hide);
    chart.addEventListener("keydown", function (event) {
      var moves = { ArrowLeft: current - 1, ArrowRight: current + 1, Home: 0, End: xs.length - 1 };
      if (event.key === "Escape") hide();
      if (!(event.key in moves)) return;
      event.preventDefault();
      show(Math.min(xs.length - 1, Math.max(0, moves[event.key])));
    });
  }

  // ------------------------------------------------------------ the chart

  function init(host, data) {
    var langs = (data.languages || []).filter(function (lang) { return lang.rows && lang.rows.length; });
    if (!langs.length) {
      host.textContent = "The chart data has no results.";
      return;
    }
    var state = { lang: storedLanguage(langs), row: null, axis: "n", table: false };
    var controls = el("div", "sweep-controls");
    var langControl = segmented("Language", langs.map(function (lang) {
      return [lang.key, lang.label];
    }), function (value) {
      state.lang = value;
      update();
    });
    var select = el("select", "sweep-select");
    select.setAttribute("aria-label", "Test");
    select.addEventListener("change", function () {
      state.row = select.value;
      update();
    });
    var axisControl = segmented("Axis", [["n", AXES.n], ["z", AXES.z]], function (value) {
      state.axis = value;
      update();
    });
    var tableButton = el("button", "sweep-toggle", "Table");
    tableButton.type = "button";
    tableButton.addEventListener("click", function () {
      state.table = !state.table;
      update();
    });
    controls.append(langControl.node, select, axisControl.node, tableButton);
    var legend = el("ul", "sweep-legend");
    var figure = el("div", "sweep-figure");
    var notes = el("ul", "sweep-notes");
    var setup = el("p", "sweep-meta");
    host.append(controls, legend, figure, notes, setup);
    var redraw = null; // draws the plot again at a new width (null in the table view)
    var drawnWidth = 0;

    function update() {
      var lang = find(langs, state.lang);
      var meta = data.meta[lang.key] || {};
      var passes = meta.passes;
      var row = find(lang.rows, state.row) || lang.rows[0];
      state.row = row.key;
      // HSIC has no |Z| sweep: show n, and keep the choice for the other tests.
      var axis = row.sweeps[state.axis] ? state.axis : Object.keys(row.sweeps)[0];
      var sweep = row.sweeps[axis];
      sweep.series.forEach(function (series) { // the log axis has no place for 0: a value <= 0 is missing
        series.values = series.values.map(function (v) { return v > 0 ? v : null; });
      });

      langControl.set(state.lang);
      axisControl.set(axis, function (value) {
        return Boolean(row.sweeps[value]);
      });
      tableButton.setAttribute("aria-pressed", String(state.table));
      select.textContent = "";
      lang.rows.forEach(function (row) {
        select.appendChild(new Option(row.label, row.key, false, row.key === state.row));
      });

      legend.textContent = "";
      sweep.series.forEach(function (series) {
        var item = el("li");
        item.append(key(series.engine), series.label);
        legend.appendChild(item);
      });
      legend.hidden = state.table;

      figure.textContent = "";
      redraw = null;
      if (state.table) figure.appendChild(tableOf(sweep, axis));
      else {
        redraw = function () {
          drawnWidth = figure.clientWidth;
          drawPlot(figure, sweep, axis, passes);
        };
        redraw();
      }

      notes.textContent = "";
      var lines = notesOf(sweep, axis, passes);
      if (data.quick) lines.unshift(["Quick run", "few queries and one pass. Do not use these numbers."]);
      lines.forEach(function (line) {
        var item = el("li");
        item.append(el("strong", null, line[0]), ": " + line[1]);
        notes.appendChild(item);
      });
      notes.hidden = !lines.length;

      var parts = [meta.interpreter, meta.cpu && meta.cpu + " (" + meta.logical_cpus + " logical CPUs)", meta.os,
        meta.date && meta.date.slice(0, 10), passes && passes + (passes === 1 ? " pass" : " passes")];
      var versions = function (map) {
        return Object.keys(map || {}).map(function (name) {
          return name + " " + map[name];
        }).join(", ");
      };
      var text = parts.filter(Boolean).join(" · ");
      if (meta.versions) text += ". Versions: " + versions(meta.versions) + ".";
      (meta.other_runs || []).forEach(function (run) {
        text += " Other run, " + run.interpreter + ": " + versions(run.versions) + ".";
      });
      setup.textContent = text;
    }

    update();
    window.addEventListener("resize", function () {
      if (redraw && figure.clientWidth !== drawnWidth) redraw();
    });
  }

  function start() {
    var host = document.querySelector(".sweep-chart");
    if (!host) return; // no sweep.json at build time: the page shows a notice
    fetch(host.getAttribute("data-src"))
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) { init(host, data); })
      .catch(function () {
        host.textContent = "The chart data did not load.";
      });
  }

  start(); // the script is deferred, so the page is parsed
})();
