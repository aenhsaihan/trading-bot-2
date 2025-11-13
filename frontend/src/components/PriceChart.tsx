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

    console.log("PriceChart: Creating chart instance");

    try {
      setChartError(null);

      // Create chart
      const chart = createChart(chartContainerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: "#0f0f1e" },
          textColor: "#d1d5db",
        },
        grid: {
          vertLines: { color: "#1f2937" },
          horzLines: { color: "#1f2937" },
        },
        width: chartContainerRef.current.clientWidth,
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
      console.log("PriceChart: Chart methods check", {
        hasAddCandlestickSeries:
          typeof (chart as any).addCandlestickSeries === "function",
        hasAddLineSeries: typeof (chart as any).addLineSeries === "function",
        hasAddAreaSeries: typeof (chart as any).addAreaSeries === "function",
      });

      chartRef.current = chart;

      // Handle resize
      const handleResize = () => {
        if (chartContainerRef.current && chart) {
          chart.applyOptions({
            width: chartContainerRef.current.clientWidth,
          });
        }
      };

      window.addEventListener("resize", handleResize);

      return () => {
        window.removeEventListener("resize", handleResize);
        try {
          chart.remove();
        } catch (e) {
          console.warn("Error removing chart:", e);
        }
      };
    } catch (error) {
      console.error("Error creating chart:", error);
      setChartError(
        error instanceof Error ? error.message : "Failed to create chart"
      );
    }
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
      const chartData = candles
        .filter((c) => c.timestamp && c.open && c.high && c.low && c.close)
        .map((candle) => {
          const time = Math.floor(candle.timestamp / 1000);
          return {
            time: time as Time, // Convert milliseconds to seconds
            open: Number(candle.open),
            high: Number(candle.high),
            low: Number(candle.low),
            close: Number(candle.close),
          };
        });

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
      className="w-full"
      style={{ height: `${height}px` }}
    >
      {(!candles || candles.length === 0) && (
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <div className="text-sm">No chart data available</div>
          </div>
        </div>
      )}
    </div>
  );
}
