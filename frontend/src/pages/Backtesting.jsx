import React, { useState } from "react";

const Backtesting = () => {
  const [symbol, setSymbol] = useState("BTCUSD");
  const [fromDate, setFromDate] = useState("2023-01-01");
  const [toDate, setToDate] = useState("2024-01-01");
  const [timeframe, setTimeframe] = useState("900");
  const [capital, setCapital] = useState("10000");
  const [status, setStatus] = useState("");

  const downloadHistoricalData = async () => {
    setStatus("⏳ Descargando datos...");
    try {
      const params = new URLSearchParams({
        symbol,
        from: fromDate,
        to: toDate,
        timeframe,
      });

      const response = await fetch(`http://localhost:8000/api/backtesting/download_data/?${params.toString()}`);
      const data = await response.json();

      if (!response.ok) throw new Error(data.error || "Error desconocido");

      setStatus(data.message);
    } catch (err) {
      console.error(err);
      setStatus(`❌ Error: ${err.message}`);
    }
  };

  const runBacktest = async () => {
    setStatus("⏳ Ejecutando backtest...");
    try {
      const params = new URLSearchParams({
        symbol,
        from: fromDate,
        to: toDate,
        timeframe,
        capital,
      });

      const response = await fetch(`http://localhost:8000/api/backtesting/run_backtest/?${params.toString()}`);
      const data = await response.json();

      if (!response.ok) throw new Error(data.error || "Error desconocido");

      setStatus(data.message);
    } catch (err) {
      console.error(err);
      setStatus(`❌ Error: ${err.message}`);
    }
  };

  return (
    <div className="max-w-xl mx-auto mt-10 bg-white p-6 rounded shadow">
      <h1 className="text-2xl font-bold mb-4">Backtesting Panel</h1>

      <label className="block mb-2 font-medium">Símbolo</label>
      <input
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        className="w-full border px-3 py-2 rounded mb-4"
        placeholder="BTCUSD"
      />

      <label className="block mb-2 font-medium">Fecha Inicio</label>
      <input
        type="date"
        value={fromDate}
        onChange={(e) => setFromDate(e.target.value)}
        className="w-full border px-3 py-2 rounded mb-4"
      />

      <label className="block mb-2 font-medium">Fecha Fin</label>
      <input
        type="date"
        value={toDate}
        onChange={(e) => setToDate(e.target.value)}
        className="w-full border px-3 py-2 rounded mb-4"
      />

      <label className="block mb-2 font-medium">Timeframe</label>
<select
  value={timeframe}
  onChange={(e) => setTimeframe(e.target.value)}
  className="w-full border px-3 py-2 rounded mb-4"
>
  <option value="60">1 minuto</option>
  <option value="300">5 minutos</option>
  <option value="900">15 minutos</option>
  <option value="1800">30 minutos</option>
  <option value="3600">1 hora</option>
  <option value="86400">1 día</option>
</select>


      <label className="block mb-2 font-medium">Capital Inicial</label>
      <input
        type="number"
        value={capital}
        onChange={(e) => setCapital(e.target.value)}
        className="w-full border px-3 py-2 rounded mb-4"
      />

      <button
        onClick={downloadHistoricalData}
        className="bg-blue-600 text-white px-4 py-2 rounded w-full mb-3"
      >
        Descargar Histórico
      </button>

      <button
        onClick={runBacktest}
        className="bg-green-600 text-white px-4 py-2 rounded w-full"
      >
        Ejecutar Backtest
      </button>

      {status && (
        <div className="mt-4 text-sm text-gray-700 bg-gray-100 p-3 rounded">
          {status}
        </div>
      )}
    </div>
  );
};

export default Backtesting;
