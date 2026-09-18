import React from 'react';
import { SafeAreaView, StyleSheet, Text, View } from 'react-native';
export default function App() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <Text style={styles.label}>The Textile Care Marketplace</Text>
        <Text style={styles.subtitle}>Mobile application foundation</Text>
      </View>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#f8fafc' },
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  label: { fontSize: 28, fontWeight: '700', color: '#0f172a' },
  subtitle: { marginTop: 8, fontSize: 16, color: '#475569' },
});
