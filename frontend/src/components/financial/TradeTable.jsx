import { useState } from "react";

export default function TradeTable({ trades, prices }) {
  const [closing, setClosing] = useState(null);

  const closeTrade = async (tradeId) => {
    if (!window.confirm("¿Cerrar este trade manualmente?")) return;
    setClosing(tradeId);
    try {
      const res = await fetch(`http://localhost:8000/trades/api/trades/${tradeId}/close/`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Error al cerrar el trade.");
    } catch (err) {
      alert("❌ Error al cerrar: " + err.message);
    } finally {
      setClosing(null);
    }
  };

  return (
    <div className="overflow-auto mb-6 bg-gray-50">

      <table className="w-full border text-sm">
        <thead className="bg-gray-100">
          <tr>
            <th className="p-2">Symbol</th>
            <th className="p-2">Direction</th>
            <th className="p-2">Entry</th>
            <th className="p-2">Current Price</th>

            <th className="p-2">Notional</th>
            <th className="p-2">SL</th>
            <th className="p-2">TP</th>
            <th className="p-2">Trail</th>

            <th className="p-2">PnL</th>

            <th className="p-2">Acción</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => {
            console.log("💥 Trade:", trade.symbol, "→", trade.logo_url);

            return (
              <tr key={trade.id} className="hover:bg-gray-100">

                <td className="p-2 flex items-center gap-2">
                  {trade.logo_url ? (
                    <img
                      src={`/images/crypto/${trade.symbol}.png`}
                      alt={trade.symbol}
                      className="w-5 h-5 rounded-full border"
                      onError={(e) => {
                        e.target.onerror = null;
                        e.target.src = "https://via.placeholder.com/20?text=❓";
                      }}
                    />
                  ) : (
                    <span className="text-gray-400">🪙</span>
                  )}

                </td>

                <td className="p-2 font-semibold">
  {trade.direction.toLowerCase() === "buy" ? (
    <span className="text-green-600">⬆️ BUY</span>
  ) : (
    <span className="text-red-600">⬇️ SELL</span>
  )}
</td>

                <td className="p-2">{trade.price}</td>
                <td className="p-2">
                  {prices?.[trade.symbol] ??
                    (trade.live_price !== undefined
                      ? trade.live_price.toFixed(5)
                      : "—")}
                </td>


                <td className="p-2">{trade.notional}</td>
                <td className="p-2">{trade.stop_loss ?? "—"}</td>
                <td className="p-2">{trade.take_profit ?? "—"}</td>
                <td className="p-2">{trade.trailing_stop_level ?? "—"}</td>

                <td
                  className={`p-2 font-semibold ${
                    trade.pnl > 0
                      ? "text-green-600"
                      : trade.pnl < 0
                      ? "text-red-600"
                      : "text-gray-600"
                  }`}
                >
                  {trade.pnl !== null ? `${trade.pnl.toFixed(2)} USD` : "—"}
                </td>

                <td className="p-2">
                  {trade.status === "EXECUTED" && (
                    <button
                      onClick={() => closeTrade(trade.id)}
                      disabled={closing === trade.id}
                      className={`px-2 py-1 rounded text-white text-xs ${
                        closing === trade.id
                          ? "bg-gray-400 cursor-wait"
                          : "bg-red-600 hover:bg-red-700"
                      }`}
                    >
                      ❌ Cerrar
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
