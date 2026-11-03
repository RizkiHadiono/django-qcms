(function () {
  "use strict";

  const dataElement = document.getElementById("chart-data");
  if (!dataElement || typeof Chart === "undefined") return;

  const data = JSON.parse(dataElement.textContent);
  const NAVY = "#102a43";
  const ACCENT = "#0ea5a4";
  const DANGER = "#d64545";
  const WARNING = "#d97706";
  const GREEN = "#12805c";
  const PALETTE = [NAVY, ACCENT, WARNING, DANGER, "#6366f1", "#0891b2", "#7c3aed", "#059669"];

  Chart.defaults.font.family =
    '"Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif';
  Chart.defaults.font.size = 11;
  Chart.defaults.color = "#6b7c93";

  function ctx(id) {
    const canvas = document.getElementById(id);
    return canvas ? canvas.getContext("2d") : null;
  }

  function rupiah(value) {
    return new Intl.NumberFormat("id-ID").format(value);
  }

  /* Tren defect rate + volume */
  if (data.trend && ctx("chart-trend")) {
    const threshold = new Array(data.trend.labels.length).fill(data.trend.threshold);
    new Chart(ctx("chart-trend"), {
      data: {
        labels: data.trend.labels,
        datasets: [
          {
            type: "bar",
            label: "Diperiksa",
            data: data.trend.inspected,
            backgroundColor: "rgba(14, 165, 164, 0.18)",
            borderColor: "rgba(14, 165, 164, 0.4)",
            borderWidth: 1,
            yAxisID: "y1",
            order: 3,
          },
          {
            type: "line",
            label: "Defect Rate (%)",
            data: data.trend.rates,
            borderColor: DANGER,
            backgroundColor: "rgba(214, 69, 69, 0.08)",
            tension: 0.3,
            pointRadius: 3,
            fill: true,
            yAxisID: "y",
            order: 1,
          },
          {
            type: "line",
            label: "Ambang (%)",
            data: threshold,
            borderColor: WARNING,
            borderDash: [6, 4],
            pointRadius: 0,
            borderWidth: 1.5,
            yAxisID: "y",
            order: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, usePointStyle: true } },
          tooltip: {
            callbacks: {
              label: function (context) {
                if (context.dataset.yAxisID === "y1") {
                  return context.dataset.label + ": " + rupiah(context.parsed.y);
                }
                return context.dataset.label + ": " + context.parsed.y.toFixed(2) + "%";
              },
            },
          },
        },
        scales: {
          y: {
            position: "left",
            beginAtZero: true,
            ticks: { callback: (value) => value + "%" },
            grid: { color: "#eef2f7" },
          },
          y1: {
            position: "right",
            beginAtZero: true,
            grid: { display: false },
            ticks: { callback: (value) => rupiah(value) },
          },
          x: { grid: { display: false } },
        },
      },
    });
  }

  /* Pareto kecacatan */
  if (data.pareto && ctx("chart-pareto")) {
    new Chart(ctx("chart-pareto"), {
      data: {
        labels: data.pareto.labels,
        datasets: [
          {
            type: "bar",
            label: "Kejadian",
            data: data.pareto.totals,
            backgroundColor: NAVY,
            borderRadius: 4,
            yAxisID: "y",
            order: 2,
          },
          {
            type: "line",
            label: "Kumulatif (%)",
            data: data.pareto.cumulative,
            borderColor: WARNING,
            backgroundColor: WARNING,
            tension: 0.25,
            pointRadius: 3,
            yAxisID: "y1",
            order: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, usePointStyle: true } },
          tooltip: {
            callbacks: {
              label: function (context) {
                if (context.dataset.yAxisID === "y1") {
                  return context.dataset.label + ": " + context.parsed.y.toFixed(1) + "%";
                }
                return context.dataset.label + ": " + rupiah(context.parsed.y);
              },
            },
          },
        },
        scales: {
          y: { beginAtZero: true, grid: { color: "#eef2f7" }, ticks: { precision: 0 } },
          y1: {
            position: "right",
            beginAtZero: true,
            max: 100,
            grid: { display: false },
            ticks: { callback: (value) => value + "%" },
          },
          x: { grid: { display: false }, ticks: { autoSkip: false, maxRotation: 40, minRotation: 0 } },
        },
      },
    });
  }

  /* Severity */
  if (data.severity && ctx("chart-severity")) {
    new Chart(ctx("chart-severity"), {
      type: "doughnut",
      data: {
        labels: data.severity.labels,
        datasets: [
          {
            data: data.severity.totals,
            backgroundColor: [DANGER, WARNING, "#6366f1"],
            borderWidth: 2,
            borderColor: "#fff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, usePointStyle: true } },
        },
      },
    });
  }

  /* Komposisi lolos vs cacat */
  if (data.composition && ctx("chart-composition")) {
    new Chart(ctx("chart-composition"), {
      type: "doughnut",
      data: {
        labels: data.composition.labels,
        datasets: [
          {
            data: data.composition.totals,
            backgroundColor: [GREEN, DANGER],
            borderWidth: 2,
            borderColor: "#fff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, usePointStyle: true } },
          tooltip: {
            callbacks: {
              label: function (context) {
                return context.label + ": " + rupiah(context.parsed) + " unit";
              },
            },
          },
        },
      },
    });
  }

  /* Perbandingan per lini */
  if (data.lines && ctx("chart-lines")) {
    new Chart(ctx("chart-lines"), {
      type: "bar",
      data: {
        labels: data.lines.labels,
        datasets: [
          {
            label: "Defect Rate (%)",
            data: data.lines.rates,
            backgroundColor: PALETTE,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { callback: (value) => value + "%" },
            grid: { color: "#eef2f7" },
          },
          x: { grid: { display: false } },
        },
      },
    });
  }
})();
