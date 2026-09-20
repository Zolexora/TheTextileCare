'use client';

import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin, Navigation, Search, ChevronRight, Loader2 } from 'lucide-react';
import { Button, Input, Card, CardContent, Alert, AlertTitle, AlertDescription } from '@/components/ui';
import { useLocationStore } from '@/lib/stores';

// ---------------------------------------------------------------------------
// GPS permission flow
// ---------------------------------------------------------------------------

function GpsButton({ onLocation }: { onLocation: (lat: number, lon: number) => void }) {
  const [status, setStatus] = useState<'idle' | 'requesting' | 'denied' | 'error'>('idle');

  const requestGps = useCallback(() => {
    setStatus('requesting');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setStatus('idle');
        onLocation(pos.coords.latitude, pos.coords.longitude);
      },
      (err) => {
        setStatus(err.code === err.PERMISSION_DENIED ? 'denied' : 'error');
      },
      { timeout: 10_000, maximumAge: 60_000 }
    );
  }, [onLocation]);

  return (
    <div className="space-y-2">
      <Button
        onClick={requestGps}
        disabled={status === 'requesting'}
        className="w-full"
        variant="outline"
      >
        {status === 'requesting' ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <Navigation className="mr-2 h-4 w-4 text-accent" aria-hidden />
        )}
        Use Current Location
      </Button>
      {status === 'denied' && (
        <Alert variant="warning">
          <AlertTitle>Location access denied</AlertTitle>
          <AlertDescription>
            Please enable location in your browser settings, or enter your pincode below.
          </AlertDescription>
        </Alert>
      )}
      {status === 'error' && (
        <Alert variant="destructive">
          <AlertTitle>Could not detect location</AlertTitle>
          <AlertDescription>
            Please enter your pincode manually.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pincode lookup — India Post API integration boundary
// ponytail: placeholder lookup — wire India Post API when available
// ---------------------------------------------------------------------------

interface PostOffice {
  office_name: string;
  district: string;
  state: string;
  pincode: string;
}

async function lookupPincode(pincode: string): Promise<PostOffice[]> {
  if (pincode.length !== 6) return [];
  try {
    // Integration boundary: India Post API
    const res = await fetch(`https://api.postalpincode.in/pincode/${pincode}`);
    const data = await res.json();
    if (data[0]?.Status === 'Success') {
      return (data[0].PostOffice ?? []).map((po: Record<string, string>) => ({
        office_name: po['Name'],
        district: po['District'],
        state: po['State'],
        pincode,
      }));
    }
  } catch {
    // Silently fall through — manual entry still works
  }
  return [];
}

function PincodeSearch({
  onSelect,
}: {
  onSelect: (pincode: string, locality: string, city: string, state: string) => void;
}) {
  const [pincode, setPincode] = useState('');
  const [offices, setOffices] = useState<PostOffice[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (pincode.length !== 6) return;
    setLoading(true);
    const results = await lookupPincode(pincode);
    setOffices(results);
    setSearched(true);
    setLoading(false);
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          type="tel"
          placeholder="Enter 6-digit pincode"
          value={pincode}
          maxLength={6}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, '');
            setPincode(v);
            setSearched(false);
          }}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          aria-label="Pincode"
        />
        <Button
          onClick={handleSearch}
          disabled={pincode.length !== 6 || loading}
          isLoading={loading}
          aria-label="Search pincode"
        >
          <Search className="h-4 w-4" aria-hidden />
        </Button>
      </div>

      {searched && offices.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No post offices found for {pincode}. Please check the pincode.
        </p>
      )}

      {offices.length > 0 && (
        <ul className="max-h-60 overflow-y-auto rounded-md border border-border" role="listbox" aria-label="Select locality">
          {offices.map((po, i) => (
            <li key={i}>
              <button
                role="option"
                aria-selected={false}
                onClick={() => onSelect(po.pincode, po.office_name, po.district, po.state)}
                className="flex w-full items-center justify-between px-3 py-2.5 text-left text-sm hover:bg-muted focus-visible:bg-muted focus-visible:outline-none"
              >
                <span>
                  <span className="font-medium">{po.office_name}</span>
                  <span className="ml-1 text-muted-foreground">{po.district}, {po.state}</span>
                </span>
                <ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Location page
// ---------------------------------------------------------------------------

export default function LocationPage() {
  const router = useRouter();
  const { setCoords, setPincode } = useLocationStore();

  const handleGps = useCallback(
    (lat: number, lon: number) => {
      setCoords({ latitude: lat, longitude: lon });
      router.push('/sellers');
    },
    [setCoords, router]
  );

  const handlePincode = useCallback(
    (pincode: string, locality: string, city: string, state: string) => {
      setPincode(pincode, locality, city, state);
      router.push('/sellers');
    },
    [setPincode, router]
  );

  return (
    <div className="mx-auto max-w-lg px-4 py-10 sm:px-6">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-accent/10">
          <MapPin className="h-7 w-7 text-accent" aria-hidden />
        </div>
        <h1 className="text-2xl font-bold text-foreground">Where are you?</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          We use your location to show sellers and services available near you.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-6 p-6">
          {/* GPS */}
          {typeof navigator !== 'undefined' && 'geolocation' in navigator && (
            <>
              <GpsButton onLocation={handleGps} />
              <div className="relative flex items-center">
                <div className="flex-1 border-t border-border" />
                <span className="mx-3 text-xs text-muted-foreground">or enter pincode</span>
                <div className="flex-1 border-t border-border" />
              </div>
            </>
          )}

          {/* Pincode search */}
          <PincodeSearch onSelect={handlePincode} />
        </CardContent>
      </Card>

      <p className="mt-4 text-center text-xs text-muted-foreground">
        You can browse without setting a location, but you&apos;ll need one before checkout.
      </p>
    </div>
  );
}
