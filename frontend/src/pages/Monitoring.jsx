import React, { useEffect, useState } from "react";

const SOURCES = ["strategies", "trades", "streaming", "risk_manager"];
const LEVELS = ["INFO", "WARNING", "ERROR"];

const formatSource = (src) =>
  src
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

const Monitoring = () => {
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState("strategies");
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("");

  useEffect(() => {
    setLogs([]); // 🧹 limpiar logs al cambiar de tab

    const fetchLogs = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/monitoring/logs/?limit=500&source=${activeTab}`);
        const data = await res.json();
        setLogs(data);
      } catch (err) {
        console.error("Error al cargar logs:", err);
      }
    };

    fetchLogs();

    const socket = new WebSocket("ws://localhost:8000/ws/logs/");

    socket.onmessage = (event) => {
      const log = JSON.parse(event.data);
      const now = new Date();
      const logTime = new Date(log.timestamp);
      const diffHours = (now - logTime) / 1000 / 60 / 60;

      if (diffHours <= 24 && log.source.toLowerCase() === activeTab) {
        setLogs((prev) => [log, ...prev.slice(0, 499)]);
      }
    };

    socket.onerror = (error) => console.error("WebSocket error:", error);

    return () => {
      socket.close(); // ✅ cerrar socket viejo
    };
  }, [activeTab]);

  const getColor = (level) => {
    switch (level) {
      case "ERROR": return "text-red-500";
      case "WARNING": return "text-orange-500";
      case "INFO": return "text-blue-500";
      default: return "text-gray-500";
    }
  };

  const filteredLogs = logs
    .filter((log) => (levelFilter ? log.level === levelFilter : true))
    .filter((log) => log.message.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="p-6 bg-white text-gray-800 h-screen overflow-y-auto">
      <h1 className="text-2xl font-bold mb-4">📊 Monitoring Dashboard</h1>

      <div className="flex mb-4 gap-4">
        {SOURCES.map((src) => (
          <button
            key={src}
            onClick={() => {
              setActiveTab(src);
              setSearch("");
              setLevelFilter("");
            }}
            className={`px-4 py-1 rounded border ${
              activeTab === src ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-800"
            }`}
          >
            {formatSource(src)}
          </button>
        ))}
      </div>

      <div className="flex gap-4 mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar en mensajes..."
          className="border p-2 rounded w-1/2"
        />
        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          className="border p-2 rounded"
        >
          <option value="">Todos los niveles</option>
          {LEVELS.map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </select>
      </div>

      <div className="text-sm text-gray-500 mb-2">
        🟢 Mostrando {filteredLogs.length} logs de las últimas 24 horas para <strong>{formatSource(activeTab)}</strong>
      </div>

      <div className="space-y-1">
        {filteredLogs.map((log, idx) => (
          <div key={idx} className="text-sm font-mono">
            <span className="text-gray-500">[{log.timestamp}]</span>{" "}
            <span className={`${getColor(log.level)} font-bold`}>[{log.level}]</span>{" "}
            <span className="text-purple-600">{formatSource(log.source)}:</span>{" "}
            <span>{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Monitoring;
