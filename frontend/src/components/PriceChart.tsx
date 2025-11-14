import { useEffect, useRef, useState } from "react";
import {
  createChart,
  IChartApi,
  ISeriesApi,
  ColorType,
  Time,
  CandlestickSeries,
  LineSeries,
  AreaSeries,
} from "lightweight-charts";
import { Candle } from "../services/api";

interface PriceChartProps {
  candles: Candle[];
  symbol: string;
  chartType?: "candles" | "line" | "area";
  height?: number;
}

export function PriceChart({
  candles,
  chartType = "candles",
  height = 400,
}: PriceChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick" | "Line" | "Area"> | null>(
    null
  );
  const [chartError, setChartError] = useState<string | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) {
      console.log("PriceChart: Container ref not ready");
      return;
    }

    // Ensure container has width before creating chart
    const container = chartContainerRef.current;
    let chart: IChartApi | null = null;
    let timeoutId: NodeJS.Timeout | null = null;

    const createChartInstance = (width: number) => {
      console.log("PriceChart: Creating chart instance with width", width);

      try {
        setChartError(null);

        // Create chart
        chart = createChart(container, {
          layout: {
            background: { type: ColorType.Solid, color: "#0f0f1e" },
            textColor: "#d1d5db",
          },
          grid: {
            vertLines: { color: "#1f2937" },
            horzLines: { color: "#1f2937" },
          },
          width: width,
          height: height,
          timeScale: {
            timeVisible: true,
            secondsVisible: false,
            borderColor: "#374151",
          },
          rightPriceScale: {
            borderColor: "#374151",
          },
        });

        console.log("PriceChart: Chart created successfully", chart);

        chartRef.current = chart;

        // Use ResizeObserver for better container size tracking
        const resizeObserver = new ResizeObserver((entries) => {
          for (const entry of entries) {
            const newWidth = entry.contentRect.width;
            if (newWidth > 0 && chart) {
              chart.applyOptions({
                width: newWidth,
              });
            }
          }
        });

        resizeObserver.observe(container);

        // Also handle window resize as fallback
        const handleResize = () => {
          if (container && chart) {
            const newWidth = container.clientWidth || container.offsetWidth;
            if (newWidth > 0) {
              chart.applyOptions({
                width: newWidth,
              });
            }
          }
        };

        window.addEventListener("resize", handleResize);

        // Store cleanup function
        return () => {
          resizeObserver.disconnect();
          window.removeEventListener("resize", handleResize);
          try {
            if (chart) {
              chart.remove();
            }
          } catch (e) {
            console.warn("Error removing chart:", e);
          }
        };
      } catch (error) {
        console.error("Error creating chart:", error);
        setChartError(
          error instanceof Error ? error.message : "Failed to create chart"
        );
        return () => {}; // Return empty cleanup on error
      }
    };

    const containerWidth =
      container.clientWidth || container.offsetWidth || 800;
    let cleanupFn: (() => void) | null = null;

    if (containerWidth === 0) {
      console.log("PriceChart: Container width is 0, waiting for layout");
      // Use a small timeout to wait for layout
      timeoutId = setTimeout(() => {
        const width = container.clientWidth || container.offsetWidth || 800;
        if (width > 0) {
          cleanupFn = createChartInstance(width);
        }
      }, 100);
    } else {
      cleanupFn = createChartInstance(containerWidth);
    }

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      if (cleanupFn) {
        cleanupFn();
      }
      if (chart) {
        try {
          chart.remove();
        } catch (e) {
          console.warn("Error removing chart:", e);
        }
      }
    };
  }, [height]);

  useEffect(() => {
    if (!chartRef.current) {
      console.log(
        "PriceChart: chartRef.current is null, waiting for chart to initialize"
      );
      return;
    }

    if (!candles || !candles.length) {
      console.log("PriceChart: No candles data available", {
        candlesLength: candles?.length,
      });
      return;
    }

    console.log("PriceChart: Rendering chart with", candles.length, "candles");

    try {
      // Remove existing series
      if (seriesRef.current) {
        try {
          chartRef.current.removeSeries(seriesRef.current);
        } catch (e) {
          console.warn("Error removing series:", e);
        }
        seriesRef.current = null;
      }

      // Prepare data - lightweight-charts expects Unix timestamp in seconds
      // Sort by timestamp to ensure ascending order (required by lightweight-charts)
      const chartData = candles
        .filter((c) => c.timestamp && c.open && c.high && c.low && c.close)
        .map((candle) => ({
          time: Math.floor(candle.timestamp / 1000) as Time, // Convert milliseconds to seconds
          open: Number(candle.open),
          high: Number(candle.high),
          low: Number(candle.low),
          close: Number(candle.close),
          originalTimestamp: candle.timestamp, // Keep for sorting
        }))
        .sort((a, b) => {
          // Sort by original timestamp in ascending order
          return a.originalTimestamp - b.originalTimestamp;
        })
        .map(({ originalTimestamp, ...rest }) => rest); // Remove helper field

      if (chartData.length === 0) {
        console.warn("No valid chart data after filtering");
        return;
      }

      // Verify chart instance exists
      if (!chartRef.current) {
        throw new Error("Chart instance is null");
      }

      const chart = chartRef.current;

      // Create series based on chart type using the new v5 API (addSeries)
      let series: ISeriesApi<"Candlestick" | "Line" | "Area">;

      if (chartType === "candles") {
        // Use addSeries with CandlestickSeries class
        series = chart.addSeries(CandlestickSeries, {
          upColor: "#10b981",
          downColor: "#ef4444",
          borderVisible: false,
          wickUpColor: "#10b981",
          wickDownColor: "#ef4444",
        }) as ISeriesApi<"Candlestick">;
        series.setData(chartData);
      } else if (chartType === "line") {
        // Use addSeries with LineSeries class
        series = chart.addSeries(LineSeries, {
          color: "#3b82f6",
          lineWidth: 2,
          priceFormat: {
            type: "price",
            precision: 2,
            minMove: 0.01,
          },
        }) as ISeriesApi<"Line">;
        // For line chart, use close prices
        const lineData = chartData.map((d) => ({
          time: d.time,
          value: d.close,
        }));
        series.setData(lineData);
      } else {
        // Area chart - Use addSeries with AreaSeries class
        series = chart.addSeries(AreaSeries, {
          lineColor: "#3b82f6",
          topColor: "rgba(59, 130, 246, 0.2)",
          bottomColor: "rgba(59, 130, 246, 0)",
          lineWidth: 2,
        }) as ISeriesApi<"Area">;
        // For area chart, use close prices
        const areaData = chartData.map((d) => ({
          time: d.time,
          value: d.close,
        }));
        series.setData(areaData);
      }

      seriesRef.current = series;

      // Fit content
      chartRef.current.timeScale().fitContent();
    } catch (error) {
      console.error("Error rendering chart:", error);
      setChartError(
        error instanceof Error ? error.message : "Failed to render chart"
      );
    }
  }, [candles, chartType]);

  // Show error state if there's an error
  if (chartError) {
    return (
      <div
        className="flex items-center justify-center h-full text-red-400"
        style={{ height: `${height}px` }}
      >
        <div className="text-center">
          <div className="text-sm">Chart Error: {chartError}</div>
        </div>
      </div>
    );
  }

  // Always render the container so hooks can run
  // The chart will render when data is available
  return (
    <div
      ref={chartContainerRef}
      className="w-full relative overflow-hidden"
      style={{ height: `${height}px`, minWidth: "100px", width: "100%" }}
    >
      {(!candles || candles.length === 0) && (
        <div className="flex items-center justify-center h-full text-gray-500 absolute inset-0">
          <div className="text-center">
            <div className="text-sm">No chart data available</div>
          </div>
        </div>
      )}
    </div>
  );
}
