import { Button, Card, Logo } from '@ttc/ui';
export default function Page() {
  return (
    <main className="min-h-screen bg-slate-950 p-10 text-slate-50">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="flex items-center justify-between border-b border-slate-800 pb-6">
          <Logo theme="dark" size="sm" />
          <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-violet-400">Admin Console</span>
        </header>
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
