import { Button, Card } from '@ttc/ui';
export default function Page() {
  return (
    <main className="min-h-screen bg-slate-950 p-10 text-slate-50">
      <div className="mx-auto max-w-5xl">
        <Card className="space-y-5 border-slate-700 bg-slate-900 text-slate-50">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-violet-400">Admin</p>
          <h1 className="text-4xl font-bold">The Textile Care Admin</h1>
          <p className="text-slate-300">Internal administration placeholder for shared platform governance.</p>
          <div className="flex gap-3">
            <Button>Overview</Button>
            <Button variant="secondary">Operations</Button>
          </div>
        </Card>
      </div>
    </main>
  );
}
