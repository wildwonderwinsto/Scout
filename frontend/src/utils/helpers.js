/**
 * Format large numbers into human-readable strings.
 * 1234 → "1.2K", 1234567 → "1.2M"
 */
export function formatNumber(num) {
  if (num == null) return '—';
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toLocaleString();
}

/**
 * Get the color class for a breakout score.
 */
export function breakoutColor(score) {
  if (score >= 8) return { bg: 'bg-emerald-900/40', text: 'text-emerald-300', border: 'border-emerald-500/50', glow: true };
  if (score >= 3) return { bg: 'bg-green-900/30', text: 'text-green-400', border: 'border-green-500/30', glow: false };
  if (score >= 2) return { bg: 'bg-yellow-900/30', text: 'text-yellow-400', border: 'border-yellow-500/30', glow: false };
  return { bg: 'bg-zinc-800/50', text: 'text-zinc-400', border: 'border-zinc-600/30', glow: false };
}

/**
 * Get VPH display with optional fire icon.
 */
export function vphDisplay(vph) {
  if (vph == null) return { text: '—', fire: false };
  const text = formatNumber(Math.round(vph));
  return { text, fire: vph >= 3000 };
}

/**
 * Format engagement rate as percentage.
 */
export function formatEngagement(rate) {
  if (rate == null) return '—';
  return `${(rate * 100).toFixed(2)}%`;
}

/**
 * Format relative time like "3d ago", "12h ago".
 */
export function formatTimeAgo(days) {
  if (days == null) return '—';
  if (days === 0) return 'Today';
  if (days === 1) return '1d ago';
  return `${days}d ago`;
}

/**
 * Saved videos — localStorage helpers.
 */
const SAVED_KEY = 'yt_scout_saved';

export function getSavedVideos() {
  try {
    const data = JSON.parse(localStorage.getItem(SAVED_KEY) || '[]');
    // Filter out corrupted data (like strings accidentally pushed)
    return Array.isArray(data) ? data.filter(v => v && typeof v === 'object' && v.video_id) : [];
  } catch {
    return [];
  }
}

export function saveVideo(video) {
  const saved = getSavedVideos();
  if (!saved.find(v => v.video_id === video.video_id)) {
    saved.push(video);
    localStorage.setItem(SAVED_KEY, JSON.stringify(saved));
  }
  return saved;
}

export function unsaveVideo(videoId) {
  const saved = getSavedVideos().filter(v => v.video_id !== videoId);
  localStorage.setItem(SAVED_KEY, JSON.stringify(saved));
  return saved;
}

export function isVideoSaved(videoId) {
  return getSavedVideos().some(v => v.video_id === videoId);
}
