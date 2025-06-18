import { useEffect, useState } from "react";

export default function Strategies() {
  const [strategies, setStrategies] = useState([]);

  const fetchStrategies = async () => {
    const res = await fetch("http://localhost:8000/strategies/api/strategies/");
    const data = await res.json();
    setStrategies(data);
  };

  useEffect(() => {
    fetchStrategies();
  }, []);

  const handleUpdate = async (strategy) => {
    await fetch(`http://localhost:8000/strategies/api/strategies/${strategy.id}/`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(strategy),
    });
    fetchStrategies();
  };

  const handleChange = (id, field, value) => {
    setStrategies((prev) =>
      prev.map((s) =>
        s.id === id ? { ...s, [field]: value } : s
      )
    );
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">⚙️ Strategy Settings</h2>

      <div className="space-y-4">
        {strategies.map((s) => (
          <details key={s.id} className="border rounded shadow">
            <summary className="cursor-pointer px-4 py-3 font-semibold bg-gray-100 hover:bg-gray-200">
              {s.name}
            </summary>
            <div className="px-6 py-4 bg-white space-y-4">
              <div>
                <label className="block font-medium">📝 Description</label>
                <textarea
                  value={s.description || ""}
                  onChange={(e) => handleChange(s.id, "description", e.target.value)}
                  className="w-full border p-2 rounded"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-medium">📊 Score</label>
                  <input
                    type="number"
                    value={s.score}
                    onChange={(e) => handleChange(s.id, "score", parseInt(e.target.value))}
                    className="w-full border p-2 rounded"
                  />
                </div>

                <div>
                  <label className="block font-medium">⏱️ Validity (minutes)</label>
                  <input
                    type="number"
                    value={s.validity_minutes}
                    onChange={(e) =>
                      handleChange(s.id, "validity_minutes", parseInt(e.target.value))
                    }
                    className="w-full border p-2 rounded"
                  />
                </div>

                <div>
                  <label className="block font-medium">📈 Confidence Threshold</label>
                  <input
                    type="number"
                    value={s.confidence_threshold}
                    onChange={(e) =>
                      handleChange(s.id, "confidence_threshold", parseInt(e.target.value))
                    }
                    className="w-full border p-2 rounded"
                  />
                </div>

                <div>
                  <label className="block font-medium">📏 Required Bars</label>
                  <input
                    type="number"
                    value={s.required_bars}
                    onChange={(e) =>
                      handleChange(s.id, "required_bars", parseInt(e.target.value))
                    }
                    className="w-full border p-2 rounded"
                  />
                </div>

                <div>
                  <label className="block font-medium">🕒 Timeframe</label>
                  <select
                    value={s.timeframe}
                    onChange={(e) => handleChange(s.id, "timeframe", e.target.value)}
                    className="w-full border p-2 rounded"
                  >
                    <option value="1m">1 minute</option>
                    <option value="5m">5 minutes</option>
                    <option value="15m">15 minutes</option>
                    <option value="30m">30 minutes</option>
                    <option value="1h">1 hour</option>
                    <option value="4h">4 hours</option>
                    <option value="1d">1 day</option>
                  </select>
                </div>

                <div>
                  <label className="block font-medium">⚙️ Execution Mode</label>
                  <select
                    value={s.execution_mode}
                    onChange={(e) => handleChange(s.id, "execution_mode", e.target.value)}
                    className="w-full border p-2 rounded"
                  >
                    <option value="simulated">Simulated</option>
                    <option value="paper">Paper</option>
                    <option value="live">Live</option>
                  </select>
                </div>

                <div>
                  <label className="block font-medium">🎯 Priority</label>
                  <select
                    value={s.priority}
                    onChange={(e) => handleChange(s.id, "priority", e.target.value)}
                    className="w-full border p-2 rounded"
                  >
                    <option value="primary">Primary</option>
                    <option value="confirm">Confirm</option>
                    <option value="context">Context</option>
                  </select>
                </div>

                <div className="flex items-center gap-2 mt-2">
                  <label className="font-medium">🔥 Auto Execute</label>
                  <input
                    type="checkbox"
                    checked={s.auto_execute}
                    onChange={() => handleChange(s.id, "auto_execute", !s.auto_execute)}
                  />
                </div>
              </div>

              <button
                onClick={() => handleUpdate(s)}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                💾 Save Changes
              </button>
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
