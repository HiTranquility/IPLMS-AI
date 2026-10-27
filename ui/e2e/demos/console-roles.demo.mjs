// AI Console role demo runner (ISSUE-020, docs/projects/issues/10-2026/ISSUE-020-*/review/review-1.md):
// every account gets its own cookie jar and all accounts run at the same time, so roles never
// share a session. For each role it signs in (wrong password, password, wrong TOTP, TOTP), reads
// /me, then calls the read endpoints and compares each status with the permissions /me returned.
// It records observations; it does not label, approve or change roles, but every run creates
// sessions and writes auth.login / auth.mfa / logout rows to the console audit log.
//
//   node ui/e2e/demos/console-roles.demo.mjs      (in ai/, console running on 127.0.0.1:8090)
//
// The server rejects a TOTP code already used in the same 30 s step (console_store.py:463-472):
// run again ≥ 30 s later, and not right after signing in to the UI with the same account.
//
// Accounts: AI_QA_<ROLE>_EMAIL / _PASSWORD / _TOTP_SECRET (base32 from the otpauth URI that
// `python -m app.script.console_admin` prints once). Never hard-code them here.
// URL: AI_CONSOLE_URL (default http://127.0.0.1:8090).
import { createHmac } from 'node:crypto';

const BASE = process.env.AI_CONSOLE_URL ?? 'http://127.0.0.1:8090';
if (!['localhost', '127.0.0.1', '[::1]'].includes(new URL(BASE).hostname)) throw new Error(`Demo chỉ chạy trên máy dev — từ chối ${BASE}`);
const API = `${BASE}/console/api`;

// Endpoint đọc → permission, chép từ controller (đổi controller thì sửa bảng này).
const READS = [
  ['/members', 'ai:member:manage'], //       console_member_controller.py:48-50
  ['/audit', 'ai:audit:read'], //            console_member_controller.py:84-87
  ['/vision/status', 'ai:metrics:read'], //  console_vision_controller.py:223-224
  ['/vision/queue', 'ai:task:label'], //     console_vision_controller.py:234-237
  ['/vision/reviews', 'ai:label:approve'], // console_vision_controller.py:266-269
  ['/vision/snapshots', ['ai:dataset:snapshot', 'ai:model:evaluate']], // console_vision_controller.py:284-286
];

const roles = [...new Set(Object.keys(process.env).map((k) => k.match(/^AI_QA_(\w+)_EMAIL$/)?.[1]).filter(Boolean))];
if (!roles.length) { console.log('BLOCKED: không có biến AI_QA_<ROLE>_EMAIL nào'); process.exit(0); }

const B32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
const normalizeSecret = (raw) => {
  const s = (raw ?? '').toUpperCase().replace(/[\s=]/g, '');
  return s && [...s].every((c) => B32.includes(c)) ? s : null;
};
const totp = (b32, step = 0) => {
  const bits = [...b32].map((c) => B32.indexOf(c).toString(2).padStart(5, '0')).join('');
  const key = Buffer.from(bits.match(/.{8}/g).map((b) => parseInt(b, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000) + step));
  const h = createHmac('sha1', key).update(counter).digest();
  const o = h[h.length - 1] & 0xf;
  return String((h.readUInt32BE(o) & 0x7fffffff) % 1_000_000).padStart(6, '0');
};

// Một "context" = một cookie jar riêng cho một tài khoản.
function context() {
  const jar = new Map();
  return async (method, path, body) => {
    const res = await fetch(`${API}${path}`, {
      method,
      headers: { Accept: 'application/json', 'X-Console-Request': '1', ...(body ? { 'Content-Type': 'application/json' } : {}), Cookie: [...jar].map(([k, v]) => `${k}=${v}`).join('; ') },
      body: body ? JSON.stringify(body) : undefined,
    });
    for (const c of res.headers.getSetCookie()) { const [kv] = c.split(';'); const i = kv.indexOf('='); jar.set(kv.slice(0, i), kv.slice(i + 1)); }
    const json = await res.json().catch(() => ({}));
    // Envelope BaseResponse: { success, total, message, data: [...] } (app/api/rest/schemas/base_response.py:13-17).
    return { status: res.status, data: json.data?.[0], code: json.error?.code ?? json.code };
  };
}

async function play(role) {
  const out = [];
  const log = (step, what) => out.push(`${step} [${role.toLowerCase()}] ${what}`);
  const env = (k) => process.env[`AI_QA_${role}_${k}`];
  const call = context();
  const secret = normalizeSecret(env('TOTP_SECRET'));
  if (!env('PASSWORD') || !secret) {
    log('L0', `BLOCKED: thiếu AI_QA_${role}_PASSWORD hoặc AI_QA_${role}_TOTP_SECRET (base32) hợp lệ`);
    return out;
  }
  try {
    await steps(call, log, env, secret);
  } catch (e) {
    log('L0', `BLOCKED: ${e.cause?.code ?? e.message}`); // console tắt, mạng lỗi…
  }
  return out;
}

async function steps(call, log, env, secret) {
  let r = await call('POST', '/auth/password', { email: env('EMAIL'), password: `${env('PASSWORD')}-sai` });
  log('L1', `sai mật khẩu → ${r.status} ${r.code ?? ''}`);
  r = await call('POST', '/auth/password', { email: env('EMAIL'), password: env('PASSWORD') });
  log('L2', `đúng mật khẩu → ${r.status} · mfa_required=${r.data?.mfa_required}`);
  if (r.status !== 200) return;
  // Mã của khung cách 5 bước (2,5 phút) — chắc chắn sai mà vẫn đúng định dạng 6 số.
  r = await call('POST', '/auth/totp', { code: totp(secret, 5) });
  log('L3', `sai TOTP → ${r.status} ${r.code ?? ''}`);
  r = await call('POST', '/auth/totp', { code: totp(secret) });
  log('L4', `đúng TOTP → ${r.status} ${r.code ?? ''}${r.code === 'TOTP_INVALID' ? ' (mã của bước 30 s này có thể đã dùng — chạy lại sau 30 s)' : ''}`);
  if (r.status !== 200) return;
  const me = (await call('GET', '/me')).data ?? {};
  log('M0', `/me mfa_done=${me.mfa_done}`);
  log('M1', `vai = ${(me.roles ?? []).join(',') || '(không có)'} · ${me.permissions?.length ?? 0} quyền`);
  for (const [path, need] of READS) {
    const allowed = [need].flat().some((p) => me.permissions?.includes(p));
    const { status } = await call('GET', path);
    const ok = allowed ? status === 200 : status === 403;
    log('R', `${ok ? '✅' : '❌'} GET ${path} → ${status} (mong ${allowed ? 200 : 403}, cần ${[need].flat().join('|')})`);
  }
  r = await call('POST', '/auth/logout');
  log('L5', `đăng xuất → ${r.status}; /me sau đó → ${(await call('GET', '/me')).status}`);
}

console.log(`# AI Console role runner — ${new Date().toISOString()} · ${roles.length} context song song: ${roles.join(', ').toLowerCase()}`);
for (const lines of await Promise.all(roles.map(play))) console.log(lines.join('\n'));
