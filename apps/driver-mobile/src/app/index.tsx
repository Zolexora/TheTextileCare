import React from 'react';
import { SafeAreaView, StyleSheet, Text, View } from 'react-native';
export default function App() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <Text style={styles.label}>The Textile Care Driver</Text>
        <Text style={styles.subtitle}>Single shared driver app foundation</Text>
      </View>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#0f172a' },
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  label: { fontSize: 28, fontWeight: '700', color: '#f8fafc' },
  subtitle: { marginTop: 8, fontSize: 16, color: '#cbd5e1' },
});
