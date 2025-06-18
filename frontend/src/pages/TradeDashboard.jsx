import React, { useState, useEffect } from "react";
import TradeTable from "../components/financial/TradeTable";
import TradeMetrics from "../components/financial/TradeMetrics";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function EnhancedTradeDashboard() {
  const [trades, setTrades] = useState([]);
  const [prices, setPrices] = useState({});
  const [usdBalance, setUsdBalance] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [activeTab, setActiveTab] = useState("summary");
  const [symbolFilter, setSymbolFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/trades/api/trades/")
      .then((res) => res.json())
      .then((data) => setTrades(data));

    fetch("http://localhost:8000/trades/api/portfolio/")
      .then((res) => res.json())
      .then((data) => setUsdBalance(data.usd_balance));

    fetch("http://localhost:8000/trades/api/metrics/")
      .then((res) => res.json())
      .then((data) => setMetrics(data));

    const tradeSocket = new WebSocket("ws://localhost:8000/ws/trades/");
    const balanceSocket = new WebSocket("ws://localhost:8000/ws/portfolio/");
    const priceSocket = new WebSocket("ws://localhost:8000/ws/live-prices/");

    tradeSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.deleted) {
        setTrades((prev) => prev.filter((t) => t.id !== data.id));
        return;
      }
      setTrades((prev) => {
        const exists = prev.some((t) => t.id === data.id);
        return exists ? prev.map((t) => (t.id === data.id ? data : t)) : prev;
      });
    };

    balanceSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setUsdBalance(data.usd_balance);
    };

    priceSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setPrices(data);
    };

    return () => {
      tradeSocket.close();
      balanceSocket.close();
      priceSocket.close();
    };
  }, []);

  const applyFilters = (list) =>
    list.filter((t) => {
      const matchSymbol =
        symbolFilter === "" ||
        t.symbol.toLowerCase().includes(symbolFilter.toLowerCase());
      const matchDateFrom =
        dateFrom === "" || new Date(t.executed_at) >= new Date(dateFrom);
      const matchDateTo =
        dateTo === "" || new Date(t.executed_at) <= new Date(dateTo);
      return matchSymbol && matchDateFrom && matchDateTo;
    });

  const openTrades = applyFilters(trades.filter((t) => t.status === "EXECUTED"));
  const closedTrades = applyFilters(trades.filter((t) => t.status === "CLOSED"));

  const equityCurve = trades
  .filter((t) => t.status === "CLOSED" && t.closed_at)
  .sort((a, b) => new Date(a.closed_at) - new Date(b.closed_at))
  .reduce((acc, trade) => {
    const lastValue = acc.length > 0 ? acc[acc.length - 1].balance : 0;
    acc.push({
      date: new Date(trade.closed_at), // ✅ timestamp completo
      balance: lastValue + (trade.pnl || 0),
    });
    return acc;
  }, []);


  const exportToCSV = () => {
    const rows = [
      [
        "Symbol",
        "Strategy",
        "Direction",
        "Price",
        "Exit Price",
        "PNL",
        "Executed At",
        "Closed At",
      ],
    ];
    trades.forEach((t) => {
      rows.push([
        t.symbol.symbol,
        t.strategy,
        t.direction,
        t.price,
        t.exit_price || "",
        t.pnl || "",
        t.executed_at,
        t.closed_at || "",
      ]);
    });
    const csvContent =
      "data:text/csv;charset=utf-8," + rows.map((r) => r.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "trades_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-6 space-y-6 bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-4xl font-black text-slate-800 tracking-tight">
          📊 Trade Control Center
        </h1>
        {usdBalance !== null && (
          <div className="bg-emerald-100 text-emerald-800 font-semibold px-5 py-3 rounded-2xl shadow-xl text-lg">
            💼 Balance: ${usdBalance.toFixed(2)} USD
          </div>
        )}
      </div>

      <div className="flex gap-4 border-b pb-2 text-lg font-medium">
        {[
          { key: "summary", label: "📋 Overview" },
          { key: "open", label: "🟢 Open Positions" },
          { key: "closed", label: "🔴 Closed Trades" },
        ].map((tab) => (
          <button
            key={tab.key}
            className={`px-5 py-2 rounded-t-xl transition-all duration-200 ease-in-out shadow-sm ${
              activeTab === tab.key
                ? "bg-white text-slate-900 shadow-md border-t-4 border-emerald-500"
                : "text-slate-500 hover:text-slate-700 hover:bg-slate-200"
            }`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-4 items-center mt-4">
        <input
          type="text"
          placeholder="🔍 Filter symbol..."
          className="border px-4 py-2 rounded-lg shadow-sm w-56"
          value={symbolFilter}
          onChange={(e) => setSymbolFilter(e.target.value)}
        />
        <input
          type="date"
          className="border px-4 py-2 rounded-lg shadow-sm"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
        />
        <input
          type="date"
          className="border px-4 py-2 rounded-lg shadow-sm"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
        />
        <button
          onClick={exportToCSV}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded-lg font-semibold shadow-md"
        >
          ⬇️ Export CSV
        </button>
      </div>

      <div className="pt-6">
        {activeTab === "summary" && (
          <TradeMetrics
            trades={trades}
            equityCurve={equityCurve}
            avgDrawdown={metrics?.avg_drawdown || 0}
          />
        )}

        {activeTab === "open" && (
          <div>
            <h2 className="text-2xl font-bold mb-4 text-green-700">🟢 Open Trades</h2>
            <TradeTable trades={openTrades} prices={prices} />
          </div>
        )}

        {activeTab === "closed" && (
          <div>
            <h2 className="text-2xl font-bold mb-4 text-red-700">🔴 Closed Trades</h2>
            <TradeTable trades={closedTrades} prices={prices} />
          </div>
        )}
      </div>
    </div>
  );
}
