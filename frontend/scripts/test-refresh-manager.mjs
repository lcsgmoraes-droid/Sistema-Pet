import assert from 'node:assert/strict';
import { createRefreshManager } from '../src/auth/refreshManager.js';

let storedRefreshToken = 'refresh-inicial';
let storedAccessToken = null;
let calls = 0;
let releaseRefresh;

const refreshRequest = async (refreshToken) => {
  calls += 1;
  assert.equal(refreshToken, 'refresh-inicial');
  await new Promise((resolve) => {
    releaseRefresh = resolve;
  });
  return {
    data: {
      access_token: 'access-renovado',
      refresh_token: 'refresh-renovado',
    },
  };
};

const manager = createRefreshManager({
  refreshRequest,
  getRefreshToken: () => storedRefreshToken,
  setAccessToken: (token) => {
    storedAccessToken = token;
  },
  setRefreshToken: (token) => {
    storedRefreshToken = token;
  },
  clearAuthTokens: () => {
    storedRefreshToken = null;
    storedAccessToken = null;
  },
});

const first = manager.refreshAccessToken();
const second = manager.refreshAccessToken();

assert.equal(calls, 1, 'renovacoes concorrentes devem compartilhar uma unica chamada');
releaseRefresh();

assert.equal(await first, 'access-renovado');
assert.equal(await second, 'access-renovado');
assert.equal(storedAccessToken, 'access-renovado');
assert.equal(storedRefreshToken, 'refresh-renovado');

const missingRefreshManager = createRefreshManager({
  refreshRequest,
  getRefreshToken: () => null,
  setAccessToken: () => {},
  setRefreshToken: () => {},
  clearAuthTokens: () => {},
});

await assert.rejects(
  () => missingRefreshManager.refreshAccessToken(),
  /Refresh token ausente/,
);
