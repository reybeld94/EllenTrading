import React from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import DrawdownTarget from "./DrawdownCard";
import EquityChart from "./EquityChart";

export default function TradeMetrics({ trades, equityCurve }) {
  const total = trades.length;
  const wins = trades.filter((t) => t.status === "CLOSED" && t.pnl > 0).length;
  const losses = trades.filter((t) => t.status === "CLOSED" && t.pnl < 0).length;
  const totalPnL = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
  const avgPnL = total > 0 ? totalPnL / total : 0;
  const winRate = wins + losses > 0 ? (wins / (wins + losses)) * 100 : 0;

  const tradesByStrategy = trades.reduce((acc, t) => {
    const strat = t.strategy || "Unknown";
    acc[strat] = (acc[strat] || 0) + 1;
    return acc;
  }, {});

  const tradesByTimeframe = trades.reduce((acc, t) => {
    const tf = t.timeframe || "N/A";
    acc[tf] = (acc[tf] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="bg-white rounded-xl shadow p-6 space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div className="bg-slate-100 p-4 rounded-xl">
          <p className="text-xs text-gray-500">Total Trades</p>
          <p className="text-2xl font-bold text-slate-800">{total}</p>
        </div>
        <div className="bg-green-100 p-4 rounded-xl">
          <p className="text-xs text-green-700">Total PnL</p>
          <p className="text-2xl font-bold text-green-800">${totalPnL.toFixed(2)}</p>
        </div>
        <div className="bg-blue-100 p-4 rounded-xl">
          <p className="text-xs text-blue-700">Win Rate</p>
          <p className="text-2xl font-bold text-blue-800">{winRate.toFixed(1)}%</p>
        </div>
        <div className="bg-yellow-100 p-4 rounded-xl">
          <p className="text-xs text-yellow-700">Avg PnL / Trade</p>
          <p className="text-2xl font-bold text-yellow-800">${avgPnL.toFixed(2)}</p>
        </div>
      </div>

      <EquityChart equityCurve={equityCurve} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-bold text-slate-800 mb-2">📚 Por Estrategia</h3>
          <ul className="space-y-1 text-sm text-slate-700">
            {Object.entries(tradesByStrategy).map(([strat, count]) => (
              <li key={strat} className="flex justify-between border-b py-1">
                <span>{strat}</span>
                <span className="font-semibold">{count}</span>
              </li>
            ))}
          </ul>
        </div>
<DrawdownTarget  />

      </div>
    </div>
  );
}
