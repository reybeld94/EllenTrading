import React, { useEffect, useState } from "react";
import walletIcon from "../../../public/balance.png"; // 👈 Asegúrate de poner el PNG aquí

export default function PortfolioOverview() {
  const [portfolio, setPortfolio] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/core/api/portfolio/")
      .then((res) => res.json())
      .then((data) => setPortfolio(data))
      .catch((err) => console.error("❌ Error cargando portafolio:", err));
  }, []);

  if (!portfolio) return <div className="text-gray-500">Loading portfolio...</div>;

  return (
    <div className="bg-white shadow rounded-xl p-4 flex gap-6 items-start mb-6">
      <div className="flex items-center gap-4">
        <img src={walletIcon} alt="wallet" className="w-12 h-12" />
        <div>
          <h2 className="text-lg font-semibold">💼 Portafolio: {portfolio.name}</h2>
          <p className="text-green-700 font-bold text-xl">${portfolio.usd_balance.toFixed(2)} USD</p>
        </div>
      </div>

      <div className="flex-1">
        <h3 className="text-sm text-gray-500 mb-2">📌 Posiciones activas</h3>
        {portfolio.positions.length > 0 ? (
          <table className="w-full text-sm border">
            <thead className="bg-gray-100">
              <tr>
                <th className="p-2">Symbol</th>
                <th className="p-2">Qty</th>
                <th className="p-2">Avg Price</th>
                <th className="p-2">Current</th>
                <th className="p-2">Value</th>
                <th className="p-2">PnL</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.positions.map((pos) => (
                <tr key={pos.symbol} className="text-center">
                  <td className="p-2">{pos.symbol}</td>
                  <td className="p-2">{pos.qty}</td>
                  <td className="p-2">${pos.avg_price.toFixed(2)}</td>
                  <td className="p-2">${pos.current_price.toFixed(2)}</td>
                  <td className="p-2">${pos.market_value.toFixed(2)}</td>
                  <td
                    className={`p-2 font-semibold ${
                      pos.unrealized_pnl > 0
                        ? "text-green-600"
                        : pos.unrealized_pnl < 0
                        ? "text-red-600"
                        : "text-gray-600"
                    }`}
                  >
                    ${pos.unrealized_pnl.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-gray-500">Sin posiciones aún.</p>
        )}
      </div>
    </div>
  );
}
