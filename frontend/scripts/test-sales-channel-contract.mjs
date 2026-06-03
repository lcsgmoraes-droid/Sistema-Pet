import assert from 'node:assert/strict';

import {
  CANAL_APP,
  CANAL_ECOMMERCE,
  CANAL_LOJA_FISICA,
  getSalesChannelInfo,
  isOnlineSalesChannel,
  normalizeSalesChannel,
} from '../src/utils/salesChannel.js';

assert.equal(normalizeSalesChannel('app'), CANAL_APP);
assert.equal(normalizeSalesChannel('aplicativo'), CANAL_APP);
assert.equal(normalizeSalesChannel('mobile'), CANAL_APP);
assert.equal(normalizeSalesChannel('app_movel'), CANAL_APP);

assert.equal(normalizeSalesChannel('web'), CANAL_ECOMMERCE);
assert.equal(normalizeSalesChannel('site'), CANAL_ECOMMERCE);
assert.equal(normalizeSalesChannel('e-commerce'), CANAL_ECOMMERCE);

assert.equal(normalizeSalesChannel('pdv'), CANAL_LOJA_FISICA);
assert.equal(normalizeSalesChannel('loja-fisica'), CANAL_LOJA_FISICA);
assert.equal(normalizeSalesChannel('balcao'), CANAL_LOJA_FISICA);

assert.equal(normalizeSalesChannel('app_funcionario'), 'app_funcionario');
assert.equal(normalizeSalesChannel('banho_tosa'), 'banho_tosa');
assert.equal(normalizeSalesChannel('veterinario'), 'veterinario');

assert.equal(normalizeSalesChannel(null), CANAL_ECOMMERCE);
assert.equal(normalizeSalesChannel('', CANAL_LOJA_FISICA), CANAL_LOJA_FISICA);

assert.equal(isOnlineSalesChannel('mobile'), true);
assert.equal(isOnlineSalesChannel('site'), true);
assert.equal(isOnlineSalesChannel('pdv'), false);

assert.equal(getSalesChannelInfo('mobile').label, 'App');
assert.equal(getSalesChannelInfo('site').label, 'Ecommerce');
assert.equal(getSalesChannelInfo('pdv').label, 'PDV');

console.log('Sales channel contract checks passed.');
