import { Button, Card } from '@ttc/ui';
export default function Page() {
  return (
    <main className="min-h-screen bg-slate-50 p-10 text-slate-900">
      <div className="mx-auto max-w-5xl">
        <Card className="space-y-5">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-600">Seller</p>
          <h1 className="text-4xl font-bold">The Textile Care Seller</h1>
          <p className="text-slate-600">Shared seller SaaS foundation without business workflows.</p>
          <div className="flex gap-3">
            <Button>Dashboard</Button>
            <Button variant="secondary">Setup</Button>
          </div>
        </Card>
      </div>
    </main>
  );
}
