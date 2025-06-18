import { useState, useEffect, useRef } from "react";
import { createChart } from "lightweight-charts";

const TIMEFRAMES = ["1m", "5m", "15m", "1h"];

export default function LiveCharts() {
  const [symbols, setSymbols] = useState([]);
  const [symbol, setSymbol] = useState("BTCUSD");
  const [timeframe, setTimeframe] = useState("1m");
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const socketRef = useRef(null);

  // Cargar lista de símbolos desde el backend
  useEffect(() => {
    fetch("http://localhost:8000/core/api/symbols/")
      .then((res) => res.json())
      .then((data) => {
        setSymbols(data);
        if (data.length > 0 && !symbol) {
          setSymbol(data[0].symbol);
        }
      });
  }, []);

  // Crear gráfico una sola vez
  useEffect(() => {
    const chart = createChart(chartContainerRef.current, {
  width: chartContainerRef.current.clientWidth,
  height: 400,
  layout: {
    backgroundColor: "#ffffff",
    textColor: "#111827", // Tailwind gray-900
  },
  grid: {
    vertLines: { color: "#e5e7eb" }, // Tailwind gray-200
    horzLines: { color: "#e5e7eb" },
  },
  crosshair: {
    mode: 1,
  },
  timeScale: {
    timeVisible: true,
    secondsVisible: false,
    borderColor: "#d1d5db", // Tailwind gray-300
  },
});


    const candleSeries = chart.addCandlestickSeries();
    chartRef.current = chart;
    seriesRef.current = candleSeries;

    return () => chart.remove();
  }, []);

  // Cargar histórico + WebSocket
  useEffect(() => {
    if (!symbol || !timeframe) return;

    const loadCandles = async () => {
      const res = await fetch(`http://localhost:8000/core/api/market_data/${symbol}/?tf=${timeframe}`);
      const data = await res.json();

      const formatted = data.map((c) => ({
        time: Math.floor(new Date(c.start_time).getTime() / 1000),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));

      seriesRef.current.setData(formatted);
    };

    loadCandles();

    if (socketRef.current) {
      socketRef.current.close();
    }

    const socket = new WebSocket(`ws://localhost:8000/ws/market/${symbol}/`);
    socketRef.current = socket;

    socket.onmessage = (event) => {
      const d = JSON.parse(event.data);
      if (!d.timestamp) return;

      seriesRef.current.update({
        time: Math.floor(new Date(d.timestamp).getTime() / 1000),
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      });
    };

    return () => socket.close();
  }, [symbol, timeframe]);

  return (
    <div className="p-6 bg-white min-h-screen text-gray-900">

      <h2 className="text-xl font-bold mb-4">📊 Live Trading Chart</h2>

      {/* Selector visual de símbolos con logos */}
      <div className="relative overflow-hidden h-[56px] mb-6">
  <div
    className="flex gap-4 absolute animate-[ticker_40s_linear_infinite] will-change-transform"
    style={{
      animation: "ticker 40s linear infinite",
    }}
  >
    {[...symbols, ...symbols].map((s, idx) => (
      <div
        key={`${s.symbol}-${idx}`}
        onClick={() => setSymbol(s.symbol)}
        className={`flex-shrink-0 cursor-pointer px-4 py-2 rounded-full flex items-center gap-2 whitespace-nowrap border-2 ${
          symbol === s.symbol
            ? "bg-indigo-600 text-white border-indigo-600"
            : "bg-white text-gray-800 border-gray-300 hover:bg-gray-100"
        }`}
      >
        <img
  src={`/images/crypto/${s.symbol}.png`}
  alt={s.symbol}
  className="w-5 h-5"
/>

        <span className="font-semibold text-sm">{s.symbol}</span>
      </div>
    ))}
  </div>

  {/* Inline keyframes CSS */}
  <style>{`
    @keyframes ticker {
      0% { transform: translateX(0%); }
      100% { transform: translateX(-50%); }
    }
  `}</style>
</div>




      {/* Selector de timeframe */}
      <div className="flex gap-4 items-center mb-4">
        <label className="font-semibold">Timeframe:</label>
        <select
          className="border px-3 py-2 rounded shadow bg-white text-black"
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
        >
          {TIMEFRAMES.map((tf) => (
            <option key={tf}>{tf}</option>
          ))}
        </select>
      </div>

      {/* Contenedor del gráfico */}
      <div
        ref={chartContainerRef}
        className="w-full h-[400px] bg-gray-800 rounded shadow"
      />
    </div>
  );
}
