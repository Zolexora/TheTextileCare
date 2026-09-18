import React from 'react';
import { SafeAreaView, StyleSheet, Text, View } from 'react-native';
import type { TenantConfiguration } from '@ttc/branding';

const MOCK_CONFIG: TenantConfiguration = {
  tenantId: 'tenant-123',
  name: 'The Textile Care',
  theme: {
    primaryColor: '#062B5F',
    secondaryColor: '#f8fafc',
  },
  assets: {},
  features: {
    'feature.seller_dashboard': true,
  }
};

export default function App() {
  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: MOCK_CONFIG.theme.secondaryColor }]}>
      <View style={styles.container}>
        <Text style={[styles.label, { color: MOCK_CONFIG.theme.primaryColor }]}>{MOCK_CONFIG.name} Seller</Text>
        <Text style={styles.subtitle}>Tenant: {MOCK_CONFIG.tenantId}</Text>
        
        {MOCK_CONFIG.features['feature.seller_dashboard'] && (
          <View style={[styles.badge, { backgroundColor: MOCK_CONFIG.theme.primaryColor }]}>
            <Text style={styles.badgeText}>Dashboard Enabled</Text>
          </View>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  label: { fontSize: 28, fontWeight: '700' },
  subtitle: { marginTop: 8, fontSize: 16, color: '#475569' },
  badge: { marginTop: 16, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16 },
  badgeText: { color: '#ffffff', fontWeight: '600' }
});
