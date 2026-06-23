(function () {
  const queuedOperations = Array.isArray(window.FGChartQueue) ? window.FGChartQueue.slice() : [];

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

  function datasetValues(dataset) {
    return (dataset && Array.isArray(dataset.data) ? dataset.data : []).map(function (value) {
      const numeric = Number(value);
      return Number.isFinite(numeric) ? numeric : 0;
    });
  }

  function hasRenderableData(config) {
    const labels = Array.isArray(config.labels) ? config.labels : [];
    const datasets = Array.isArray(config.datasets) ? config.datasets : [];
    if (!labels.length || !datasets.length) {
      return false;
    }
    return datasets.some(function (dataset) {
      return datasetValues(dataset).some(function (value) {
        return Math.abs(value) > 0;
      });
    });
  }

  function ensureEmptyState(canvas) {
    const shell = canvas.closest(".chart-shell") || canvas.parentElement;
    if (!shell) {
      return null;
    }
    let emptyState = shell.querySelector(".chart-empty-state");
    if (!emptyState) {
      emptyState = document.createElement("div");
      emptyState.className = "chart-empty-state";
      emptyState.textContent = "No data available for this period";
      shell.appendChild(emptyState);
    }
    return emptyState;
  }

  function setEmptyState(canvas, visible) {
    const emptyState = ensureEmptyState(canvas);
    if (!emptyState) {
      return;
    }
    emptyState.hidden = !visible;
    canvas.hidden = Boolean(visible);
  }

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

  function chartTheme() {
    const darkMode = document.documentElement.getAttribute("data-theme") === "dark";
    return {
      darkMode: darkMode,
      text: darkMode ? "#E7F0F1" : "#24373D",
      muted: darkMode ? "#A9BCC2" : "#596A70",
      grid: darkMode ? "rgba(231, 240, 241, 0.12)" : "rgba(32, 63, 70, 0.09)",
      tooltipBg: darkMode ? "#F4F7F8" : "#1D343A",
      tooltipTitle: darkMode ? "#102126" : "#FFFFFF",
      tooltipBody: darkMode ? "#23383F" : "#F6F8F8",
      radialCenter: darkMode ? "#0E1C21" : "#FFFFFF",
      axisLabel: darkMode ? "#D7E4E6" : "#596A70",
    };
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
      normalized.pointRadius = normalized.pointRadius === undefined ? 3 : normalized.pointRadius;
      normalized.pointHoverRadius = normalized.pointHoverRadius === undefined ? 5 : normalized.pointHoverRadius;
    }

    if (chartType === "bar") {
      normalized.borderRadius = normalized.borderRadius === undefined ? 8 : normalized.borderRadius;
      normalized.maxBarThickness = normalized.maxBarThickness === undefined ? 36 : normalized.maxBarThickness;
    }

    normalized.data = datasetValues(normalized);
    return normalized;
  }

  function formatTooltipValue(value, config) {
    const numberValue = Number(value);
    if (Number.isNaN(numberValue)) {
      return "0";
    }
    const formattedNumber = numberValue.toLocaleString(undefined, {
      maximumFractionDigits: config.tooltipDecimals === undefined ? 2 : config.tooltipDecimals,
    });
    if (config.tooltipPrefix) {
      return `${config.tooltipPrefix}${formattedNumber}`;
    }
    if (config.tooltipSuffix) {
      return `${formattedNumber}${config.tooltipSuffix}`;
    }
    return formattedNumber;
  }

  function legendDisplay(config) {
    if (typeof config.legend === "boolean") {
      return config.legend;
    }
    return config.type === "doughnut" || config.type === "pie" || (config.datasets || []).length > 1;
  }

  function chartOptions(config) {
    const radial = config.type === "doughnut" || config.type === "pie";
    const theme = chartTheme();
    return {
      responsive: true,
      maintainAspectRatio: false,
      resizeDelay: 100,
      animation: {
        duration: config.animationDuration === undefined ? 700 : config.animationDuration,
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
                color: theme.muted,
                maxRotation: 0,
                autoSkip: true,
                font: {
                  size: 11,
                  weight: "500",
                },
              },
              title: {
                display: true,
                text: config.xAxisTitle || "Period",
                color: theme.axisLabel,
                font: {
                  size: 11,
                  weight: "600",
                },
              },
            },
            y: {
              beginAtZero: true,
              grid: {
                color: theme.grid,
              },
              ticks: {
                color: theme.muted,
                precision: 0,
                font: {
                  size: 11,
                  weight: "500",
                },
              },
              title: {
                display: true,
                text: config.yAxisTitle || "Value",
                color: theme.axisLabel,
                font: {
                  size: 11,
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
            color: theme.text,
            font: {
              size: 12,
              weight: "500",
            },
            padding: 18,
          },
        },
        tooltip: {
          enabled: true,
          backgroundColor: theme.tooltipBg,
          titleColor: theme.tooltipTitle,
          bodyColor: theme.tooltipBody,
          borderColor: theme.darkMode ? "rgba(207, 174, 132, 0.28)" : "rgba(255, 255, 255, 0.12)",
          borderWidth: 1,
          padding: 12,
          displayColors: true,
          callbacks: {
            title: function (items) {
              const first = items && items[0];
              return first ? String(first.label || "Period") : "";
            },
            label: function (context) {
              const dataset = context.dataset || {};
              const label = dataset.label || context.label || "Value";
              const formattedValue = formatTooltipValue(context.raw, config);

              if (config.showPercentageTooltip && Array.isArray(dataset.rawValues)) {
                const rawValue = dataset.rawValues[context.dataIndex];
                return `${label}: ${rawValue === undefined || rawValue === null ? 0 : rawValue} (${formattedValue})`;
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

  function chartColorAt(color, index) {
    const normalized = normalizeColorInput(color);
    if (Array.isArray(normalized)) {
      return normalized[index % normalized.length] || defaultColorForIndex(index);
    }
    return normalized || defaultColorForIndex(index);
  }

  function prepareFallbackCanvas(canvas) {
    const theme = chartTheme();
    const shell = canvas.closest(".chart-shell") || canvas.parentElement;
    const rect = shell ? shell.getBoundingClientRect() : canvas.getBoundingClientRect();
    const width = Math.max(220, Math.floor(rect.width || canvas.clientWidth || 320));
    const height = Math.max(180, Math.floor(rect.height || canvas.clientHeight || 260));
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    const context = canvas.getContext("2d");
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);
    context.font = "12px Poppins, system-ui, sans-serif";
    context.fillStyle = theme.text;
    context.lineCap = "round";
    context.lineJoin = "round";
    return { context, width, height };
  }

  function roundedRectPath(context, x, y, width, height, radius) {
    const safeRadius = Math.min(radius, Math.abs(width) / 2, Math.abs(height) / 2);
    if (typeof context.roundRect === "function") {
      context.roundRect(x, y, width, height, safeRadius);
      return;
    }
    context.moveTo(x + safeRadius, y);
    context.lineTo(x + width - safeRadius, y);
    context.quadraticCurveTo(x + width, y, x + width, y + safeRadius);
    context.lineTo(x + width, y + height - safeRadius);
    context.quadraticCurveTo(x + width, y + height, x + width - safeRadius, y + height);
    context.lineTo(x + safeRadius, y + height);
    context.quadraticCurveTo(x, y + height, x, y + height - safeRadius);
    context.lineTo(x, y + safeRadius);
    context.quadraticCurveTo(x, y, x + safeRadius, y);
  }

  function drawFallbackLegend(context, labels, values, colors, x, y, maxWidth) {
    const theme = chartTheme();
    context.textBaseline = "middle";
    labels.slice(0, 6).forEach(function (label, index) {
      const rowY = y + index * 22;
      context.fillStyle = colors[index];
      context.beginPath();
      roundedRectPath(context, x, rowY - 5, 10, 10, 3);
      context.fill();
      context.fillStyle = theme.text;
      const text = `${label}: ${Number(values[index] || 0).toLocaleString()}`;
      context.fillText(text.length > 28 ? `${text.slice(0, 25)}...` : text, x + 16, rowY, maxWidth || 150);
    });
  }

  function drawFallbackRadial(canvas, config) {
    const prepared = prepareFallbackCanvas(canvas);
    const theme = chartTheme();
    const context = prepared.context;
    const width = prepared.width;
    const height = prepared.height;
    const labels = Array.isArray(config.labels) ? config.labels : [];
    const dataset = (config.datasets || [])[0] || {};
    const values = datasetValues(dataset);
    const total = values.reduce(function (sum, value) {
      return sum + Math.max(0, value);
    }, 0);
    const colors = values.map(function (_, index) {
      return chartColorAt(dataset.backgroundColor, index);
    });
    const hasWideLegend = width >= 360;
    const centerX = hasWideLegend ? width * 0.34 : width / 2;
    const centerY = hasWideLegend ? height / 2 : Math.max(86, height * 0.42);
    const radius = Math.max(54, Math.min(hasWideLegend ? width * 0.22 : width * 0.28, height * 0.32));
    const cutoutRatio = config.type === "doughnut" ? 0.62 : 0;
    let current = -Math.PI / 2;

    values.forEach(function (value, index) {
      const slice = total > 0 ? (Math.max(0, value) / total) * Math.PI * 2 : 0;
      context.beginPath();
      context.moveTo(centerX, centerY);
      context.arc(centerX, centerY, radius, current, current + slice);
      context.closePath();
      context.fillStyle = colors[index];
      context.fill();
      current += slice;
    });

    if (cutoutRatio) {
      context.beginPath();
      context.arc(centerX, centerY, radius * cutoutRatio, 0, Math.PI * 2);
      context.fillStyle = theme.radialCenter;
      context.fill();
    }

    context.fillStyle = theme.text;
    context.textAlign = "center";
    context.font = "700 20px Poppins, system-ui, sans-serif";
    context.fillText(total.toLocaleString(), centerX, centerY + 4);
    context.font = "500 11px Poppins, system-ui, sans-serif";
    context.fillStyle = theme.muted;
    context.fillText("Total", centerX, centerY + 23);

    context.textAlign = "left";
    drawFallbackLegend(
      context,
      labels,
      values,
      colors,
      hasWideLegend ? width * 0.62 : 18,
      hasWideLegend ? Math.max(44, centerY - labels.length * 9) : height - Math.min(88, labels.length * 20),
      hasWideLegend ? width * 0.34 : width - 36
    );
  }

  function drawFallbackCartesian(canvas, config) {
    const prepared = prepareFallbackCanvas(canvas);
    const theme = chartTheme();
    const context = prepared.context;
    const width = prepared.width;
    const height = prepared.height;
    const labels = Array.isArray(config.labels) ? config.labels : [];
    const datasets = (config.datasets || []).map(function (dataset, index) {
      return normalizeDataset(dataset, index, config.type);
    });
    const values = datasets.reduce(function (allValues, dataset) {
      return allValues.concat(datasetValues(dataset));
    }, []);
    const maxValue = Math.max(1, Math.max.apply(null, values));
    const left = 48;
    const right = 18;
    const top = 18;
    const bottom = 44;
    const chartWidth = width - left - right;
    const chartHeight = height - top - bottom;
    const labelStep = Math.max(1, Math.ceil(labels.length / 6));

    context.strokeStyle = theme.grid;
    context.lineWidth = 1;
    context.fillStyle = theme.muted;
    context.textAlign = "right";
    context.textBaseline = "middle";
    for (let tick = 0; tick <= 4; tick += 1) {
      const value = (maxValue / 4) * tick;
      const y = top + chartHeight - (value / maxValue) * chartHeight;
      context.beginPath();
      context.moveTo(left, y);
      context.lineTo(width - right, y);
      context.stroke();
      context.fillText(Math.round(value).toLocaleString(), left - 8, y);
    }

    context.textAlign = "center";
    context.textBaseline = "top";
    labels.forEach(function (label, index) {
      if (index % labelStep !== 0 && index !== labels.length - 1) {
        return;
      }
      const x = left + (labels.length <= 1 ? chartWidth / 2 : (index / (labels.length - 1)) * chartWidth);
      context.fillText(String(label), x, height - bottom + 18);
    });

    if (config.type === "bar") {
      const groupWidth = chartWidth / Math.max(1, labels.length);
      const barWidth = Math.min(34, (groupWidth * 0.72) / Math.max(1, datasets.length));
      datasets.forEach(function (dataset, datasetIndex) {
        const color = chartColorAt(dataset.backgroundColor || dataset.borderColor, datasetIndex);
        datasetValues(dataset).forEach(function (value, index) {
          const groupX = left + index * groupWidth + groupWidth / 2;
          const x = groupX - (barWidth * datasets.length) / 2 + datasetIndex * barWidth;
          const barHeight = (Math.max(0, value) / maxValue) * chartHeight;
          const y = top + chartHeight - barHeight;
          context.fillStyle = color;
          context.beginPath();
          roundedRectPath(context, x, y, Math.max(4, barWidth - 3), barHeight, 7);
          context.fill();
        });
      });
      return;
    }

    datasets.forEach(function (dataset, datasetIndex) {
      const color = chartColorAt(dataset.borderColor || dataset.backgroundColor, datasetIndex);
      const points = datasetValues(dataset).map(function (value, index) {
        return {
          x: left + (labels.length <= 1 ? chartWidth / 2 : (index / (labels.length - 1)) * chartWidth),
          y: top + chartHeight - (Math.max(0, value) / maxValue) * chartHeight,
        };
      });
      if (dataset.fill || dataset.gradientFill) {
        context.beginPath();
        points.forEach(function (point, index) {
          if (index === 0) {
            context.moveTo(point.x, top + chartHeight);
            context.lineTo(point.x, point.y);
          } else {
            context.lineTo(point.x, point.y);
          }
        });
        if (points.length) {
          context.lineTo(points[points.length - 1].x, top + chartHeight);
        }
        context.closePath();
        context.fillStyle = withAlpha(color, 0.13);
        context.fill();
      }
      context.beginPath();
      points.forEach(function (point, index) {
        if (index === 0) {
          context.moveTo(point.x, point.y);
        } else {
          context.lineTo(point.x, point.y);
        }
      });
      context.strokeStyle = color;
      context.lineWidth = 3;
      context.stroke();
      context.fillStyle = color;
      points.forEach(function (point) {
        context.beginPath();
        context.arc(point.x, point.y, 3, 0, Math.PI * 2);
        context.fill();
      });
    });
  }

  function drawFallbackChart(canvas, config) {
    if (canvas._fgFallbackResize) {
      window.removeEventListener("resize", canvas._fgFallbackResize);
    }
    const normalizedConfig = Object.assign({}, config || {});
    if (normalizedConfig.type === "doughnut" || normalizedConfig.type === "pie") {
      drawFallbackRadial(canvas, normalizedConfig);
    } else {
      drawFallbackCartesian(canvas, normalizedConfig);
    }
    canvas.title = "Chart rendered from live system data";
    canvas._fgFallbackResize = function () {
      window.clearTimeout(canvas._fgFallbackResizeTimer);
      canvas._fgFallbackResizeTimer = window.setTimeout(function () {
        drawFallbackChart(canvas, normalizedConfig);
      }, 120);
    };
    window.addEventListener("resize", canvas._fgFallbackResize);
    canvas._fgChart = {
      destroy: function () {
        if (canvas._fgFallbackResize) {
          window.removeEventListener("resize", canvas._fgFallbackResize);
          canvas._fgFallbackResize = null;
        }
        const context = canvas.getContext("2d");
        context.clearRect(0, 0, canvas.width, canvas.height);
      },
    };
    return canvas._fgChart;
  }

  function upsert(canvas, config) {
    if (!canvas) {
      return null;
    }
    if (canvas._fgChart) {
      canvas._fgChart.destroy();
      canvas._fgChart = null;
    }
    const normalizedConfig = Object.assign({}, config || {});
    canvas._fgChartConfig = normalizedConfig;
    canvas.dataset.fgChart = "true";
    normalizedConfig.labels = Array.isArray(normalizedConfig.labels) ? normalizedConfig.labels : [];
    normalizedConfig.datasets = Array.isArray(normalizedConfig.datasets) ? normalizedConfig.datasets : [];

    if (!hasRenderableData(normalizedConfig)) {
      setEmptyState(canvas, true);
      return null;
    }
    if (!window.Chart) {
      setEmptyState(canvas, false);
      return drawFallbackChart(canvas, normalizedConfig);
    }
    setEmptyState(canvas, false);
    canvas._fgChart = new window.Chart(canvas, buildChartConfig(normalizedConfig));
    return canvas._fgChart;
  }

  function refreshTheme() {
    document.querySelectorAll("canvas[data-fg-chart='true']").forEach(function (canvas) {
      if (canvas._fgChartConfig) {
        upsert(canvas, canvas._fgChartConfig);
      }
    });
  }

  function renderMany(configs) {
    (configs || []).forEach(function (config) {
      upsert(document.getElementById(config.id), config);
    });
  }

  window.FGCharts = {
    ready: true,
    palette: palette,
    withAlpha: withAlpha,
    upsert: upsert,
    renderMany: renderMany,
    refreshTheme: refreshTheme,
  };

  window.addEventListener("fg:themechange", refreshTheme);

  queuedOperations.forEach(function (operation) {
    if (!operation || !operation.method) {
      return;
    }
    if (operation.method === "upsert") {
      upsert(operation.canvas, operation.config);
    }
    if (operation.method === "renderMany") {
      renderMany(operation.configs);
    }
  });
  window.FGChartQueue = [];
})();
