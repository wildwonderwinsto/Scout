import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',  // Env var for production, Vite proxy for local dev
  timeout: 60000,
});

// ── Scan Endpoints ─────────────────────────────────────────
export const fetchGeneralScan = (filters) =>
  api.post('/scan/general', filters).then(r => r.data);

export const fetchKeywordScan = (filters) =>
  api.post('/scan/keyword', filters).then(r => r.data);

export const fetchChannelScan = (channelId, filters) =>
  api.post(`/scan/channel/${channelId}`, filters).then(r => r.data);

// ── Channel Endpoints ──────────────────────────────────────
export const fetchChannelAnalysis = (channelIdOrUrl) =>
  api.get(`/channels/${encodeURIComponent(channelIdOrUrl)}/analysis`).then(r => r.data);

export const fetchSnapshotStats = () =>
  api.get('/channels/snapshots/stats').then(r => r.data);

export const refreshSnapshots = (videoIds) =>
  api.post('/channels/snapshots/refresh', videoIds).then(r => r.data);

// ── Video Endpoints ────────────────────────────────────────
export const fetchVideoDetails = (videoId) =>
  api.get(`/videos/${videoId}`).then(r => r.data);

// ── Health ──────────────────────────────────────────────────
export const fetchHealth = () =>
  api.get('/health').then(r => r.data);

export default api;
