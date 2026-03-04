-- =============================================
-- Tabelas para Fila Compartilhada Multi-Usuário
-- =============================================

-- Sessão (metadados de cada rodada de processamento)
CREATE TABLE IF NOT EXISTS fila_sessao (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'processando'
    CHECK (status IN ('processando', 'revisao', 'concluido', 'cancelado')),
  total_itens INT DEFAULT 0,
  itens_processados INT DEFAULT 0,
  iniciado_por TEXT NOT NULL,
  iniciado_por_nome TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Items da fila
CREATE TABLE IF NOT EXISTS fila_admissao (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  sessao_id TEXT NOT NULL REFERENCES fila_sessao(id) ON DELETE CASCADE,
  cod_requisicao TEXT NOT NULL,
  paciente_nome TEXT,
  cpf TEXT,
  status TEXT NOT NULL DEFAULT 'pendente'
    CHECK (status IN ('pendente', 'processando', 'processado', 'em_revisao', 'salvo', 'pulado', 'erro')),
  form_data_snapshot JSONB,
  patient_data_snapshot JSONB,
  resultado_consolidado JSONB,
  erro TEXT,
  processado_por TEXT,
  revisado_por TEXT,
  revisado_por_nome TEXT,
  lock_timestamp TIMESTAMPTZ,
  salvo_por TEXT,
  ordem INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fila_admissao_sessao ON fila_admissao(sessao_id);
CREATE INDEX IF NOT EXISTS idx_fila_admissao_status ON fila_admissao(sessao_id, status);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS fila_admissao_updated_at ON fila_admissao;
CREATE TRIGGER fila_admissao_updated_at
  BEFORE UPDATE ON fila_admissao
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS fila_sessao_updated_at ON fila_sessao;
CREATE TRIGGER fila_sessao_updated_at
  BEFORE UPDATE ON fila_sessao
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Habilitar Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE fila_admissao;
ALTER PUBLICATION supabase_realtime ADD TABLE fila_sessao;

-- RLS: Permitir acesso total para qualquer usuario autenticado
ALTER TABLE fila_admissao ENABLE ROW LEVEL SECURITY;
ALTER TABLE fila_sessao ENABLE ROW LEVEL SECURITY;

-- Policies permissivas (todos os usuarios autenticados podem tudo)
DROP POLICY IF EXISTS "fila_admissao_all" ON fila_admissao;
CREATE POLICY "fila_admissao_all" ON fila_admissao FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "fila_sessao_all" ON fila_sessao;
CREATE POLICY "fila_sessao_all" ON fila_sessao FOR ALL USING (true) WITH CHECK (true);

-- Função de lock atômico para revisão
CREATE OR REPLACE FUNCTION acquire_review_lock(
  p_item_id UUID,
  p_user_id TEXT,
  p_user_nome TEXT,
  p_lock_timeout_minutes INT DEFAULT 5
)
RETURNS BOOLEAN AS $$
DECLARE
  current_status TEXT;
  current_reviewer TEXT;
  current_lock_ts TIMESTAMPTZ;
BEGIN
  SELECT status, revisado_por, lock_timestamp
  INTO current_status, current_reviewer, current_lock_ts
  FROM fila_admissao
  WHERE id = p_item_id
  FOR UPDATE;

  IF current_status = 'processado' THEN
    UPDATE fila_admissao
    SET status = 'em_revisao',
        revisado_por = p_user_id,
        revisado_por_nome = p_user_nome,
        lock_timestamp = now()
    WHERE id = p_item_id;
    RETURN TRUE;
  ELSIF current_status = 'em_revisao' THEN
    IF current_reviewer = p_user_id THEN
      UPDATE fila_admissao SET lock_timestamp = now() WHERE id = p_item_id;
      RETURN TRUE;
    ELSIF current_lock_ts < now() - (p_lock_timeout_minutes || ' minutes')::INTERVAL THEN
      UPDATE fila_admissao
      SET status = 'em_revisao',
          revisado_por = p_user_id,
          revisado_por_nome = p_user_nome,
          lock_timestamp = now()
      WHERE id = p_item_id;
      RETURN TRUE;
    ELSE
      RETURN FALSE;
    END IF;
  ELSE
    RETURN FALSE;
  END IF;
END;
$$ LANGUAGE plpgsql;
