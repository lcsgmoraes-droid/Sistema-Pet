import assert from "node:assert/strict";

import { normalizePessoaAppLogin } from "./pessoaAppLogin.js";

assert.equal(normalizePessoaAppLogin(null), null);

assert.deepEqual(
  normalizePessoaAppLogin({
    username: "teste1",
    email: "",
    password: "senha-segura",
    role_id: 1,
  }),
  {
    username: "teste1",
    email: null,
    password: "senha-segura",
    role_id: 1,
  },
);

assert.equal(normalizePessoaAppLogin({ email: "   " }).email, null);
assert.equal(
  normalizePessoaAppLogin({ email: "  FUNCIONARIO@EXEMPLO.COM.BR  " }).email,
  "funcionario@exemplo.com.br",
);
