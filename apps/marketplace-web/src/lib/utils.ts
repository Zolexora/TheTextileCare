import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Merge Tailwind classes safely, resolving conflicts. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format currency for display. Backend sends decimal strings. */
export function formatCurrency(
  amount: string | number,
  currency = 'INR',
  locale = 'en-IN'
): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return '—';
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(num);
}

/** Format a date string for display. */
export function formatDate(
  dateStr: string,
  options: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' },
  locale = 'en-IN'
): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return new Intl.DateTimeFormat(locale, options).format(d);
}

/** Format a time string from ISO for display. */
export function formatTime(dateStr: string, locale = 'en-IN'): string {
  return formatDate(dateStr, { hour: '2-digit', minute: '2-digit' }, locale);
}

/** Generate initials from a display name. */
export function getInitials(name: string | null | undefined, fallback = '?'): string {
  if (!name) return fallback;
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
}

/** Truncate text to a max length. */
export function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max).trimEnd() + '…' : text;
}
