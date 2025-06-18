import React, { useEffect, useState, useRef } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  TimeScale,
  Tooltip,
  Legend,
  Filler,
  Title,
} from "chart.js";
import "chartjs-adapter-date-fns";

ChartJS.register(
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  TimeScale,
  Tooltip,
  Legend,
  Filler,
  Title
);

const MarketChart = ({ ticker = "BTCUSD" }) => {
  const [chartData, setChartData] = useState({ labels: [], datasets: [] });
  const wsRef = useRef(null);
  const dataRef = useRef([]);

  useEffect(() => {
    dataRef.current = [];

    fetch(`http://localhost:8000/api/market_data/${ticker}/`)
      .then((res) => res.json())
      .then((data) => {
        const initial = data.map((d) => ({
          x: new Date(d.start_time),
          y: d.close,
        }));
        dataRef.current = initial;
        setChartData({
          labels: initial.map((p) => p.x),
          datasets: [
            {
              label: `${ticker} - Precio en Vivo`,
              data: initial,
              fill: true,
              borderColor: "#4f46e5",
              backgroundColor: "rgba(79, 70, 229, 0.1)",
              pointRadius: 0,
              borderWidth: 2,
              tension: 0.4,
            },
          ],
        });
      });

    wsRef.current = new WebSocket(`ws://localhost:8000/ws/market/${ticker}/`);
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const time = new Date(data.timestamp);
      if (isNaN(time.getTime())) return;

      const point = { x: time, y: data.close };
      dataRef.current.push(point);
      const trimmed = dataRef.current.slice(-50);

      setChartData({
        labels: trimmed.map((p) => p.x),
        datasets: [
          {
            label: `${ticker} - Precio en Vivo`,
            data: trimmed,
            fill: true,
            borderColor: "#4f46e5",
            backgroundColor: "rgba(79, 70, 229, 0.1)",
            pointRadius: 0,
            borderWidth: 2,
            tension: 0.4,
          },
        ],
      });
    };

    return () => wsRef.current?.close();
  }, [ticker]);

  return (
    <div className="w-full h-96 bg-white p-6 rounded-2xl shadow-xl border border-slate-200">
      <Line
        data={chartData}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          animation: {
            duration: 700,
            easing: "easeOutQuart",
          },
          plugins: {
            legend: {
              display: true,
              labels: {
                color: "#1e293b",
                font: { size: 12, weight: "bold" },
              },
            },
            title: {
              display: true,
              text: `${ticker} Live Chart`,
              color: "#0f172a",
              font: { size: 16, weight: "bold" },
              padding: { top: 10, bottom: 10 },
            },
            tooltip: {
              backgroundColor: "#ffffff",
              titleColor: "#000",
              bodyColor: "#000",
              borderColor: "#e5e7eb",
              borderWidth: 1,
              padding: 10,
              cornerRadius: 6,
              shadowOffsetX: 1,
              shadowOffsetY: 1,
              shadowBlur: 6,
              shadowColor: "rgba(0,0,0,0.15)",
            },
          },
          scales: {
            x: {
              type: "time",
              time: {
                unit: "minute",
                tooltipFormat: "HH:mm",
              },
              ticks: {
                maxTicksLimit: 8,
                color: "#64748b",
              },
              grid: {
                color: "#f1f5f9",
              },
            },
            y: {
              ticks: {
                color: "#64748b",
              },
              grid: {
                color: "#f1f5f9",
              },
            },
          },
        }}
      />
    </div>
  );
};

export default MarketChart;
