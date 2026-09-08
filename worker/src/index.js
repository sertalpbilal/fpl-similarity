// Cloudflare Worker replacement for fpl-fetch (https://github.com/sertalpbilal/fpl-fetch).
// GET /fpl_data?id=<entry>&gw=<last gameweek>
//   -> { info, picks: { GW1: ..., GW2: ... }, trs: [...] }
// Same response shape as the Flask app, so static/js/main.js needs only the base URL changed.
// The FPL API sends no CORS headers, so the browser cannot call it from GitHub Pages directly.

const FPL = 'https://fantasy.premierleague.com/api';
const UA = 'fpl-similarity (https://sertalpbilal.github.io/fpl-similarity/)';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get('Origin') || '';
    const allowed = (env.ALLOWED_ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean);
    const cors = corsHeaders(origin, allowed);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors });
    }
    if (request.method !== 'GET') {
      return json({ error: 'GET only' }, 405, cors);
    }
    if (url.pathname === '/' || url.pathname === '/health') {
      return json({ ok: true, service: 'fpl-fetch worker' }, 200, cors);
    }
    if (url.pathname !== '/fpl_data') {
      return json({ error: 'Not found' }, 404, cors);
    }

    const id = url.searchParams.get('id') || '';
    const gw = parseInt(url.searchParams.get('gw') || '38', 10);
    if (!/^\d{1,9}$/.test(id)) return json({ error: 'Missing or invalid id' }, 400, cors);
    if (!(gw >= 1 && gw <= 38)) return json({ error: 'gw must be 1..38' }, 400, cors);

    // Edge cache keyed on id+gw, so repeat lookups of the same team are instant.
    const ttl = parseInt(env.CACHE_SECONDS || '600', 10);
    const cacheKey = new Request(`https://cache.fpl-fetch.invalid/fpl_data?id=${id}&gw=${gw}`);
    const cache = caches.default;
    const hit = await cache.match(cacheKey);
    if (hit) {
      const r = new Response(hit.body, hit);
      for (const [k, v] of Object.entries(cors)) r.headers.set(k, v);
      r.headers.set('X-Cache', 'HIT');
      return r;
    }

    try {
      const data = await buildTeamData(id, gw);
      if (!data.info) return json({ error: `Team ${id} not found` }, 404, cors);

      const body = JSON.stringify(data);
      const res = new Response(body, {
        status: 200,
        headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': `public, max-age=${ttl}`, 'X-Cache': 'MISS', ...cors },
      });
      ctx.waitUntil(cache.put(cacheKey, res.clone()));
      return res;
    } catch (e) {
      return json({ error: 'Upstream FPL API error', detail: String(e) }, 502, cors);
    }
  },
};

async function buildTeamData(id, gw) {
  const get = async (path) => {
    const r = await fetch(`${FPL}${path}`, { headers: { 'User-Agent': UA, 'Accept': 'application/json' } });
    if (r.status === 404) return null;
    if (!r.ok) throw new Error(`${path} -> ${r.status}`);
    return r.json();
  };

  const gws = Array.from({ length: gw }, (_, i) => i + 1);
  const [info, trs, ...picks] = await Promise.all([
    get(`/entry/${id}/`),
    get(`/entry/${id}/transfers/`),
    ...gws.map(g => get(`/entry/${id}/event/${g}/picks/`)),
  ]);

  const picksByGw = {};
  gws.forEach((g, i) => { if (picks[i]) picksByGw[`GW${g}`] = picks[i]; });

  return { info, picks: picksByGw, trs: trs || [] };
}

function corsHeaders(origin, allowed) {
  const ok = allowed.includes(origin);
  return {
    'Access-Control-Allow-Origin': ok ? origin : allowed[0] || '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With, Access-Control-Allow-Origin, Access-Control-Allow-Headers, Access-Control-Allow-Methods, Referrer-Policy',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}

function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', ...cors } });
}
