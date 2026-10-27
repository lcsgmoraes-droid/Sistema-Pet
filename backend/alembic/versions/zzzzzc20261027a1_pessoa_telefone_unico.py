"""Impede novas atribuições de telefone a pessoas diferentes no mesmo grupo.

Não reescreve nem funde cadastros legados. As funções de consulta nunca devolvem
dados da outra pessoa. A ordem é topologia → escopos de telefone → linhas;
transações que atribuem números precisam usar READ COMMITTED.
"""

from alembic import op
import sqlalchemy as sa

revision = "zzzzzc20261027a1"
down_revision = "zzzzzb20261027a1"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    pode_validar_rls = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )
        )
        .scalar_one()
    )
    if not pode_validar_rls:
        raise RuntimeError(
            "Execute esta migração com a role administrativa de migrations. "
            "A validação entre lojas exige BYPASSRLS; nenhum cadastro foi alterado."
        )
    op.execute(
        r"""
CREATE FUNCTION public.normalizar_telefone_pessoa(valor text)
RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  WITH numero AS (
    SELECT regexp_replace(coalesce(valor, ''), '[^0-9]', '', 'g') AS digitos
  )
  SELECT nullif(CASE
    WHEN left(digitos, 4) = '0055' AND length(digitos) IN (14, 15)
      THEN substr(digitos, 5)
    WHEN left(digitos, 2) = '55' AND length(digitos) IN (12, 13)
      THEN substr(digitos, 3)
    ELSE digitos END, '') FROM numero
$$;

CREATE FUNCTION public._pessoa_telefone_lojas(empresa uuid)
RETURNS uuid[] LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
  SELECT ARRAY(
    SELECT empresa UNION
    SELECT destino.empresa_id::uuid
    FROM public.grupo_comercial_membros origem
    JOIN public.grupo_comercial_membros destino USING (grupo_id)
    JOIN public.grupos_comerciais grupo ON grupo.id = origem.grupo_id
    WHERE origem.empresa_id::uuid = empresa AND origem.status = 'ativo'
      AND destino.status = 'ativo' AND grupo.status = 'ativo'
  )
$$;

CREATE FUNCTION public._pessoa_telefone_validar_contexto(empresa uuid)
RETURNS void LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE ator uuid := nullif(current_setting('app.tenant_id', true), '')::uuid;
BEGIN
  IF ator IS NULL OR empresa IS NULL
     OR NOT empresa = ANY(public._pessoa_telefone_lojas(ator)) THEN
    RAISE EXCEPTION USING ERRCODE = '42501',
      MESSAGE = 'Contexto da loja obrigatório para atribuir telefone a uma pessoa.';
  END IF;
END
$$;

CREATE FUNCTION public.pessoa_telefone_bloquear_escopo(empresa uuid DEFAULT NULL)
RETURNS void LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE
  ator uuid := nullif(current_setting('app.tenant_id', true), '')::uuid;
  lojas uuid[];
  chave bigint;
BEGIN
  -- Sem contexto, só é permitido inserir/retirar dados sem nova posse de número.
  -- A validação por linha rejeita qualquer atribuição nesse caso.
  IF ator IS NULL AND empresa IS NULL THEN RETURN; END IF;
  PERFORM pg_advisory_xact_lock_shared(1735281201, 1);
  -- Uma mudança de grupo pode ter terminado enquanto aguardávamos a barreira.
  -- Revalidar a dona apenas depois dela evita trabalhar com acesso revogado.
  PERFORM public._pessoa_telefone_validar_contexto(coalesce(empresa, ator));
  lojas := public._pessoa_telefone_lojas(ator);
  -- O ator pode editar pessoas de qualquer loja diretamente compartilhada.
  -- Travar também os grupos dessas donas cobre lojas com várias participações.
  FOR chave IN
    SELECT DISTINCT hashtextextended(escopo, 1735281201)
    FROM (
      SELECT 'loja:' || loja::text AS escopo FROM unnest(lojas) AS loja
      UNION
      SELECT 'grupo:' || membro.grupo_id::text
      FROM public.grupo_comercial_membros membro
      JOIN public.grupos_comerciais grupo ON grupo.id = membro.grupo_id
      WHERE membro.empresa_id::uuid = ANY(lojas)
        AND membro.status = 'ativo' AND grupo.status = 'ativo'
    ) escopos ORDER BY 1
  LOOP
    PERFORM pg_advisory_xact_lock(chave);
  END LOOP;
END
$$;

CREATE FUNCTION public.pessoa_telefone_em_uso(
  empresa uuid, excluir_pessoa integer, chave text, excluir_contato integer DEFAULT NULL
)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE lojas uuid[];
BEGIN
  PERFORM public._pessoa_telefone_validar_contexto(empresa);
  IF chave IS NULL THEN RETURN false; END IF;
  lojas := public._pessoa_telefone_lojas(empresa);
  RETURN EXISTS (
    SELECT 1 FROM public.clientes pessoa
    WHERE pessoa.tenant_id = ANY(lojas) AND pessoa.merged_into_id IS NULL
      AND (excluir_pessoa IS NULL OR pessoa.id <> excluir_pessoa)
      AND (
        public.normalizar_telefone_pessoa(pessoa.telefone) = chave
        OR public.normalizar_telefone_pessoa(pessoa.celular) = chave
        OR EXISTS (
          SELECT 1 FROM public.cliente_contatos contato
          WHERE contato.cliente_id = pessoa.id AND contato.tenant_id = pessoa.tenant_id
            AND (excluir_contato IS NULL OR contato.id <> excluir_contato)
            AND public.normalizar_telefone_pessoa(contato.numero) = chave
        )
      )
  );
END
$$;

CREATE FUNCTION public._pessoa_telefone_travar_statement()
RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
BEGIN
  PERFORM public.pessoa_telefone_bloquear_escopo();
  RETURN NULL;
END
$$;

CREATE FUNCTION public._pessoa_telefone_validar_cliente()
RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE
  anteriores text[] := ARRAY[]::text[];
  posteriores text[];
  chave text;
  campo text;
BEGIN
  IF NEW.merged_into_id IS NOT NULL THEN RETURN NEW; END IF;
  IF TG_OP = 'UPDATE' AND OLD.merged_into_id IS NULL
      AND OLD.tenant_id = NEW.tenant_id THEN
    anteriores := ARRAY[
      public.normalizar_telefone_pessoa(OLD.telefone),
      public.normalizar_telefone_pessoa(OLD.celular)
    ];
    anteriores := anteriores || ARRAY(
      SELECT public.normalizar_telefone_pessoa(numero)
      FROM public.cliente_contatos WHERE cliente_id = OLD.id AND tenant_id = OLD.tenant_id
    );
  END IF;
  posteriores := ARRAY[
    public.normalizar_telefone_pessoa(NEW.telefone),
    public.normalizar_telefone_pessoa(NEW.celular)
  ];
  posteriores := posteriores || ARRAY(
    SELECT public.normalizar_telefone_pessoa(numero)
    FROM public.cliente_contatos WHERE cliente_id = NEW.id AND tenant_id = NEW.tenant_id
  );
  FOR chave IN
    SELECT DISTINCT numero FROM unnest(posteriores) numero WHERE numero IS NOT NULL
    EXCEPT SELECT numero FROM unnest(anteriores) numero WHERE numero IS NOT NULL
  LOOP
    PERFORM public._pessoa_telefone_validar_contexto(NEW.tenant_id);
    IF current_setting('transaction_isolation') NOT IN ('read committed', 'read uncommitted') THEN
      RAISE EXCEPTION USING ERRCODE = '40001',
        MESSAGE = 'Atribuição de telefone requer transação READ COMMITTED. Tente novamente.';
    END IF;
    IF public.pessoa_telefone_em_uso(NEW.tenant_id, NEW.id, chave) THEN
      campo := CASE WHEN public.normalizar_telefone_pessoa(NEW.telefone) = chave
        THEN 'telefone' WHEN public.normalizar_telefone_pessoa(NEW.celular) = chave
        THEN 'celular' ELSE 'contatos_adicionais' END;
      RAISE EXCEPTION USING ERRCODE = '23505', CONSTRAINT = 'uq_pessoa_telefone_escopo',
        COLUMN = campo, MESSAGE = 'Este telefone já está vinculado a outra pessoa.';
    END IF;
  END LOOP;
  RETURN NEW;
END
$$;

CREATE FUNCTION public._pessoa_telefone_validar_contato()
RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE pessoa public.clientes%ROWTYPE; chave text;
BEGIN
  SELECT * INTO pessoa FROM public.clientes WHERE id = NEW.cliente_id;
  IF NOT FOUND OR pessoa.tenant_id <> NEW.tenant_id THEN
    RAISE EXCEPTION USING ERRCODE = '23503', MESSAGE = 'Contato deve pertencer à loja da pessoa.';
  END IF;
  IF pessoa.merged_into_id IS NOT NULL THEN RETURN NEW; END IF;
  chave := public.normalizar_telefone_pessoa(NEW.numero);
  IF chave IS NULL THEN RETURN NEW; END IF;
  IF TG_OP = 'UPDATE' AND OLD.cliente_id = NEW.cliente_id
      AND OLD.tenant_id = NEW.tenant_id
      AND public.normalizar_telefone_pessoa(OLD.numero) = chave THEN RETURN NEW; END IF;
  PERFORM public._pessoa_telefone_validar_contexto(NEW.tenant_id);
  IF current_setting('transaction_isolation') NOT IN ('read committed', 'read uncommitted') THEN
    RAISE EXCEPTION USING ERRCODE = '40001',
      MESSAGE = 'Atribuição de telefone requer transação READ COMMITTED. Tente novamente.';
  END IF;
  IF public.pessoa_telefone_em_uso(NEW.tenant_id, NEW.cliente_id, chave, NEW.id) THEN
    RAISE EXCEPTION USING ERRCODE = '23505', CONSTRAINT = 'uq_pessoa_telefone_escopo',
      COLUMN = 'contatos_adicionais', MESSAGE = 'Este telefone já está vinculado a outra pessoa.';
  END IF;
  RETURN NEW;
END
$$;

-- Mudanças de grupo são raras e usam a barreira exclusiva, antes de suas tuplas.
-- Escritas normais compartilham a barreira e lojas independentes não se bloqueiam.
CREATE FUNCTION public._pessoa_telefone_travar_topologia()
RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
BEGIN
  PERFORM pg_advisory_xact_lock(1735281201, 1);
  RETURN NULL;
END
$$;

CREATE FUNCTION public._pessoa_telefone_colisao_lojas(lojas_a uuid[], lojas_b uuid[])
RETURNS boolean LANGUAGE sql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
  WITH numeros AS (
    SELECT pessoa.id, pessoa.tenant_id, public.normalizar_telefone_pessoa(valor) AS chave
    FROM public.clientes pessoa
    CROSS JOIN LATERAL unnest(ARRAY[pessoa.telefone, pessoa.celular]) AS valor
    WHERE pessoa.merged_into_id IS NULL AND pessoa.tenant_id = ANY(lojas_a || lojas_b)
    UNION ALL
    SELECT pessoa.id, pessoa.tenant_id, public.normalizar_telefone_pessoa(contato.numero)
    FROM public.clientes pessoa JOIN public.cliente_contatos contato
      ON contato.cliente_id = pessoa.id AND contato.tenant_id = pessoa.tenant_id
    WHERE pessoa.merged_into_id IS NULL AND pessoa.tenant_id = ANY(lojas_a || lojas_b)
  )
  SELECT EXISTS (
    SELECT 1 FROM numeros a JOIN numeros b ON a.chave = b.chave
    WHERE a.chave IS NOT NULL AND a.tenant_id = ANY(lojas_a) AND b.tenant_id = ANY(lojas_b)
      AND a.id <> b.id AND a.tenant_id <> b.tenant_id
  )
$$;

CREATE FUNCTION public._pessoa_telefone_validar_membro()
RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE outras uuid[];
BEGIN
  IF NEW.status <> 'ativo' THEN RETURN NEW; END IF;
  IF TG_OP = 'UPDATE' AND OLD.status = 'ativo' AND OLD.grupo_id = NEW.grupo_id
      AND OLD.empresa_id = NEW.empresa_id THEN RETURN NEW; END IF;
  IF NOT EXISTS (SELECT 1 FROM public.grupos_comerciais
    WHERE id = NEW.grupo_id AND status = 'ativo') THEN RETURN NEW; END IF;
  outras := ARRAY(SELECT empresa_id::uuid FROM public.grupo_comercial_membros
    WHERE grupo_id = NEW.grupo_id AND status = 'ativo' AND empresa_id <> NEW.empresa_id);
  IF cardinality(outras) = 0 THEN RETURN NEW; END IF;
  IF current_setting('transaction_isolation') NOT IN ('read committed', 'read uncommitted') THEN
    RAISE EXCEPTION USING ERRCODE = '40001', MESSAGE = 'Mudança de grupo requer READ COMMITTED.';
  END IF;
  IF public._pessoa_telefone_colisao_lojas(ARRAY[NEW.empresa_id::uuid], outras) THEN
    RAISE EXCEPTION USING ERRCODE = '23505', CONSTRAINT = 'uq_pessoa_telefone_escopo',
      COLUMN = 'telefone', MESSAGE = 'Revise os telefones compartilhados antes de unir as lojas ao grupo.';
  END IF;
  RETURN NEW;
END
$$;

CREATE FUNCTION public._pessoa_telefone_validar_grupo()
RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public SET row_security = off AS $$
DECLARE lojas uuid[];
BEGIN
  IF NEW.status <> 'ativo' THEN RETURN NEW; END IF;
  IF TG_OP = 'UPDATE' AND OLD.status = 'ativo' THEN RETURN NEW; END IF;
  lojas := ARRAY(SELECT empresa_id::uuid FROM public.grupo_comercial_membros
    WHERE grupo_id = NEW.id AND status = 'ativo');
  IF cardinality(lojas) < 2 THEN RETURN NEW; END IF;
  IF current_setting('transaction_isolation') NOT IN ('read committed', 'read uncommitted') THEN
    RAISE EXCEPTION USING ERRCODE = '40001', MESSAGE = 'Mudança de grupo requer READ COMMITTED.';
  END IF;
  IF public._pessoa_telefone_colisao_lojas(lojas, lojas) THEN
    RAISE EXCEPTION USING ERRCODE = '23505', CONSTRAINT = 'uq_pessoa_telefone_escopo',
      COLUMN = 'telefone', MESSAGE = 'Revise os telefones compartilhados antes de reativar o grupo.';
  END IF;
  RETURN NEW;
END
$$;

CREATE INDEX ix_clientes_tenant_telefone_chave ON public.clientes
  (tenant_id, public.normalizar_telefone_pessoa(telefone)) WHERE merged_into_id IS NULL;
CREATE INDEX ix_clientes_tenant_celular_chave ON public.clientes
  (tenant_id, public.normalizar_telefone_pessoa(celular)) WHERE merged_into_id IS NULL;
CREATE INDEX ix_cliente_contatos_tenant_telefone_chave ON public.cliente_contatos
  (tenant_id, public.normalizar_telefone_pessoa(numero));

CREATE TRIGGER pessoa_telefone_lock BEFORE INSERT OR UPDATE OF telefone, celular,
  merged_into_id, tenant_id ON public.clientes FOR EACH STATEMENT
  EXECUTE FUNCTION public._pessoa_telefone_travar_statement();
CREATE TRIGGER pessoa_telefone_guard BEFORE INSERT OR UPDATE OF telefone, celular,
  merged_into_id, tenant_id ON public.clientes FOR EACH ROW
  EXECUTE FUNCTION public._pessoa_telefone_validar_cliente();
CREATE TRIGGER pessoa_contato_telefone_lock BEFORE INSERT OR UPDATE OF numero,
  numero_digitos, cliente_id, tenant_id ON public.cliente_contatos FOR EACH STATEMENT
  EXECUTE FUNCTION public._pessoa_telefone_travar_statement();
CREATE TRIGGER pessoa_contato_telefone_guard BEFORE INSERT OR UPDATE OF numero,
  numero_digitos, cliente_id, tenant_id ON public.cliente_contatos FOR EACH ROW
  EXECUTE FUNCTION public._pessoa_telefone_validar_contato();
CREATE TRIGGER pessoa_telefone_topologia_lock BEFORE INSERT OR DELETE OR UPDATE OF
  grupo_id, empresa_id, status ON public.grupo_comercial_membros FOR EACH STATEMENT
  EXECUTE FUNCTION public._pessoa_telefone_travar_topologia();
CREATE TRIGGER pessoa_telefone_topologia_guard BEFORE INSERT OR UPDATE OF
  grupo_id, empresa_id, status ON public.grupo_comercial_membros FOR EACH ROW
  EXECUTE FUNCTION public._pessoa_telefone_validar_membro();
CREATE TRIGGER pessoa_telefone_grupo_lock BEFORE INSERT OR DELETE OR UPDATE OF status
  ON public.grupos_comerciais FOR EACH STATEMENT
  EXECUTE FUNCTION public._pessoa_telefone_travar_topologia();
CREATE TRIGGER pessoa_telefone_grupo_guard BEFORE INSERT OR UPDATE OF status
  ON public.grupos_comerciais FOR EACH ROW
  EXECUTE FUNCTION public._pessoa_telefone_validar_grupo();

REVOKE ALL ON FUNCTION public._pessoa_telefone_lojas(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public._pessoa_telefone_validar_contexto(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public._pessoa_telefone_colisao_lojas(uuid[], uuid[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION public._pessoa_telefone_travar_statement() FROM PUBLIC;
REVOKE ALL ON FUNCTION public._pessoa_telefone_validar_cliente() FROM PUBLIC;
REVOKE ALL ON FUNCTION public._pessoa_telefone_validar_contato() FROM PUBLIC;
REVOKE ALL ON FUNCTION public._pessoa_telefone_travar_topologia() FROM PUBLIC;
REVOKE ALL ON FUNCTION public._pessoa_telefone_validar_membro() FROM PUBLIC;
REVOKE ALL ON FUNCTION public._pessoa_telefone_validar_grupo() FROM PUBLIC;
"""
    )


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    for tabela, gatilhos in (
        ("clientes", ("pessoa_telefone_guard", "pessoa_telefone_lock")),
        (
            "cliente_contatos",
            ("pessoa_contato_telefone_guard", "pessoa_contato_telefone_lock"),
        ),
        (
            "grupo_comercial_membros",
            ("pessoa_telefone_topologia_guard", "pessoa_telefone_topologia_lock"),
        ),
        (
            "grupos_comerciais",
            ("pessoa_telefone_grupo_guard", "pessoa_telefone_grupo_lock"),
        ),
    ):
        for gatilho in gatilhos:
            op.execute(f"DROP TRIGGER {gatilho} ON public.{tabela}")
    for assinatura in (
        "_pessoa_telefone_validar_grupo()",
        "_pessoa_telefone_validar_membro()",
        "_pessoa_telefone_colisao_lojas(uuid[], uuid[])",
        "_pessoa_telefone_travar_topologia()",
        "_pessoa_telefone_validar_contato()",
        "_pessoa_telefone_validar_cliente()",
        "_pessoa_telefone_travar_statement()",
        "pessoa_telefone_em_uso(uuid, integer, text, integer)",
        "pessoa_telefone_bloquear_escopo(uuid)",
        "_pessoa_telefone_validar_contexto(uuid)",
        "_pessoa_telefone_lojas(uuid)",
    ):
        op.execute(f"DROP FUNCTION public.{assinatura}")
    for indice in (
        "ix_clientes_tenant_telefone_chave",
        "ix_clientes_tenant_celular_chave",
        "ix_cliente_contatos_tenant_telefone_chave",
    ):
        op.execute(f"DROP INDEX public.{indice}")
    op.execute("DROP FUNCTION public.normalizar_telefone_pessoa(text)")
