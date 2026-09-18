import React from 'react';
import { SafeAreaView, StyleSheet, Text, View } from 'react-native';
export default function App() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <Text style={styles.label}>The Textile Care Seller</Text>
        <Text style={styles.subtitle}>Seller mobile foundation</Text>
      </View>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#f0fdf4' },
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  label: { fontSize: 28, fontWeight: '700', color: '#052e16' },
  subtitle: { marginTop: 8, fontSize: 16, color: '#166534' },
});
