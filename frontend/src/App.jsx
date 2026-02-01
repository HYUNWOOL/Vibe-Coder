import { useEffect, useState } from "react";

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ ok: false }));
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <h1>VibeCoder</h1>
      <pre>{JSON.stringify(health, null, 2)}</pre>
    </div>
  );
}
