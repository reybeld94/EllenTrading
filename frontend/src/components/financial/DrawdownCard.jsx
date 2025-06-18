import Chart from "react-apexcharts";

export default function DrawdownTarget({ value = 0 }) {
  const series = [Number(value.toFixed(2))];

  const options = {
    colors: ["#334155"],
    chart: {
      fontFamily: "Outfit, sans-serif",
      type: "radialBar",
      height: 330,
      sparkline: { enabled: true },
    },
    plotOptions: {
      radialBar: {
        startAngle: -85,
        endAngle: 85,
        hollow: { size: "80%" },
        track: {
          background: "#CBD5E1",
          strokeWidth: "100%",
          margin: 5,
        },
        dataLabels: {
          name: { show: false },
          value: {
            fontSize: "36px",
            fontWeight: "600",
            offsetY: -40,
            color: "#1E293B",
            formatter: (val) => `-${val}%`,
          },
        },
      },
    },
    fill: { type: "solid", colors: ["#334155"] },
    stroke: { lineCap: "round" },
    labels: ["Drawdown"],
  };

  return (
    <div className="rounded-2xl border border-slate-300 bg-slate-50">
      <div className="px-5 pt-5 pb-10 bg-white rounded-2xl shadow">
        <h3 className="text-lg font-semibold text-slate-800 mb-1">
          📉 Drawdown Promedio
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Basado en trades cerrados
        </p>
        <div className="relative">
          <Chart options={options} series={series} type="radialBar" height={300} />
        </div>
      </div>
    </div>
  );
}
