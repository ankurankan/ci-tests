/*
 * FastCIT runtime comparison: the chart, table, footnotes, verdict sentences and run details on
 * the home page. Ported from the earlier hand-written page (docs/site/site.js).
 *
 * It reads benchmarks.json (a copy of benchmarks/results/summary.json, see docs/conf.py) and draws
 * every package and test that the file contains. Nothing about the packages is fixed here, except
 * that the FastCIT column has the key "fastcit".
 *
 * The package ecosystem tabs follow the language tabs of the page (sphinx-design sync group
 * "language"), until the reader picks an ecosystem tab. Colours come from CSS variables in
 * benchmark-chart.css, which follow the theme's html[data-theme] attribute.
 */
(function () {
  "use strict";

  // Coupling with sphinx-design (pinned in docs/requirements.txt): its design-tabs.js keeps the
  // selected tab of each sync group in localStorage under <prefix><group>. The prefix comes from the
  // data-sd-tabs-storage-prefix attribute of its script tag (config sd_tabs_storage_prefix, default
  // "sphinx-design-tab-id-"). This is internal to sphinx-design. tests/test_docs_site.py checks that
  // the built site still uses this key format; update languageKey() if that test fails.
  var DEFAULT_TABS_PREFIX = "sphinx-design-tab-id-";
  var LANGUAGE_GROUP = "language"; // the :sync-group: of the language tab sets in docs/*.md
  var FOCUS_KEY = "fastcit";
  var SLOTS = 8;
  var SVG_NS = "http://www.w3.org/2000/svg";

  var ecosystemTabs = null;
  var ecosystemPicked = false; // true after the reader picks an ecosystem tab
  var tabsCount = 0;

  // ----------------------------------------------------------------- helpers

  function readStorage(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  // The localStorage key under which sphinx-design keeps the selected language tab, or null when
  // sphinx-design does not persist tabs (empty prefix). See the coupling note at the top.
  function languageKey() {
    var script = document.querySelector("script[data-sd-tabs-storage-prefix]");
    var prefix = script ? script.getAttribute("data-sd-tabs-storage-prefix") : DEFAULT_TABS_PREFIX;
    return prefix ? prefix + LANGUAGE_GROUP : null;
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function svg(tag, attrs, className) {
    var node = document.createElementNS(SVG_NS, tag);
    if (className) node.setAttribute("class", className);
    Object.keys(attrs || {}).forEach(function (name) {
      node.setAttribute(name, attrs[name]);
    });
    return node;
  }

  function link(href, text) {
    var a = el("a", null, text);
    a.href = href;
    return a;
  }

  function joinNames(names) {
    if (names.length <= 1) return names.join("");
    return names.slice(0, -1).join(", ") + " and " + names[names.length - 1];
  }

  function plural(count, singular, pluralForm) {
    return count + " " + (count === 1 ? singular : pluralForm || singular + "s");
  }

  function capitalize(text) {
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  // -------------------------------------------------------------------- tabs

  // Build a WAI-ARIA tablist for items [{key, label, panel}]. Returns {tablist, show, has}.
  function createTabs(label, items, initial, onSelect) {
    var id = "bench-tabs-" + ++tabsCount;
    var tablist = el("div", "bench-tablist");
    tablist.setAttribute("role", "tablist");
    tablist.setAttribute("aria-label", label);

    var tabs = items.map(function (item) {
      var tab = el("button", null, item.label);
      tab.type = "button";
      tab.id = id + "-tab-" + item.key;
      tab.setAttribute("role", "tab");
      if (!item.panel.id) item.panel.id = id + "-panel-" + item.key;
      tab.setAttribute("aria-controls", item.panel.id);
      item.panel.setAttribute("role", "tabpanel");
      item.panel.setAttribute("aria-labelledby", tab.id);
      item.panel.tabIndex = 0;
      tab.addEventListener("click", function () {
        select(item.key);
      });
      tablist.appendChild(tab);
      return tab;
    });

    tablist.addEventListener("keydown", function (event) {
      var index = tabs.indexOf(document.activeElement);
      if (index < 0) return;
      var next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      select(items[next].key);
      tabs[next].focus();
    });

    function has(key) {
      return items.some(function (item) {
        return item.key === key;
      });
    }

    function show(key) {
      if (!has(key)) return false;
      items.forEach(function (item, i) {
        var selected = item.key === key;
        tabs[i].setAttribute("aria-selected", selected ? "true" : "false");
        tabs[i].tabIndex = selected ? 0 : -1;
        item.panel.hidden = !selected;
      });
      return true;
    }

    function select(key) {
      if (show(key) && onSelect) onSelect(key);
    }

    show(has(initial) ? initial : items[0].key);
    return { tablist: tablist, show: show, has: has };
  }

  // Follow the language tabs of the page: a click on "Python" or "R" shows that ecosystem.
  // sphinx-design fires "change" on the radio input of the tab that the reader selects. The label
  // after the input carries data-sync-group and data-sync-id (sphinx-design markup, see the coupling
  // note at the top).
  function followLanguageTabs() {
    document.addEventListener("change", function (event) {
      var input = event.target;
      if (!input || !input.checked || !input.closest || !input.closest(".sd-tab-set")) return;
      var label = input.nextElementSibling;
      if (!label || label.getAttribute("data-sync-group") !== LANGUAGE_GROUP) return;
      // A later language click does not change the chart once the reader has picked an ecosystem.
      if (ecosystemTabs && !ecosystemPicked) ecosystemTabs.show(label.getAttribute("data-sync-id"));
    });
  }

  // ------------------------------------------------------- benchmark helpers

  function slotClass(slot) {
    return slot < SLOTS ? "s" + (slot + 1) : "s-other";
  }

  // The palette slot of each column. FastCIT always takes slot 1, whatever its column position.
  // The other columns keep their column order for the remaining slots.
  function assignSlots(columns) {
    var next = 1;
    return columns.map(function (column) {
      return column.key === FOCUS_KEY ? 0 : next++;
    });
  }

  // The number that a cell prints, so that a comparison agrees with what the reader sees.
  function printedValue(cell) {
    return parseFloat(String(cell.text).replace(/[\s\u00a0\u202f]/g, ""));
  }

  function hasValue(cell) {
    return typeof cell.value === "number" && cell.value > 0;
  }

  function footnoteMap(table) {
    var map = {};
    (table.footnotes || []).forEach(function (note) {
      map[note.mark] = note.text;
    });
    return map;
  }

  // Sentences that name every test where another package is faster than FastCIT.
  function verdictSentences(table, prefix) {
    var focus = -1;
    table.columns.forEach(function (column, i) {
      if (column.key === FOCUS_KEY) focus = i;
    });
    if (focus < 0) return [];
    var name = table.columns[focus].label;
    var compared = 0;
    var losses = [];
    table.rows.forEach(function (row) {
      if (!hasValue(row.cells[focus])) return;
      // A package is faster only when its printed time is lower than the printed time of FastCIT.
      var own = printedValue(row.cells[focus]);
      var rivals = [];
      row.cells.forEach(function (cell, i) {
        if (i !== focus && hasValue(cell)) rivals.push({ cell: cell, column: table.columns[i] });
      });
      if (!rivals.length) return;
      compared += 1;
      var faster = rivals
        .filter(function (rival) {
          return printedValue(rival.cell) < own;
        })
        .sort(function (a, b) {
          return printedValue(a.cell) - printedValue(b.cell) || a.cell.value - b.cell.value;
        });
      if (faster.length) losses.push({ row: row, faster: faster });
    });
    var lead = prefix ? prefix + ", " : "";
    // compared counts the tests where FastCIT and at least one other package have a result.
    if (!compared) return [capitalize(lead + "no other package has a result for the same tests.")];
    if (!losses.length) {
      var all = compared === 1 ? "the one compared test" : "all " + compared + " compared tests";
      return [capitalize(lead + name + " is the fastest package on " + all + ".")];
    }
    var sentences = [
      capitalize(
        lead + name + " is not the fastest package on " + losses.length + " of " + plural(compared, "compared test") + "."
      ),
    ];
    losses.forEach(function (loss) {
      var names = loss.faster.map(function (rival) {
        return rival.column.label + rival.cell.marks.join("");
      });
      sentences.push(
        "On " + loss.row.label + loss.row.marks.join("") + ", " + joinNames(names) +
          (names.length > 1 ? " are" : " is") + " faster."
      );
    });
    return sentences;
  }

  function verdictBox(table, prefix) {
    var box = el("div", "verdict");
    box.setAttribute("role", "note");
    verdictSentences(table, prefix).forEach(function (sentence) {
      box.appendChild(el("p", null, sentence));
    });
    return box;
  }

  function footnoteList(table) {
    var list = el("ul", "footnotes");
    (table.footnotes || []).forEach(function (note) {
      var item = el("li");
      item.appendChild(el("span", "fn-mark", note.mark));
      item.appendChild(el("span", null, note.text));
      list.appendChild(item);
    });
    return list;
  }

  function failureList(table) {
    var lines = [];
    table.rows.forEach(function (row) {
      row.cells.forEach(function (cell, i) {
        if (cell.errors || cell.nan) {
          lines.push(
            row.label + ", " + table.columns[i].label + ": " + plural(cell.errors, "error") + ", " +
              cell.nan + " NaN of " + plural(cell.queries, "query", "queries") + "."
          );
        }
      });
    });
    if (!lines.length) return null;
    var wrap = el("div", "failures");
    wrap.appendChild(el("p", null, "Errors and NaN:"));
    var list = el("ul", "footnotes");
    lines.forEach(function (line) {
      list.appendChild(el("li", null, line));
    });
    wrap.appendChild(list);
    return wrap;
  }

  function swatch(slot, focus) {
    var size = 14;
    var icon = svg("svg", { width: size, height: size, viewBox: "0 0 14 14", "aria-hidden": "true", focusable: "false" });
    icon.setAttribute("class", slotClass(slot));
    icon.appendChild(svg("circle", { cx: 7, cy: 7, r: focus ? 6 : 4.5 }, "swatch"));
    return icon;
  }

  function dataTable(table, captionText) {
    var scroll = el("div", "table-scroll");
    scroll.tabIndex = 0;
    scroll.setAttribute("role", "region");
    scroll.setAttribute("aria-label", captionText);
    var slots = assignSlots(table.columns);
    var tableEl = el("table");
    tableEl.appendChild(el("caption", null, captionText));
    var head = el("thead");
    var headRow = el("tr");
    var first = el("th", null, "Test");
    first.scope = "col";
    headRow.appendChild(first);
    table.columns.forEach(function (column, i) {
      var th = el("th");
      th.scope = "col";
      var key = el("span", "col-key");
      key.appendChild(swatch(slots[i], column.key === FOCUS_KEY));
      key.appendChild(el("span", null, column.label));
      th.appendChild(key);
      headRow.appendChild(th);
    });
    head.appendChild(headRow);
    tableEl.appendChild(head);
    var body = el("tbody");
    table.rows.forEach(function (row) {
      var tr = el("tr");
      var th = el("th", null, row.label + row.marks.join(""));
      th.scope = "row";
      tr.appendChild(th);
      row.cells.forEach(function (cell) {
        tr.appendChild(el("td", null, cell.text + cell.marks.join("")));
      });
      body.appendChild(tr);
    });
    tableEl.appendChild(body);
    scroll.appendChild(tableEl);
    return scroll;
  }

  function details(summaryText, children) {
    var box = el("details");
    box.appendChild(el("summary", null, summaryText));
    var body = el("div", "details-body");
    children.forEach(function (child) {
      if (child) body.appendChild(child);
    });
    box.appendChild(body);
    return box;
  }

  function runtimeName(meta) {
    if (meta.python) return "Python " + meta.python;
    if (meta.r) return String(meta.r);
    return "";
  }

  function versionsText(meta) {
    var versions = meta.versions || {};
    var commits = meta.commits || {};
    return Object.keys(versions)
      .map(function (name) {
        return name + " " + versions[name] + (commits[name] ? " (commit " + commits[name] + ")" : "");
      })
      .join(", ");
  }

  function loadAverage(uptime) {
    var match = /load averages?:\s*(.*)$/.exec(uptime || "");
    return match ? match[1] : uptime || "not recorded";
  }

  function fileName(path) {
    return String(path).split(/[\\/]/).pop();
  }

  function columnLabel(table, key) {
    for (var i = 0; i < table.columns.length; i += 1) {
      if (table.columns[i].key === key) return table.columns[i].label;
    }
    return key;
  }

  function powerText(power) {
    if (!power) return "not recorded";
    return (
      "AC online " + power.ac_online + ", profile " + power.profile + ", CPU 0 governor " + power.governor +
      ", EPP " + power.epp
    );
  }

  function floorText(ms) {
    return typeof ms === "number" ? Number(ms.toPrecision(2)) + " ms" : "not recorded";
  }

  // One sentence about the cells whose run values spread by more than the limit.
  function spreadSentence(eco, table) {
    var spread = eco.spread || {};
    var limit = Math.round(100 * (spread.limit || 0.25)) + " %";
    var cells = 0;
    var flagged = 0;
    table.rows.forEach(function (row) {
      row.cells.forEach(function (cell) {
        if (!hasValue(cell)) return;
        cells += 1;
        if (cell.flagged) flagged += 1;
      });
    });
    if (!flagged) return "Spread: in every cell, the run values differ by " + limit + " of the cell value or less.";
    return (
      "Spread: in " + flagged + " of " + cells + " cells, the run values differ by more than " + limit +
      " of the cell value. The mark \u2020 shows these cells."
    );
  }

  // One paragraph per extra interpreter: its packages, versions and the same-interpreter reference.
  function otherRunText(table, other) {
    var reference = other.reference || {};
    var refEngines = {};
    var refs = [];
    Object.keys(reference).forEach(function (row) {
      Object.keys(reference[row]).forEach(function (engine) {
        refEngines[engine] = true;
        refs.push(reference[row][engine]);
      });
    });
    var shown = (other.engines || [])
      .filter(function (engine) {
        return !refEngines[engine];
      })
      .map(function (engine) {
        return columnLabel(table, engine);
      });
    var runs = (other.runs || []).length;
    var text =
      "The " + joinNames(shown) + " column comes from a second interpreter, " + runtimeName(other) + ", " +
      plural(runs, "run") + ". Versions: " + versionsText(other) + ".";
    refs.forEach(function (ref) {
      text +=
        " In that interpreter, " + ref.package + " took " + ref.text + " ms per " + ref.label + " call (runs " +
        ref.range_text + " ms).";
    });
    return text;
  }

  function runInfo(eco, urls) {
    var meta = eco.meta || {};
    var table = eco.per_call;
    var box = el("div", "run-info");
    var machine = [meta.cpu + (meta.logical_cpus ? " (" + meta.logical_cpus + " logical CPUs)" : ""), meta.os, runtimeName(meta)]
      .filter(Boolean)
      .join(", ");
    var line = el("p", null, "Date: ");
    line.appendChild(el("span", "nowrap", String(meta.date || "not recorded").slice(0, 10)));
    line.appendChild(document.createTextNode(". Machine: " + machine + "."));
    box.appendChild(line);
    box.appendChild(el("p", null, "Versions: " + versionsText(meta) + "."));
    (meta.other_runs || []).forEach(function (other) {
      box.appendChild(el("p", null, otherRunText(table, other)));
    });
    var runs = (meta.runs || []).length;
    var method = el(
      "p",
      null,
      "Method: the benchmark ran " + plural(runs, "time") + ", each time in a new process. " +
        "Each time on this page is the median of the run values. " +
        "In each run, the time of one query is the best of " + plural(meta.passes, "pass", "passes") + ". " +
        "The run value is the median of the query times. " +
        "The time does not include the one-time setup. Read the full method in the "
    );
    method.appendChild(link(urls.benchmarks, "benchmark folder"));
    method.appendChild(document.createTextNode("."));
    box.appendChild(method);
    box.appendChild(el("p", null, spreadSentence(eco, table)));
    return box;
  }

  function runLines(add, meta, prefix) {
    (meta.runs || []).forEach(function (run, i) {
      add(
        prefix + "run " + (i + 1),
        String(run.date || "not recorded") + ", seed " + run.seed + ". Power: " + powerText(run.power) +
          ". Harness floor: " + floorText(run.harness_floor_ms) + ". Load average before: " +
          loadAverage(run.uptime_start) + ". After: " + loadAverage(run.uptime_end) + "."
      );
    });
  }

  function runDetails(meta) {
    var list = el("dl", "run-details");
    function add(term, value) {
      list.appendChild(el("dt", null, capitalize(term)));
      list.appendChild(el("dd", null, value));
    }
    var threads = meta.threads || {};
    var commits = meta.commits || {};
    add("Passes", meta.passes + " per run. Each pass runs the packages of a test in a new random order.");
    add(
      "Commits",
      Object.keys(commits)
        .map(function (name) {
          return name + " " + commits[name];
        })
        .join(", ") || "not recorded"
    );
    add(
      "CPU affinity",
      meta.affinity
        ? Object.keys(meta.affinity)
            .map(function (name) {
              return name + " " + meta.affinity[name];
            })
            .join("; ")
        : "not recorded"
    );
    var env = threads.env && Object.keys(threads.env).length
      ? Object.keys(threads.env)
          .map(function (name) {
            return name + "=" + threads.env[name];
          })
          .join(", ")
      : "none set";
    add("Threads", "FastCIT " + (threads.fastcit || "unknown") + ". Environment variables: " + env + ".");
    if (threads.pools) add("Thread pools", [].concat(threads.pools).join("; "));
    if (threads.blas) add("BLAS", fileName(threads.blas));
    if (threads.lapack) add("LAPACK", fileName(threads.lapack));
    runLines(add, meta, "");
    (meta.other_runs || []).forEach(function (other) {
      var name = runtimeName(other);
      if (other.threads && other.threads.pools) add(name + " thread pools", [].concat(other.threads.pools).join("; "));
      runLines(add, other, name + ", ");
    });
    return list;
  }

  // -------------------------------------------------------------- dot plot

  var measureContext = null;

  function textWidth(text, font) {
    if (!measureContext) measureContext = document.createElement("canvas").getContext("2d");
    if (!measureContext) return text.length * 7;
    measureContext.font = font;
    return measureContext.measureText(text).width;
  }

  function tickText(exponent) {
    if (exponent < 0) return (Math.pow(10, exponent)).toFixed(-exponent);
    return String(Math.pow(10, exponent)).replace(/\B(?=(\d{3})+(?!\d))/g, "\u202f");
  }

  // One test per row group, one lane per package (legend order), log-scaled x axis.
  function DotPlot(host, table, ecoLabel) {
    this.host = host;
    this.table = table;
    this.ecoLabel = ecoLabel;
    this.notes = footnoteMap(table);
    this.width = 0;
    this.active = 0;
    var self = this;
    var redraw = function () {
      window.requestAnimationFrame(function () {
        self.draw();
      });
    };
    if (window.ResizeObserver) new window.ResizeObserver(redraw).observe(host);
    else window.addEventListener("resize", redraw);
    // The web font can arrive after the first draw. Measure the labels again with it.
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () {
        self.width = 0;
        redraw();
      });
    }
    redraw();
  }

  DotPlot.prototype.draw = function () {
    var host = this.host;
    var width = Math.floor(host.clientWidth);
    if (!width || width === this.width) return;
    this.width = width;
    var hadFocus = host.contains(document.activeElement);
    host.textContent = "";

    var table = this.table;
    var columns = table.columns;
    var rows = table.rows;
    var n = columns.length;
    this.slots = assignSlots(columns);
    var slots = this.slots;
    var fontFamily = window.getComputedStyle(host).fontFamily;
    var lane = n <= 4 ? 16 : n <= 6 ? 14 : 12;
    var radius = n <= 6 ? 4.5 : 4;
    var focusRadius = radius + 1.5;
    var pad = 6;
    var band = 22;

    var labels = rows.map(function (row) {
      return row.label + row.marks.join("");
    });
    var labelWidth = Math.ceil(
      Math.max.apply(
        null,
        labels.map(function (label) {
          return textWidth(label, "13px " + fontFamily);
        })
      )
    ) + 16;
    var wide = width >= 520 && labelWidth <= width * 0.32;
    var head = wide ? 0 : 22;
    var plotLeft = (wide ? labelWidth : 0) + 14;
    var plotRight = width - 14;

    var values = [];
    rows.forEach(function (row) {
      row.cells.forEach(function (cell) {
        if (typeof cell.value === "number" && cell.value > 0) values.push(cell.value);
      });
    });
    if (!values.length) {
      host.appendChild(el("p", "bench-status", "This table has no results."));
      return;
    }
    var lo = Math.floor(Math.log10(Math.min.apply(null, values)));
    var hi = Math.ceil(Math.log10(Math.max.apply(null, values)));
    if (hi <= lo) hi = lo + 1;
    var x = function (value) {
      return plotLeft + ((Math.log10(value) - lo) / (hi - lo)) * (plotRight - plotLeft);
    };

    var groupTops = [];
    var y = band + 4;
    rows.forEach(function () {
      groupTops.push(y);
      y += head + pad * 2 + n * lane;
    });
    var plotBottom = y;
    var height = plotBottom + band;

    var root = svg("svg", { width: width, height: height, viewBox: "0 0 " + width + " " + height });
    root.setAttribute("role", "group");
    root.setAttribute(
      "aria-label",
      "Dot plot of the median time of one call, " + this.ecoLabel +
        ". Use the arrow keys to move between the marks. The table below gives the same numbers."
    );
    var grid = svg("g", { "aria-hidden": "true" });
    var labelLayer = svg("g", { "aria-hidden": "true" });
    var markLayer = svg("g");
    root.appendChild(grid);
    root.appendChild(labelLayer);
    root.appendChild(markLayer);

    // Decade gridlines and tick labels (top and bottom). Skip labels when they would collide.
    var tickFont = "11px " + fontFamily;
    var decade = (plotRight - plotLeft) / (hi - lo);
    var widest = 0;
    for (var e = lo; e <= hi; e += 1) widest = Math.max(widest, textWidth(tickText(e), tickFont));
    var every = Math.max(1, Math.ceil((widest + 10) / decade));
    for (var k = lo; k <= hi; k += 1) {
      var gx = x(Math.pow(10, k));
      grid.appendChild(svg("line", { x1: gx, x2: gx, y1: band, y2: plotBottom }, "gridline"));
      if ((k - lo) % every !== 0) continue;
      var text = tickText(k);
      var half = textWidth(text, tickFont) / 2;
      var tx = Math.min(Math.max(gx, half), width - half);
      [band - 8, plotBottom + 15].forEach(function (ty) {
        var tick = svg("text", { x: tx, y: ty, "text-anchor": "middle" }, "tick");
        tick.textContent = text;
        grid.appendChild(tick);
      });
    }

    var marks = [];
    var self = this;
    var valueFont = "600 11px " + fontFamily;
    var markFont = "16px " + fontFamily;
    var smallSize = lane < 14 ? 10 : 11;
    var noneFont = smallSize + "px " + fontFamily;

    // A label next to a dot: on the right when it fits, else on the left. Returns the x range it uses.
    function sideLabel(cx, cy, r, text, className, font) {
      var w = textWidth(text, font);
      var right = cx + r + 5 + w <= width;
      var label = svg(
        "text",
        { x: right ? cx + r + 5 : cx - r - 5, y: cy, "text-anchor": right ? "start" : "end", "dominant-baseline": "central" },
        className
      );
      label.textContent = text;
      labelLayer.appendChild(label);
      return right ? [cx - r, cx + r + 5 + w] : [cx - r - 5 - w, cx + r];
    }

    rows.forEach(function (row, g) {
      var top = groupTops[g];
      var lanesTop = top + head + pad;
      if (g > 0) grid.appendChild(svg("line", { x1: 0, x2: width, y1: top, y2: top }, "separator"));
      var rowLabel = svg(
        "text",
        wide
          ? { x: labelWidth - 6, y: lanesTop + (n * lane) / 2, "text-anchor": "end", "dominant-baseline": "central" }
          : { x: 0, y: top + 16, "text-anchor": "start" },
        "test-label"
      );
      if (!wide) rowLabel.setAttribute("font-weight", "600");
      rowLabel.textContent = labels[g];
      labelLayer.appendChild(rowLabel);

      var focusIndex = -1;
      columns.forEach(function (column, i) {
        if (column.key === FOCUS_KEY) focusIndex = i;
      });
      var focusValue = focusIndex >= 0 ? row.cells[focusIndex].value : null;
      var others = row.cells.filter(function (cell, i) {
        return i !== focusIndex && typeof cell.value === "number" && cell.value > 0;
      });
      var refX = null;
      if (typeof focusValue === "number" && focusValue > 0 && others.length) {
        refX = x(focusValue);
        grid.appendChild(svg("line", { x1: refX, x2: refX, y1: lanesTop, y2: lanesTop + n * lane }, "ref-line"));
      }

      // Text in a lane goes to the left end of the plot, else to the right end, where it does not touch
      // the dot and label of the lane (used) or the FastCIT line. An empty lane may fall back to
      // the space just after the FastCIT line. Returns false when there is no free place.
      function laneText(text, cy, used, className, font, fallback) {
        var w = textWidth(text, font);
        var clear = function (start) {
          var end = start + w;
          var hitsRef = refX !== null && refX >= start - 6 && refX <= end + 6;
          var hitsUsed = used !== null && used[0] <= end + 8 && used[1] >= start - 8;
          return !hitsRef && !hitsUsed;
        };
        var left = plotLeft + 4;
        var right = plotRight - w - 4;
        var start = clear(left) ? left : clear(right) ? right : fallback ? refX + 8 : null;
        if (start === null) return false;
        var node = svg("text", { x: start, y: cy, "dominant-baseline": "central" }, className);
        node.style.fontSize = smallSize + "px";
        node.textContent = text;
        labelLayer.appendChild(node);
        return true;
      }

      columns.forEach(function (column, i) {
        var cell = row.cells[i];
        var cy = lanesTop + i * lane + lane / 2;
        if (!hasValue(cell)) {
          // A package without this test leaves its lane empty (the table shows a dash). A package that
          // ran the test and got no result on any query says so, with its marks (the star).
          if (cell.queries !== undefined) {
            var none = "no result" + cell.marks.join("");
            laneText(none, cy, null, "none-label", "italic " + noneFont, true);
          }
          return;
        }
        var isFocus = column.key === FOCUS_KEY;
        var r = isFocus ? focusRadius : radius;
        var cx = x(cell.value);
        var mark = svg("g", {}, "mark " + slotClass(slots[i]));
        mark.setAttribute("tabindex", "-1");
        mark.setAttribute("role", "img");
        var markNames = cell.marks.length ? " Marks: " + cell.marks.join(" ") + "." : "";
        mark.setAttribute(
          "aria-label",
          column.label + ", " + row.label + row.marks.join("") + ": " + cell.text + " ms." + markNames
        );
        var hitHeight = lane; // not taller than the lane pitch, so hit areas never overlap the next lane
        mark.appendChild(svg("rect", { x: cx - 14, y: cy - hitHeight / 2, width: 28, height: hitHeight }, "hit"));
        mark.appendChild(svg("circle", { cx: cx, cy: cy, r: r + 2 }, "ring"));
        mark.appendChild(svg("circle", { cx: cx, cy: cy, r: r }, "dot"));
        mark.appendChild(svg("circle", { cx: cx, cy: cy, r: r + 3.5 }, "focus-ring"));
        markLayer.appendChild(mark);
        marks.push({ node: mark, row: row, column: column, cell: cell, index: i, cx: cx, cy: cy });

        if (isFocus) {
          sideLabel(cx, cy, r + 2, cell.text + cell.marks.join(""), "value-label", valueFont);
        } else if (cell.marks.length) {
          sideLabel(cx, cy, r + 2, cell.marks.join(""), "mark-label", markFont);
        }
      });
    });

    var tooltip = el("div", "tooltip");
    tooltip.hidden = true;
    tooltip.setAttribute("aria-hidden", "true");
    host.appendChild(root);
    host.appendChild(tooltip);
    this.marks = marks;
    this.tooltip = tooltip;
    this.root = root;

    if (this.active >= marks.length) this.active = 0;
    marks.forEach(function (mark, i) {
      mark.node.setAttribute("tabindex", i === self.active ? "0" : "-1");
      mark.node.addEventListener("pointerenter", function () {
        self.showTooltip(mark);
      });
      mark.node.addEventListener("pointerleave", function () {
        var focused = self.focusedMark();
        if (focused) self.showTooltip(focused);
        else self.hideTooltip();
      });
      mark.node.addEventListener("focus", function () {
        self.setActive(i);
        self.showTooltip(mark);
      });
      mark.node.addEventListener("blur", function () {
        self.hideTooltip();
      });
    });
    root.addEventListener("keydown", function (event) {
      var next = null;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") next = Math.min(self.active + 1, marks.length - 1);
      else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = Math.max(self.active - 1, 0);
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = marks.length - 1;
      else if (event.key === "Escape") {
        self.hideTooltip();
        return;
      } else return;
      event.preventDefault();
      self.setActive(next);
      marks[next].node.focus();
    });
    if (hadFocus && marks[this.active]) marks[this.active].node.focus();
  };

  DotPlot.prototype.focusedMark = function () {
    var active = document.activeElement;
    for (var i = 0; i < this.marks.length; i += 1) {
      if (this.marks[i].node === active) return this.marks[i];
    }
    return null;
  };

  DotPlot.prototype.setActive = function (index) {
    var marks = this.marks;
    this.active = index;
    marks.forEach(function (mark, i) {
      mark.node.setAttribute("tabindex", i === index ? "0" : "-1");
    });
  };

  DotPlot.prototype.hideTooltip = function () {
    this.tooltip.hidden = true;
    this.marks.forEach(function (mark) {
      mark.node.classList.remove("is-active");
    });
  };

  DotPlot.prototype.showTooltip = function (mark) {
    var tooltip = this.tooltip;
    var notes = this.notes;
    this.marks.forEach(function (other) {
      other.node.classList.toggle("is-active", other === mark);
    });
    tooltip.textContent = "";
    tooltip.appendChild(el("span", "tt-value", mark.cell.text + " ms"));
    var series = el("span", "tt-series " + slotClass(this.slots[mark.index]));
    series.appendChild(el("span", "tt-key"));
    series.appendChild(el("span", null, mark.column.label));
    tooltip.appendChild(series);
    tooltip.appendChild(el("span", null, mark.row.label + mark.row.marks.join("")));
    if (mark.cell.runs && mark.cell.runs.length > 1) {
      tooltip.appendChild(el("span", "tt-runs", plural(mark.cell.runs.length, "run") + ": " + mark.cell.range_text + " ms"));
    }
    if (mark.cell.marks.length) {
      var list = el("ul", "tt-notes");
      mark.cell.marks.forEach(function (m) {
        var text = m + " " + (notes[m] || "");
        if (m === "*") {
          text +=
            " (" + plural(mark.cell.errors, "error") + ", " + mark.cell.nan + " NaN of " +
            plural(mark.cell.queries, "query", "queries") + ")";
        }
        list.appendChild(el("li", null, text));
      });
      tooltip.appendChild(list);
    }
    tooltip.hidden = false;
    var width = this.host.clientWidth;
    var w = tooltip.offsetWidth;
    var h = tooltip.offsetHeight;
    var left = Math.min(Math.max(mark.cx - w / 2, 0), Math.max(width - w, 0));
    var top = mark.cy - h - 14;
    if (top < 0) top = mark.cy + 14;
    tooltip.style.left = left + "px";
    tooltip.style.top = top + "px";
  };

  // ------------------------------------------------------------ benchmarks

  function ecosystemPanel(eco, urls) {
    var panel = el("div", "eco-panel");
    var table = eco.per_call;

    var figure = el("figure", "chart-card");
    var caption = el("figcaption");
    caption.appendChild(el("p", "chart-title", "Median time of one call, " + eco.label));
    caption.appendChild(
      el(
        "p",
        "chart-subtitle",
        "Milliseconds, log scale. Lower is better. Each test has one row per package, in the order of the legend. " +
          "The thin vertical line marks the time of FastCIT. " +
          "An empty row means that the package has no test with this definition."
      )
    );
    var legend = el("ul", "legend");
    legend.setAttribute("aria-label", "Packages");
    var legendSlots = assignSlots(table.columns);
    table.columns.forEach(function (column, i) {
      var item = el("li", column.key === FOCUS_KEY ? "is-focus" : null);
      item.appendChild(swatch(legendSlots[i], column.key === FOCUS_KEY));
      item.appendChild(el("span", null, column.label));
      legend.appendChild(item);
    });
    caption.appendChild(legend);
    figure.appendChild(caption);
    var chartHost = el("div", "chart");
    figure.appendChild(chartHost);
    panel.appendChild(figure);
    panel.appendChild(verdictBox(table));
    panel.appendChild(footnoteList(table));
    var failures = failureList(table);
    if (failures) panel.appendChild(failures);
    panel.appendChild(runInfo(eco, urls));

    panel.appendChild(details("Show the numbers as a table", [dataTable(table, table.title + " (ms)")]));
    var total = eco.total_per_pass;
    if (total) {
      panel.appendChild(
        details("Show the total time of one pass", [
          total.note ? el("p", null, total.note) : null,
          dataTable(total, total.title + " (ms)"),
          footnoteList(total),
          verdictBox(total, "For the total time of one pass"),
        ])
      );
    }
    panel.appendChild(details("Show more about this run", [runDetails(eco.meta || {})]));
    // Draw after the panel is in the document, so that the chart can measure its width.
    panel.drawChart = function () {
      return new DotPlot(chartHost, table, eco.label);
    };
    return panel;
  }

  function renderBenchmarks(host, data, urls) {
    var ecosystems = (data.ecosystems || []).filter(function (eco) {
      return eco.per_call && eco.per_call.rows && eco.per_call.rows.length;
    });
    if (!ecosystems.length) throw new Error("benchmarks.json has no tables");
    if (data.quick) {
      host.appendChild(el("p", "bench-notice", "This is a quick run with few queries. The numbers are not final."));
    }
    var items = ecosystems.map(function (eco) {
      return { key: eco.key, label: eco.label, panel: ecosystemPanel(eco, urls) };
    });
    // Start on the ecosystem of the language that the reader chose last (sphinx-design's stored
    // choice, see languageKey); fall back to the first ecosystem.
    var key = languageKey();
    var stored = key ? readStorage(key) : null;
    ecosystemTabs = createTabs("Package ecosystem", items, stored, function () {
      ecosystemPicked = true;
    });
    host.appendChild(ecosystemTabs.tablist);
    items.forEach(function (item) {
      host.appendChild(item.panel);
      item.panel.drawChart();
    });
  }

  function loadBenchmarks() {
    var host = document.querySelector(".bench");
    if (!host) return;
    var urls = {
      benchmarks: host.getAttribute("data-benchmarks-url"),
      summary: host.getAttribute("data-summary-url"),
    };
    var status = el("p", "bench-status", "Loading the benchmark results.");
    host.appendChild(status);
    fetch(host.getAttribute("data-src"), { cache: "no-cache" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        host.removeChild(status);
        renderBenchmarks(host, data, urls);
      })
      .catch(function () {
        host.textContent = "";
        var message = el("p", "bench-notice", "The page cannot show the benchmark results. Read them in ");
        message.appendChild(link(urls.summary, "summary.md"));
        message.appendChild(document.createTextNode("."));
        host.appendChild(message);
      });
  }

  function init() {
    followLanguageTabs();
    loadBenchmarks();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
