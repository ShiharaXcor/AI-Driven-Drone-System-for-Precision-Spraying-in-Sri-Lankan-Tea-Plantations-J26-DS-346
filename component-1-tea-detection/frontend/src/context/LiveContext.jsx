import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, wsUrl } from "../api";

const LiveContext = createContext(null);

// Merge new rows into the list by id, newest first
function mergeById(prev, incoming, max) {
  const map = new Map(prev.map((x) => [x.id, x]));
  incoming.forEach((x) => map.set(x.id, { ...map.get(x.id), ...x }));
  return [...map.values()].sort((a, b) => b.id - a.id).slice(0, max);
}

export function LiveProvider({ children }) {
  const [status, setStatus] = useState(null);
  const [events, setEvents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [online, setOnline] = useState(false);

  const refreshStatus = useCallback(() => api.status().then(setStatus).catch(() => {}), []);
  const refreshEvents = useCallback(
    () => api.events(50).then((rows) => setEvents((p) => mergeById(p, rows, 200))).catch(() => {}),
    []
  );

  const ack = useCallback(async (ids) => {
    await Promise.all(ids.map((id) => api.ack(id)));
    setAlerts((prev) => prev.map((a) => (ids.includes(a.id) ? { ...a, acked: true } : a)));
  }, []);

  useEffect(() => {
    api.alerts(200).then(setAlerts).catch(() => {});
    refreshEvents();
    refreshStatus();

    let ws;
    let timer;
    let closed = false;
    const connect = () => {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => setOnline(true);
      ws.onmessage = (m) => {
        const d = JSON.parse(m.data);
        setStatus((prev) => ({ ...prev, ...d.status }));
        if (d.events.length) setEvents((p) => mergeById(p, d.events, 200));
        if (d.alerts.length) setAlerts((p) => mergeById(p, d.alerts, 500));
      };
      ws.onclose = () => {
        setOnline(false);
        if (!closed) timer = setTimeout(connect, 2000); // reconnect automatically
      };
      ws.onerror = () => ws.close();
    };
    connect();

    return () => {
      closed = true;
      clearTimeout(timer);
      if (ws) ws.close();
    };
  }, [refreshEvents, refreshStatus]);

  return (
    <LiveContext.Provider value={{ status, events, alerts, online, ack, refreshStatus, refreshEvents }}>
      {children}
    </LiveContext.Provider>
  );
}

export function useLive() {
  return useContext(LiveContext);
}