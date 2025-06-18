import React from "react";
import Chart from "react-apexcharts";

export default function EquityChart({ equityCurve }) {
  const options = {
    chart: {
      type: "area",
      height: 300,
      fontFamily: "Outfit, sans-serif",
      toolbar: { show: false },
      zoom: { enabled: false },
    },
    colors: ["#10b981"],
    stroke: {
      curve: "smooth",
      width: 3,
    },
    fill: {
      type: "gradient",
      gradient: {
        shade: "light",
        gradientToColors: ["#6ee7b7"],
        opacityFrom: 0.6,
        opacityTo: 0.1,
      },
    },
    dataLabels: {
      enabled: false,
    },
    tooltip: {
      x: {
        format: "dd MMM HH:mm",
      },
      y: {
        formatter: (val) => `$${parseFloat(val).toFixed(2)}`
      },
      theme: "light",
    },
    xaxis: {
      type: "datetime",
      labels: {
        format: "dd MMM",
        rotate: -30,
        style: {
          colors: "#6b7280",
          fontSize: "12px",
        },
      },
      axisTicks: { show: false },
      axisBorder: { show: false },
    },
    yaxis: {
      labels: {
        style: {
          colors: "#6b7280",
          fontSize: "12px",
        },
      },
    },
    grid: {
      yaxis: { lines: { show: true } },
      xaxis: { lines: { show: false } },
    },
  };

  const series = [
    {
      name: "Equity",
      data: equityCurve.map((point) => ({
        x: new Date(point.date),
        y: parseFloat(point.balance.toFixed(2)),
      })),
    },
  ];

  return (
    <div className="bg-white rounded-xl shadow p-4">
      <h3 className="text-lg font-bold text-slate-800 mb-2">📈 Equity Curve</h3>
      {series[0].data.length > 0 ? (
        <Chart options={options} series={series} type="area" height={300} />
      ) : (
        <p className="text-sm text-gray-500 italic">No hay suficientes trades cerrados aún.</p>
      )}
    </div>
  );
}
