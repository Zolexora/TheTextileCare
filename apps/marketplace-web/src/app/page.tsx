import { Button, Card, Logo } from '@ttc/ui';
export default function Page() {
  return (
    <main className="min-h-screen bg-slate-50 p-10 text-slate-900">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="flex items-center justify-between border-b border-slate-200 pb-6">
          <Logo theme="light" size="sm" />
          <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-700">Marketplace</span>
        </header>
        <Card className="space-y-5">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-600">Marketplace</p>
          <h1 className="text-4xl font-bold">The Textile Care Marketplace</h1>
          <p className="text-slate-600">Foundation placeholder for the shared customer marketplace experience.</p>
          <div className="flex gap-3">
            <Button>Explore</Button>
            <Button variant="secondary">Account</Button>
          </div>
        </Card>
      </div>
    </main>
  );
}
