import assert from 'node:assert/strict';
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from '../src/auth/tokenStorage.js';

class MemoryStorage {
  constructor() {
    this.map = new Map();
  }

  getItem(key) {
    return this.map.has(key) ? this.map.get(key) : null;
  }

  setItem(key, value) {
    this.map.set(key, String(value));
  }

  removeItem(key) {
    this.map.delete(key);
  }
}

const newTab = () => {
  globalThis.sessionStorage = new MemoryStorage();
};

globalThis.localStorage = new MemoryStorage();
newTab();

setAccessToken('token-para-nova-aba');
newTab();

assert.equal(
  getAccessToken(),
  'token-para-nova-aba',
  'uma nova aba deve reaproveitar o token persistido'
);

assert.equal(
  globalThis.sessionStorage.getItem('access_token'),
  'token-para-nova-aba',
  'a nova aba deve hidratar o sessionStorage para as proximas requisicoes'
);

clearAuthTokens();

assert.equal(globalThis.localStorage.getItem('access_token'), null);
assert.equal(globalThis.sessionStorage.getItem('access_token'), null);
assert.equal(globalThis.localStorage.getItem('refresh_token'), null);
assert.equal(globalThis.sessionStorage.getItem('refresh_token'), null);

globalThis.localStorage.setItem('token', 'token-legado');
newTab();

assert.equal(
  getAccessToken(),
  'token-legado',
  'tokens antigos em localStorage devem continuar funcionando'
);
assert.equal(globalThis.localStorage.getItem('access_token'), 'token-legado');
assert.equal(globalThis.localStorage.getItem('token'), null);

setRefreshToken('refresh-para-nova-aba');
newTab();

assert.equal(
  getRefreshToken(),
  'refresh-para-nova-aba',
  'uma nova aba deve reaproveitar o refresh token persistido'
);
assert.equal(
  globalThis.sessionStorage.getItem('refresh_token'),
  'refresh-para-nova-aba',
  'a nova aba deve hidratar o refresh token no sessionStorage'
);

clearAuthTokens();

assert.equal(globalThis.localStorage.getItem('refresh_token'), null);
assert.equal(globalThis.sessionStorage.getItem('refresh_token'), null);

