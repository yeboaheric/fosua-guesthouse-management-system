(function () {
  const palette = {
    deep: "#2F8A57",
    gold: "#CFAE84",
    sage: "#38585F",
    bronze: "#8F6F4F",
    sand: "#E7D6BE",
    mist: "#DCE8E5",
  };

  const oldColorMap = new Map([
    ["#23444b", palette.deep],
    ["#1f3b44", palette.deep],
    ["#203f46", palette.deep],
    ["#3d7dff", palette.gold],
    ["#c7ab83", palette.gold],
    ["#f4b942", palette.gold],
    ["#78c0a8", palette.sage],
    ["#62c7ff", palette.sage],
    ["#167d47", palette.sage],
    ["#d95d39", palette.bronze],
    ["#ff8b64", palette.bronze],
    ["#8f6f4f", palette.bronze],
    ["#a06cd5", palette.sand],
    ["#8b6fff", palette.sand],
    ["#ff5fd2", palette.sand],
    ["#6c757d", "#6C7A80"],
    ["#9b6b00", "#B38A5E"],
    ["#b32836", "#A66A60"],
  ]);

  function clampAlpha(value) {
    return Math.max(0, Math.min(1, value));
  }

  function hexToRgb(hex) {
    const normalized = hex.replace("#", "");
    if (normalized.length !== 6) {
      return null;
    }
    return {
      r: parseInt(normalized.slice(0, 2), 16),
      g: parseInt(normalized.slice(2, 4), 16),
      b: parseInt(normalized.slice(4, 6), 16),
    };
  }

  function withAlpha(hex, alpha) {
    const rgb = hexToRgb(hex);
    if (!rgb) {
      return hex;
    }
    return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${clampAlpha(alpha)})`;
  }

  function mapColorString(color) {
    if (typeof color !== "string") {
      return color;
    }

    const normalized = color.trim().toLowerCase();
    if (oldColorMap.has(normalized)) {
      return oldColorMap.get(normalized);
    }

    const rgbaMatch = normalized.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([0-9.]+))?\)$/);
    if (rgbaMatch) {
      const r = Number(rgbaMatch[1]);
      const g = Number(rgbaMatch[2]);
      const b = Number(rgbaMatch[3]);
      const alpha = rgbaMatch[4] === undefined ? 1 : Number(rgbaMatch[4]);
      const rgbKey = `#${[r, g, b].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
      const mapped = oldColorMap.get(rgbKey);
      if (mapped) {
        return withAlpha(mapped, alpha);
      }
    }

    return color;
  }

  function normalizeColorInput(input) {
    if (Array.isArray(input)) {
      return input.map(normalizeColorInput);
    }
    return mapColorString(input);
  }

  function createLineGradient(context, color) {
    const chart = context.chart;
    const chartArea = chart.chartArea;
    if (!chartArea) {
      return withAlpha(color, 0.18);
    }
    const gradient = chart.ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    gradient.addColorStop(0, withAlpha(color, 0.24));
    gradient.addColorStop(1, withAlpha(color, 0.03));
    return gradient;
  }

  function defaultColorForIndex(index) {
    return [palette.deep, palette.gold, palette.sage, palette.bronze, palette.sand, "#6C7A80"][index % 6];
  }

  function normalizeDataset(dataset, index, chartType) {
    const color = mapColorString(dataset.borderColor || dataset.backgroundColor || defaultColorForIndex(index));
    const normalized = Object.assign({}, dataset);

    if (!normalized.borderColor && chartType !== "doughnut" && chartType !== "pie") {
      normalized.borderColor = color;
    } else if (normalized.borderColor) {
      normalized.borderColor = normalizeColorInput(normalized.borderColor);
    }

    if (normalized.backgroundColor) {
      normalized.backgroundColor = normalizeColorInput(normalized.backgroundColor);
    } else if (chartType === "doughnut" || chartType === "pie" || chartType === "bar") {
      normalized.backgroundColor = color;
    } else {
      normalized.backgroundColor = withAlpha(color, 0.18);
    }

    if (normalized.gradientFill) {
      const gradientBase = typeof normalized.borderColor === "string" ? normalized.borderColor : color;
      normalized.backgroundColor = function (context) {
        return createLineGradient(context, gradientBase);
      };
      normalized.fill = true;
    }

    if (chartType === "line") {
      normalized.borderWidth = normalized.borderWidth || 3;
      normalized.pointBackgroundColor = normalized.pointBackgroundColor || (typeof normalized.borderColor === "string" ? normalized.borderColor : color);
    }

    return normalized;
  }

  function formatTooltipValue(value, config) {
    const numberValue = Number(value);
    if (Number.isNaN(numberValue)) {
      return value;
    }
    if (config.tooltipPrefix) {
      return `${config.tooltipPrefix}${numberValue.toLocaleString()}`;
    }
    if (config.tooltipSuffix) {
      return `${numberValue.toLocaleString()}${config.tooltipSuffix}`;
    }
    return numberValue.toLocaleString();
  }

  function legendDisplay(config) {
    if (typeof config.legend === "boolean") {
      return config.legend;
    }
    return config.type === "doughnut" || config.type === "pie" || (config.datasets || []).length > 1;
  }

  function chartOptions(config) {
    const radial = config.type === "doughnut" || config.type === "pie";
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 700,
        easing: "easeOutCubic",
      },
      interaction: {
        mode: radial ? "nearest" : "index",
        intersect: false,
      },
      cutout: config.cutout,
      scales: radial
        ? {}
        : {
            x: {
              grid: {
                display: false,
              },
              ticks: {
                color: "#596A70",
                maxRotation: 0,
                autoSkip: true,
              },
              title: {
                display: Boolean(config.xAxisTitle),
                text: config.xAxisTitle || "Period",
                color: "#596A70",
                font: {
                  weight: "600",
                },
              },
            },
            y: {
              beginAtZero: true,
              grid: {
                color: "rgba(32, 63, 70, 0.09)",
              },
              ticks: {
                color: "#596A70",
                precision: 0,
              },
              title: {
                display: Boolean(config.yAxisTitle),
                text: config.yAxisTitle || "Value",
                color: "#596A70",
                font: {
                  weight: "600",
                },
              },
            },
          },
      plugins: {
        legend: {
          display: legendDisplay(config),
          position: config.legendPosition || "bottom",
          labels: {
            usePointStyle: true,
            boxWidth: 10,
            color: "#24373D",
            padding: 18,
          },
        },
        tooltip: {
          enabled: true,
          backgroundColor: "#1D343A",
          titleColor: "#FFFFFF",
          bodyColor: "#F6F8F8",
          padding: 12,
          displayColors: true,
          callbacks: {
            label: function (context) {
              const dataset = context.dataset || {};
              const label = dataset.label || context.label || "Value";
              const formattedValue = formatTooltipValue(context.raw, config);

              if (config.showPercentageTooltip && Array.isArray(dataset.rawValues)) {
                const rawValue = dataset.rawValues[context.dataIndex];
                return `${label}: ${rawValue} (${formattedValue})`;
              }

              return `${label}: ${formattedValue}`;
            },
          },
        },
      },
    };
  }

  function buildChartConfig(config) {
    return {
      type: config.type,
      data: {
        labels: config.labels,
        datasets: (config.datasets || []).map(function (dataset, index) {
          return normalizeDataset(dataset, index, config.type);
        }),
      },
      options: chartOptions(config),
    };
  }

  function upsert(canvas, config) {
    if (!canvas || !window.Chart) {
      return null;
    }
    if (canvas._fgChart) {
      canvas._fgChart.destroy();
    }
    canvas._fgChart = new window.Chart(canvas, buildChartConfig(config));
    return canvas._fgChart;
  }

  function renderMany(configs) {
    (configs || []).forEach(function (config) {
      upsert(document.getElementById(config.id), config);
    });
  }

  window.FGCharts = {
    palette: palette,
    withAlpha: withAlpha,
    upsert: upsert,
    renderMany: renderMany,
  };
})();
