import { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../components/ui/table";

export default function SignalsPanel() {
  const [signals, setSignals] = useState([]);
  const [symbolFilter, setSymbolFilter] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/signals/api/signals/?limit=30")
      .then((res) => res.json())
      .then((data) => {
        const sorted = data.sort(
          (a, b) =>
            new Date(b.received_at || b.created_at) -
            new Date(a.received_at || a.created_at)
        );
        setSignals(sorted);
      });
  }, []);

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:8000/ws/signals/");

    socket.onopen = () => console.log("✅ WebSocket connected");

    socket.onmessage = (event) => {
      const newSignal = JSON.parse(event.data);
      setSignals((prev) => {
        const updated = [newSignal, ...prev];
        return updated.slice(0, 30);
      });
    };

    socket.onerror = (err) => console.error("❌ WebSocket error", err);
    socket.onclose = () => console.warn("⚠️ WebSocket closed");

    return () => socket.close();
  }, []);

  const filteredSignals = symbolFilter
    ? signals.filter((s) =>
        s.symbol.toLowerCase().includes(symbolFilter.toLowerCase())
      )
    : signals;

  return (
    <div className="p-6">
      <div className="bg-white dark:bg-gray-900 shadow-md rounded-xl p-6">
        <h2 className="text-2xl font-bold mb-4">📡 Latest Signals</h2>

        <div className="mb-4 flex items-center gap-4">
          <input
            type="text"
            placeholder="🔍 Filter by symbol..."
            className="border px-3 py-1 rounded w-64"
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
          />
        </div>

        <div
          className="overflow-y-auto rounded-lg border border-gray-200"
          style={{ height: "400px", minHeight: "400px" }}
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableCell isHeader={true}>📅 Date</TableCell>
                <TableCell isHeader={true}>🪙 Symbol</TableCell>
                <TableCell isHeader={true}>🎯 Action</TableCell>
                <TableCell isHeader={true}>⚙️ Strategy</TableCell>
                <TableCell isHeader={true}>📊 Confidence</TableCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredSignals.map((signal) => {
                const type = signal.signal || signal.direction;
                const conf = signal.confidence_score || signal.confidence;

                return (
                  <TableRow
                    key={signal.id}
                    className="border-b border-gray-200"
                  >
                    <TableCell>
                      {new Date(
                        signal.received_at || signal.created_at
                      ).toLocaleString()}
                    </TableCell>
                    <TableCell className="flex items-center gap-2">
  <img
    src={`/images/crypto/${signal.symbol}.png`}
    alt={`${signal.symbol} logo`}
    className="w-5 h-5"
  />
  {signal.symbol}
</TableCell>
                    <TableCell
                      className={`font-semibold ${
                        type === "buy" ? "text-green-600" : "text-red-600"
                      }`}
                    >
                      {type === "buy" ? "🟢 Buy" : "🔴 Sell"}
                    </TableCell>
                    <TableCell>{signal.strategy}</TableCell>
                    <TableCell
                      className={`font-semibold ${
                        conf >= 80
                          ? "text-green-600"
                          : conf >= 60
                          ? "text-yellow-500"
                          : "text-red-600"
                      }`}
                    >
                      {conf ?? "—"}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
