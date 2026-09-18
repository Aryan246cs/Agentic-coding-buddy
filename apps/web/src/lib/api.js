/**
 * Talking to the API.
 *
 * Two kinds of token, kept apart on purpose. The platform token belongs to the
 * person building apps. An app token belongs to someone using one published
 * app and is stored under that app's slug, so signing into one app never
 * grants anything in another.
 */

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const PLATFORM_KEY = 'platform_token';
const appKey = (slug) => `app_token:${slug}`;

/** localStorage throws in private windows; a missing token is not a crash. */
function readStore(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStore(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* nothing we can do, and nothing worth breaking the page over */
  }
}

export const platformToken = {
  get: () => readStore(PLATFORM_KEY),
  set: (token) => writeStore(PLATFORM_KEY, token),
  clear: () => writeStore(PLATFORM_KEY, null),
};

export const appToken = {
  get: (slug) => readStore(appKey(slug)),
  set: (slug, token) => writeStore(appKey(slug), token),
  clear: (slug) => writeStore(appKey(slug), null),
};

/**
 * An error carrying what the API actually said, so a form can show per-field
 * messages instead of a generic failure.
 */
export class ApiError extends Error {
  constructor(status, detail) {
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.message || 'Something went wrong. Please try again.';
    super(message);
    this.status = status;
    this.fieldErrors = detail?.field_errors || {};
    this.errors = detail?.errors || [];
  }
}

async function request(path, { method = 'GET', body, token } = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'Could not reach the server. Is the API running?');
  }

  if (response.status === 204) return null;

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, payload.detail);
  return payload;
}

/** Calls made as the person who builds apps. */
export const api = {
  signup: (body) => request('/api/auth/signup', { method: 'POST', body }),
  login: (body) => request('/api/auth/login', { method: 'POST', body }),
  me: () => request('/api/auth/me', { token: platformToken.get() }),
  health: () => request('/api/health'),

  templates: () => request('/api/templates', { token: platformToken.get() }),
  usage: () => request('/api/usage', { token: platformToken.get() }),

  listProjects: () => request('/api/projects', { token: platformToken.get() }),
  getProject: (id) => request(`/api/projects/${id}`, { token: platformToken.get() }),
  createProject: (body) =>
    request('/api/projects', { method: 'POST', body, token: platformToken.get() }),
  createFromTemplate: (template) =>
    request('/api/projects/from-template', {
      method: 'POST',
      body: { template },
      token: platformToken.get(),
    }),
  updateProject: (id, body) =>
    request(`/api/projects/${id}`, { method: 'PATCH', body, token: platformToken.get() }),
  deleteProject: (id) =>
    request(`/api/projects/${id}`, { method: 'DELETE', token: platformToken.get() }),

  planApp: (description) =>
    request('/api/plan/app', {
      method: 'POST',
      body: { description },
      token: platformToken.get(),
    }),
  planSite: (description) =>
    request('/api/plan/site', {
      method: 'POST',
      body: { description },
      token: platformToken.get(),
    }),
  revise: (id, instruction) =>
    request(`/api/projects/${id}/revise`, {
      method: 'POST',
      body: { instruction },
      token: platformToken.get(),
    }),

  publish: (id) =>
    request(`/api/projects/${id}/publish`, { method: 'POST', token: platformToken.get() }),
  unpublish: (id) =>
    request(`/api/projects/${id}/unpublish`, { method: 'POST', token: platformToken.get() }),

  testRun: (id, body) =>
    request(`/api/projects/${id}/test-run`, {
      method: 'POST',
      body,
      token: platformToken.get(),
    }),
  listRuns: (id) => request(`/api/projects/${id}/runs`, { token: platformToken.get() }),
  getRun: (id, runId) =>
    request(`/api/projects/${id}/runs/${runId}`, { token: platformToken.get() }),

  listMembers: (id) => request(`/api/projects/${id}/members`, { token: platformToken.get() }),
  inviteMember: (id, body) =>
    request(`/api/projects/${id}/members`, {
      method: 'POST',
      body,
      token: platformToken.get(),
    }),
  removeMember: (id, memberId) =>
    request(`/api/projects/${id}/members/${memberId}`, {
      method: 'DELETE',
      token: platformToken.get(),
    }),
};

/** Calls made as someone using a published app. */
export const runtimeApi = {
  info: (slug) => request(`/api/a/${slug}/info`),
  login: (slug, body) => request(`/api/a/${slug}/login`, { method: 'POST', body }),
  join: (slug, body) => request(`/api/a/${slug}/join`, { method: 'POST', body }),
  me: (slug) => request(`/api/a/${slug}/me`, { token: appToken.get(slug) }),

  screen: (slug, key, params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, value]) => value !== null && value !== ''),
    ).toString();
    return request(`/api/a/${slug}/screens/${key}${query ? `?${query}` : ''}`, {
      token: appToken.get(slug),
    });
  },
  submit: (slug, key, data) =>
    request(`/api/a/${slug}/screens/${key}/submit`, {
      method: 'POST',
      body: { data },
      token: appToken.get(slug),
    }),
  record: (slug, entity, id) =>
    request(`/api/a/${slug}/records/${entity}/${id}`, { token: appToken.get(slug) }),
  decide: (slug, approvalId, body) =>
    request(`/api/a/${slug}/approvals/${approvalId}`, {
      method: 'POST',
      body,
      token: appToken.get(slug),
    }),
  notifications: (slug) =>
    request(`/api/a/${slug}/notifications`, { token: appToken.get(slug) }),
  markRead: (slug) =>
    request(`/api/a/${slug}/notifications/read`, {
      method: 'POST',
      token: appToken.get(slug),
    }),

  site: (slug) => request(`/api/s/${slug}`),
};
