import { Button, Card, Logo } from '@ttc/ui';
import type { TenantConfiguration } from '@ttc/branding';

// Simulated configuration resolution (in reality, this would fetch from /api/v1/public/configuration)
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
    'feature.seller_branches': true,
  }
};

export default function Page() {
  return (
    <main className="min-h-screen p-10" style={{ backgroundColor: MOCK_CONFIG.theme.secondaryColor, color: MOCK_CONFIG.theme.primaryColor }}>
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="flex items-center justify-between border-b pb-6">
          <Logo theme="light" size="sm" />
          <span className="rounded-full px-3 py-1 text-xs font-semibold" style={{ backgroundColor: MOCK_CONFIG.theme.primaryColor, color: '#fff' }}>
            Seller Portal - {MOCK_CONFIG.name}
          </span>
        </header>
        <Card className="space-y-5 shadow-sm">
          <h1 className="text-4xl font-bold">Welcome to {MOCK_CONFIG.name}</h1>
          <p className="text-lg opacity-80">
            Tenant Identity: <code>{MOCK_CONFIG.tenantId}</code>
          </p>
          <div className="mt-8 flex gap-4">
            <Button variant="default" style={{ backgroundColor: MOCK_CONFIG.theme.primaryColor }}>View Orders</Button>
            {MOCK_CONFIG.features['feature.seller_branches'] && (
              <Button variant="outline">Manage Branches</Button>
            )}
          </div>
        </Card>
      </div>
    </main>
  );
}
