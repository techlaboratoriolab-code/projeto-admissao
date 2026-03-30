import { useState, useEffect, useRef, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from '../contexts/AuthContext';

/**
 * Hook para gerenciar fila de admissões compartilhada entre múltiplos usuários.
 * Usa Supabase Realtime para sincronizar estado entre clientes.
 */
export function useFilaCompartilhada() {
  const { usuario } = useAuth();

  const [sessaoAtiva, setSessaoAtiva] = useState(null);
  const [filaRequisicoes, setFilaRequisicoes] = useState([]);
  const [filaStatus, setFilaStatus] = useState('idle');
  const [euSouProcessador, setEuSouProcessador] = useState(false);

  const sessaoIdRef = useRef(null);
  const meuLockRef = useRef(null); // ID do item que estou revisando

  // ============================================================
  // CARREGAR SESSÃO ATIVA AO MONTAR
  // ============================================================
  useEffect(() => {
    const carregarSessaoAtiva = async () => {
      try {
        const { data, error } = await supabase
          .from('fila_sessao')
          .select('*')
          .in('status', ['processando', 'revisao'])
          .order('created_at', { ascending: false })
          .limit(1);

        if (error) {
          console.error('[FilaCompartilhada] Erro ao buscar sessão:', error);
          return;
        }

        if (data && data.length > 0) {
          // Filtrar: finalizar automaticamente sessoes de dias anteriores
          const hoje = new Date().toISOString().split('T')[0];
          let sessaoHoje = null;

          for (const s of data) {
            const dataSessao = s.created_at ? s.created_at.split('T')[0] : '';
            if (dataSessao === hoje) {
              sessaoHoje = s;
              break;
            } else {
              // Sessao de dia anterior -> finalizar automaticamente
              console.log(`[FilaCompartilhada] Finalizando sessao antiga ${s.id} de ${dataSessao}`);
              await supabase
                .from('fila_sessao')
                .update({ status: 'finalizado' })
                .eq('id', s.id);
            }
          }

          if (sessaoHoje) {
            const sessao = sessaoHoje;
            setSessaoAtiva(sessao);
            sessaoIdRef.current = sessao.id;
            setFilaStatus(sessao.status);
            setEuSouProcessador(sessao.iniciado_por === usuario?.id);

            // Carregar items da sessão
            const { data: items, error: itemsError } = await supabase
              .from('fila_admissao')
              .select('*')
              .eq('sessao_id', sessao.id)
              .order('ordem', { ascending: true });

            if (!itemsError && items) {
              setFilaRequisicoes(items);
            }
          }
        }
      } catch (err) {
        console.error('[FilaCompartilhada] Erro:', err);
      }
    };

    if (usuario?.id) {
      carregarSessaoAtiva();
    }
  }, [usuario?.id]);

  // ============================================================
  // SUBSCRIPTIONS REALTIME
  // ============================================================
  useEffect(() => {
    if (!sessaoIdRef.current) return;

    const sessaoChannel = supabase
      .channel('fila-sessao-changes')
      .on('postgres_changes', {
        event: '*',
        schema: 'public',
        table: 'fila_sessao',
        filter: `id=eq.${sessaoIdRef.current}`
      }, (payload) => {
        if (payload.new) {
          setSessaoAtiva(payload.new);
          setFilaStatus(payload.new.status);
        }
      })
      .subscribe();

    const itemsChannel = supabase
      .channel('fila-items-changes')
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'fila_admissao',
        filter: `sessao_id=eq.${sessaoIdRef.current}`
      }, (payload) => {
        setFilaRequisicoes(prev => {
          const exists = prev.some(item => item.id === payload.new.id);
          if (exists) return prev;
          return [...prev, payload.new].sort((a, b) => a.ordem - b.ordem);
        });
      })
      .on('postgres_changes', {
        event: 'UPDATE',
        schema: 'public',
        table: 'fila_admissao',
        filter: `sessao_id=eq.${sessaoIdRef.current}`
      }, (payload) => {
        setFilaRequisicoes(prev =>
          prev.map(item => item.id === payload.new.id ? payload.new : item)
        );
      })
      .subscribe();

    return () => {
      supabase.removeChannel(sessaoChannel);
      supabase.removeChannel(itemsChannel);
    };
  }, [sessaoAtiva?.id]);

  // ============================================================
  // CLEANUP: liberar lock ao fechar aba
  // ============================================================
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (meuLockRef.current) {
        // Usar sendBeacon para garantir que o request sai antes do unload
        // Como não temos endpoint REST direto, liberamos via supabase update
        navigator.sendBeacon && supabase
          .from('fila_admissao')
          .update({ status: 'processado', revisado_por: null, revisado_por_nome: null, lock_timestamp: null })
          .eq('id', meuLockRef.current)
          .then();
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // Cleanup no unmount também
      if (meuLockRef.current) {
        supabase
          .from('fila_admissao')
          .update({ status: 'processado', revisado_por: null, revisado_por_nome: null, lock_timestamp: null })
          .eq('id', meuLockRef.current)
          .then();
      }
    };
  }, []);

  // ============================================================
  // AÇÕES
  // ============================================================

  const iniciarSessao = useCallback(async (sessaoId, items, user) => {
    sessaoIdRef.current = sessaoId;

    // Criar sessão
    const { error: sessaoError } = await supabase
      .from('fila_sessao')
      .insert({
        id: sessaoId,
        status: 'processando',
        total_itens: items.length,
        itens_processados: 0,
        iniciado_por: user?.id || 'anon',
        iniciado_por_nome: user?.nome_completo || user?.username || 'Anônimo'
      });

    if (sessaoError) {
      console.error('[FilaCompartilhada] Erro ao criar sessão:', sessaoError);
      throw sessaoError;
    }

    // Inserir items
    const { error: itemsError } = await supabase
      .from('fila_admissao')
      .insert(items);

    if (itemsError) {
      console.error('[FilaCompartilhada] Erro ao inserir items:', itemsError);
      throw itemsError;
    }

    setSessaoAtiva({
      id: sessaoId,
      status: 'processando',
      total_itens: items.length,
      itens_processados: 0,
      iniciado_por: user?.id || 'anon',
      iniciado_por_nome: user?.nome_completo || user?.username || 'Anônimo'
    });
    setFilaStatus('processando');
    setEuSouProcessador(true);
    setFilaRequisicoes(items.map((item, idx) => ({ ...item, id: item.id || `temp-${idx}` })));
  }, []);

  const atualizarItem = useCallback(async (itemId, dados) => {
    const { error } = await supabase
      .from('fila_admissao')
      .update(dados)
      .eq('id', itemId);

    if (error) {
      console.error('[FilaCompartilhada] Erro ao atualizar item:', error);
    }

    // Atualizar localmente também (para o processador que não espera o Realtime)
    setFilaRequisicoes(prev =>
      prev.map(item => item.id === itemId ? { ...item, ...dados } : item)
    );
  }, []);

  const atualizarSessao = useCallback(async (dados) => {
    if (!sessaoIdRef.current) return;
    const { error } = await supabase
      .from('fila_sessao')
      .update(dados)
      .eq('id', sessaoIdRef.current);

    if (error) {
      console.error('[FilaCompartilhada] Erro ao atualizar sessão:', error);
    }

    // Atualizar local
    setSessaoAtiva(prev => prev ? { ...prev, ...dados } : prev);
    if (dados.status) setFilaStatus(dados.status);
  }, []);

  const adquirirLockRevisao = useCallback(async (itemId) => {
    try {
      const { data, error } = await supabase.rpc('acquire_review_lock', {
        p_item_id: itemId,
        p_user_id: usuario?.id || 'anon',
        p_user_nome: usuario?.nome_completo || usuario?.username || 'Anônimo',
        p_lock_timeout_minutes: 5
      });

      if (error) {
        console.error('[FilaCompartilhada] Erro ao adquirir lock:', error);
        return false;
      }

      if (data === true) {
        // Liberar lock anterior se existir
        if (meuLockRef.current && meuLockRef.current !== itemId) {
          await liberarLockRevisao(meuLockRef.current);
        }
        meuLockRef.current = itemId;
        return true;
      }
      return false;
    } catch (err) {
      console.error('[FilaCompartilhada] Exceção ao adquirir lock:', err);
      return false;
    }
  }, [usuario]);

  const liberarLockRevisao = useCallback(async (itemId) => {
    const id = itemId || meuLockRef.current;
    if (!id) return;

    await supabase
      .from('fila_admissao')
      .update({
        status: 'processado',
        revisado_por: null,
        revisado_por_nome: null,
        lock_timestamp: null
      })
      .eq('id', id);

    if (meuLockRef.current === id) {
      meuLockRef.current = null;
    }
  }, []);

  const aprovarItem = useCallback(async (itemId, userOrId) => {
    const userId = typeof userOrId === 'string'
      ? userOrId
      : (userOrId?.id || usuario?.id);

    const userNome = typeof userOrId === 'object' && userOrId !== null
      ? (userOrId.nome_completo || userOrId.username || userOrId.aplis_usuario || '')
      : '';

    const nomeFallback = usuario?.nome_completo || usuario?.username || usuario?.aplis_usuario || '';
    const salvoPor = userNome || nomeFallback || userId || 'usuário';

    await supabase
      .from('fila_admissao')
      .update({
        status: 'salvo',
        salvo_por: salvoPor,
        revisado_por: null,
        revisado_por_nome: null,
        lock_timestamp: null
      })
      .eq('id', itemId);

    if (meuLockRef.current === itemId) {
      meuLockRef.current = null;
    }
  }, [usuario]);

  const pularItem = useCallback(async (itemId) => {
    await supabase
      .from('fila_admissao')
      .update({
        status: 'pulado',
        revisado_por: null,
        revisado_por_nome: null,
        lock_timestamp: null
      })
      .eq('id', itemId);

    if (meuLockRef.current === itemId) {
      meuLockRef.current = null;
    }
  }, []);

  const resetarSessao = useCallback(async () => {
    try {
      // Finalizar sessão ativa no Supabase
      if (sessaoIdRef.current) {
        await supabase.from('fila_sessao').update({ status: 'finalizado' }).eq('id', sessaoIdRef.current);
      } else {
        // Tentar finalizar qualquer sessão de hoje em estado processando/revisao
        const hoje = new Date().toISOString().split('T')[0];
        const { data: sessoes } = await supabase
          .from('fila_sessao')
          .select('id')
          .in('status', ['processando', 'revisao'])
          .gte('created_at', hoje);
        if (sessoes?.length) {
          const ids = sessoes.map(s => s.id);
          await supabase.from('fila_sessao').update({ status: 'finalizado' }).in('id', ids);
        }
      }
    } catch (err) {
      console.error('[FilaCompartilhada] Erro ao resetar sessão:', err);
    } finally {
      // Resetar estado local sempre
      sessaoIdRef.current = null;
      meuLockRef.current = null;
      setSessaoAtiva(null);
      setFilaRequisicoes([]);
      setFilaStatus('idle');
      setEuSouProcessador(false);
    }
  }, []);

  return {
    filaRequisicoes,
    filaStatus,
    sessaoAtiva,
    euSouProcessador,

    iniciarSessao,
    atualizarItem,
    atualizarSessao,
    adquirirLockRevisao,
    liberarLockRevisao,
    aprovarItem,
    pularItem,
    resetarSessao,
  };
}
