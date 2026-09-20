'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Mail, Lock, Eye, EyeOff, User, ArrowRight } from 'lucide-react';
import { Button, Input, Label, Card, CardContent, Alert, AlertDescription } from '@/components/ui';
import { useAuth } from '@/lib/auth-context';
import { Logo } from '@ttc/ui';

export default function LoginPage() {
  const router = useRouter();
  const { signIn, signUp } = useAuth();

  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (mode === 'login') {
        await signIn(email, password);
      } else {
        await signUp(email, password, name);
      }
      // Redirect after auth
      const params = new URLSearchParams(window.location.search);
      router.push(params.get('redirect') ?? '/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 text-center">
          <Link href="/" aria-label="Home">
            <Logo theme="light" size="sm" className="mx-auto dark:hidden" />
            <Logo theme="dark" size="sm" className="mx-auto hidden dark:block" />
          </Link>
          <h1 className="mt-4 text-2xl font-bold text-foreground">
            {mode === 'login' ? 'Welcome back' : 'Create account'}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {mode === 'login'
              ? 'Sign in to manage your orders and preferences.'
              : 'Join thousands of happy customers.'}
          </p>
        </div>

        <Card>
          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              {mode === 'signup' && (
                <div>
                  <Label htmlFor="name">Full Name</Label>
                  <div className="relative mt-1">
                    <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                    <Input
                      id="name"
                      type="text"
                      placeholder="Your name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="pl-9"
                      required
                      autoComplete="name"
                    />
                  </div>
                </div>
              )}

              <div>
                <Label htmlFor="email">Email</Label>
                <div className="relative mt-1">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-9"
                    required
                    autoComplete={mode === 'login' ? 'username' : 'email'}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="password">Password</Label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-9 pr-10"
                    required
                    minLength={8}
                    autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {mode === 'login' && (
                <div className="flex justify-end">
                  <Link href="/forgot-password" className="text-xs text-accent hover:underline">
                    Forgot password?
                  </Link>
                </div>
              )}

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full" isLoading={submitting}>
                {mode === 'login' ? 'Sign In' : 'Create Account'}
                <ArrowRight className="ml-2 h-4 w-4" aria-hidden />
              </Button>
            </form>

            <div className="mt-4 text-center text-sm">
              {mode === 'login' ? (
                <p className="text-muted-foreground">
                  Don&apos;t have an account?{' '}
                  <button onClick={() => setMode('signup')} className="font-medium text-accent hover:underline">
                    Sign up
                  </button>
                </p>
              ) : (
                <p className="text-muted-foreground">
                  Already have an account?{' '}
                  <button onClick={() => setMode('login')} className="font-medium text-accent hover:underline">
                    Sign in
                  </button>
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          By continuing, you agree to our{' '}
          <Link href="/terms" className="hover:underline">Terms</Link>
          {' '}and{' '}
          <Link href="/privacy" className="hover:underline">Privacy Policy</Link>.
        </p>
      </div>
    </div>
  );
}
