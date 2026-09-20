'use client';

import { HelpCircle } from 'lucide-react';
import { Card, CardContent, Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui';
import Link from 'next/link';

const FAQS = [
  {
    q: 'How does pickup work?',
    a: 'Choose a pickup slot during checkout. Our partner seller will arrange collection from your address.',
  },
  {
    q: 'How long does laundry take?',
    a: 'Turnaround time depends on the seller and service. You can see the estimated time before placing your order.',
  },
  {
    q: 'Can I cancel an order?',
    a: 'You can cancel a pending or confirmed order from the order details page. Cancellations after pickup may not be possible.',
  },
  {
    q: 'What if my clothes are damaged?',
    a: 'Please raise a support ticket from the order details page. Our team will investigate and resolve the issue.',
  },
  {
    q: 'How do I track my order?',
    a: 'Go to My Orders and select an order to see its live status and timeline.',
  },
];

export default function SupportPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6 lg:px-8">
      <h1 className="mb-6 text-xl font-bold text-foreground">Help &amp; Support</h1>

      <div className="mb-6">
        <Card>
          <CardContent className="p-5">
            <h2 className="mb-1 font-semibold text-foreground">Frequently Asked Questions</h2>
            <Accordion type="single" collapsible className="mt-2">
              {FAQS.map((faq, i) => (
                <AccordionItem key={i} value={`faq-${i}`}>
                  <AccordionTrigger className="text-sm text-left">{faq.q}</AccordionTrigger>
                  <AccordionContent className="text-sm text-muted-foreground">{faq.a}</AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-5 text-center">
          <HelpCircle className="mx-auto mb-3 h-8 w-8 text-muted-foreground" aria-hidden />
          <h2 className="font-semibold text-foreground mb-1">Still need help?</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Can&apos;t find what you&apos;re looking for? Contact our support team.
          </p>
          <Link
            href="mailto:support@thetextilecare.com"
            className="inline-flex h-9 items-center justify-center rounded-md border border-input bg-background px-4 text-sm font-medium hover:bg-muted transition-colors"
          >
            Email Support
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
