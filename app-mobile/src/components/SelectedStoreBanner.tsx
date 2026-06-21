import React from 'react';
import {
  Alert,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useTenantStore } from '../store/tenant.store';
import { CORES, ESPACO, FONTE, RAIO } from '../theme';

export default function SelectedStoreBanner() {
  const { tenant, limparTenant } = useTenantStore();

  if (!tenant) return null;

  function trocarLoja() {
    Alert.alert(
      'Trocar loja',
      'A conta e os pedidos ficam vinculados a loja selecionada. Deseja escolher outra loja?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Trocar',
          style: 'destructive',
          onPress: () => {
            limparTenant().catch(() => {
              Alert.alert('Erro', 'Nao foi possivel trocar a loja agora.');
            });
          },
        },
      ],
    );
  }

  const endereco = [tenant.endereco, tenant.numero].filter(Boolean).join(', ');
  const bairroCidade = [tenant.bairro, [tenant.cidade, tenant.uf].filter(Boolean).join(' / ')]
    .filter(Boolean)
    .join(' - ');
  const localizacao = [endereco, bairroCidade].filter(Boolean).join(' - ');

  return (
    <View style={styles.card}>
      <View style={styles.logoBox}>
        <Image
          source={tenant.logo_url ? { uri: tenant.logo_url } : require("../../assets/icon.png")}
          style={styles.logo}
          resizeMode="contain"
        />
      </View>

      <View style={styles.info}>
        <Text style={styles.kicker}>Loja selecionada</Text>
        <Text style={styles.nome} numberOfLines={1}>
          {tenant.nome}
        </Text>
        {localizacao ? <Text style={styles.localizacao}>{localizacao}</Text> : null}
      </View>

      <TouchableOpacity style={styles.trocarBtn} onPress={trocarLoja}>
        <Text style={styles.trocarTexto}>Trocar</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#EEF2FF',
    borderRadius: RAIO.lg,
    borderWidth: 1,
    borderColor: '#C7D2FE',
    padding: ESPACO.md,
    marginBottom: ESPACO.md,
    gap: ESPACO.sm,
  },
  logoBox: {
    width: 44,
    height: 44,
    borderRadius: RAIO.md,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  logo: {
    width: 40,
    height: 40,
  },
  info: {
    flex: 1,
  },
  kicker: {
    fontSize: FONTE.pequena,
    color: CORES.textoSecundario,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  nome: {
    color: CORES.texto,
    fontSize: FONTE.normal,
    fontWeight: '700',
    marginTop: 2,
  },
  localizacao: {
    color: CORES.textoSecundario,
    fontSize: FONTE.pequena,
    marginTop: 2,
  },
  trocarBtn: {
    borderRadius: RAIO.circulo,
    paddingHorizontal: ESPACO.sm,
    paddingVertical: ESPACO.xs,
    backgroundColor: '#fff',
  },
  trocarTexto: {
    color: CORES.primario,
    fontSize: FONTE.pequena,
    fontWeight: '700',
  },
});
