import React, { useEffect, useState } from "react";

export default function RiskManagerSettings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchSettings = async () => {
    try {
      const res = await fetch("http://localhost:8000/risk/api/risk-settings/1/");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSettings(applyDefaults(data));
      setLoading(false);
    } catch (err) {
      alert("Error loading configuration: " + err.message);
      console.error("❌ Error:", err);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const applyDefaults = (data) => ({
    ...data,
    risk_pct: data.risk_pct ?? 0.05,
    min_notional: data.min_notional ?? 10,
    conflict_threshold: data.conflict_threshold ?? 10,
    primary_min_score: data.primary_min_score ?? 60,
    primary_group_avg_score: data.primary_group_avg_score ?? 50,
    confirm_min_avg_score: data.confirm_min_avg_score ?? 50,
    context_confirm_avg_score: data.context_confirm_avg_score ?? 50,
    sl_buffer_pct: data.sl_buffer_pct ?? 0.03,
    tp_buffer_pct: data.tp_buffer_pct ?? 0.06,
    trailing_stop_pct: data.trailing_stop_pct ?? 0.02,
    weight_primary: data.weight_primary ?? 1.0,
    weight_context: data.weight_context ?? 0.7,
    weight_confirm: data.weight_confirm ?? 0.5,
  });

  const handleChange = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const isInvalidField = (key, value) => {
    if (typeof value === "string") return false;
    if (value === null || value === undefined || isNaN(value)) return true;

    const ranges = {
      risk_pct: [0, 1],
      sl_buffer_pct: [0, 1],
      tp_buffer_pct: [0, 1],
      trailing_stop_pct: [0, 1],
      weight_primary: [0, 1],
      weight_context: [0, 1],
      weight_confirm: [0, 1],
      min_notional: [0, 100000],
      conflict_threshold: [0, 100],
      primary_min_score: [0, 100],
      primary_group_avg_score: [0, 100],
      confirm_min_avg_score: [0, 100],
      context_confirm_avg_score: [0, 100],
    };

    const [min, max] = ranges[key] || [0, 1000];
    return value < min || value > max;
  };

  const hasInvalidField = () =>
    Object.entries(settings).some(([key, val]) => isInvalidField(key, val));

  const handleSave = async () => {
    try {
      const res = await fetch("http://localhost:8000/risk/api/risk-settings/1/", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      alert("✅ Configuration saved successfully.");
    } catch (err) {
      alert("❌ Error saving: " + err.message);
    }
  };

  // Debug console output
  if (settings) {
    console.log("📦 VALIDATING SETTINGS...");
    Object.entries(settings).forEach(([key, val]) => {
      const invalid = isInvalidField(key, val);
      console.log(`🔍 ${key}: ${val} → invalid? ${invalid}`);
    });
  }

  if (loading || !settings) return <p className="text-gray-500 p-4">Loading configuration...</p>;

  const renderNumberInput = (label, keyName, step = 1, min = 0, max = 1000) => (
    <div className="flex flex-col space-y-1">
      <label className="font-semibold text-sm">{label}</label>
      <input
        type="number"
        step={step}
        className={`border rounded px-3 py-1 ${
          isInvalidField(keyName, settings[keyName]) ? "border-red-500" : ""
        }`}
        value={settings[keyName]}
        onChange={(e) => handleChange(keyName, Number(e.target.value))}
      />
      {isInvalidField(keyName, settings[keyName]) && (
        <span className="text-red-500 text-xs">Invalid value</span>
      )}
    </div>
  );

  const renderPercentInput = (label, keyName) => (
    <div className="flex flex-col space-y-1">
      <label className="font-semibold text-sm">{label}</label>
      <div className="flex items-center space-x-2">
        <input
          type="number"
          min={0}
          max={100}
          step={0.1}
          className={`w-24 border rounded px-3 py-1 ${
            isInvalidField(keyName, settings[keyName]) ? "border-red-500" : ""
          }`}
          value={(settings[keyName] * 100).toFixed(1)}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            if (!isNaN(val)) handleChange(keyName, val / 100);
          }}
        />
        <span className="text-sm text-gray-600">%</span>
      </div>
      {isInvalidField(keyName, settings[keyName]) && (
        <span className="text-red-500 text-xs">Invalid value</span>
      )}
    </div>
  );

  const Section = ({ title, children }) => (
    <fieldset className="border rounded p-4 space-y-4">
      <legend className="text-lg font-bold text-blue-800 px-2">{title}</legend>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{children}</div>
    </fieldset>
  );

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-3xl font-bold text-slate-800">⚙️ Risk Manager Configuration</h1>

      <Section title="📉 Risk & Capital">
        {renderPercentInput("Risk per trade", "risk_pct")}
        {renderNumberInput("Minimum notional ($)", "min_notional", 1, 0, 100000)}
      </Section>

      <Section title="🤔 Conflict Resolution">
        {renderNumberInput("Conflict threshold", "conflict_threshold", 1, 0, 100)}
      </Section>

      <Section title="🧠 Signal Validation Scores">
        {renderNumberInput("Min Primary Score", "primary_min_score", 1, 0, 100)}
        {renderNumberInput("Avg Score for 2+ Primary", "primary_group_avg_score", 1, 0, 100)}
        {renderNumberInput("Avg Score Confirm", "confirm_min_avg_score", 1, 0, 100)}
        {renderNumberInput("Avg Score Context + Confirm", "context_confirm_avg_score", 1, 0, 100)}
      </Section>

      <Section title="🚨 Exit Parameters (SL / TP / Trailing)">
        {renderPercentInput("Stop Loss buffer", "sl_buffer_pct")}
        {renderPercentInput("Take Profit buffer", "tp_buffer_pct")}
        {renderPercentInput("Trailing Stop %", "trailing_stop_pct")}
      </Section>

      <Section title="⚖️ Strategy Priority Weights">
        {renderPercentInput("Primary weight", "weight_primary")}
        {renderPercentInput("Context weight", "weight_context")}
        {renderPercentInput("Confirm weight", "weight_confirm")}
      </Section>

      <div className="pt-4 flex justify-end">
        <button
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          onClick={handleSave}
          disabled={hasInvalidField()}
        >
          💾 Save configuration
        </button>
      </div>
    </div>
  );
}
