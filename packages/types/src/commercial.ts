export type PaymentGatewayType = 'TTC_GATEWAY' | 'SELLER_GATEWAY';
export type SellerCommercialModel = 'COMMISSION' | 'SUBSCRIPTION';
export type SellerRestrictionLevel = 'NONE' | 'WARNING' | 'MARKETPLACE_RESTRICTED' | 'WHITE_LABEL_RESTRICTED' | 'FULL_SUSPENSION';
export type PaymentStatus = 'PENDING' | 'SUCCEEDED' | 'FAILED' | 'OUTSTANDING' | 'REFUNDED' | 'PARTIALLY_REFUNDED';
export type InvoiceStatus = 'PENDING' | 'PAID' | 'OVERDUE' | 'CANCELLED';
export type SettlementStatus = 'SCHEDULED' | 'PROCESSING' | 'SETTLED' | 'FAILED';
export type PickupStatus = 'SCHEDULED' | 'DETAILS_SUBMITTED' | 'APPROVED' | 'REJECTED' | 'COMPLETED';

export interface SellerCommercialConfig {
  id: string;
  sellerId: string;
  tenantId: string;
  commercialModel: SellerCommercialModel;
  commissionRatePercent: string; // Decimal as string
  subscriptionFee: string;
  marketplaceGateway: PaymentGatewayType;
  whiteLabelGateway: PaymentGatewayType;
  paymentRequiredBeforePickup: boolean;
  outstandingReceivableAllowed: boolean;
  paymentDeadlineDays: number;
  restrictionLevel: SellerRestrictionLevel;
  createdAt: string;
  updatedAt: string;
}

export interface Payment {
  id: string;
  orderId: string;
  tenantId: string;
  sellerId: string;
  customerId: string;
  gatewayType: PaymentGatewayType;
  status: PaymentStatus;
  currency: string;
  amount: string;
  gatewayFee: string;
  gatewayTax: string;
  ttcCommission: string;
  ttcCommissionTax: string;
  refundedAmount: string;
  retainedAmount: string;
  gatewayTransactionId?: string;
  settledAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Refund {
  id: string;
  paymentId: string;
  amount: string;
  reason?: string;
  gatewayFeeReversed: string;
  gatewayTaxReversed: string;
  createdAt: string;
}

export interface SellerBillingInvoice {
  id: string;
  sellerId: string;
  tenantId: string;
  invoiceMonth: string; // YYYY-MM
  dueDate: string;
  status: InvoiceStatus;
  currency: string;
  subtotal: string;
  taxTotal: string;
  penaltyTotal: string;
  totalAmount: string;
  paidAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface SellerSettlement {
  id: string;
  sellerId: string;
  tenantId: string;
  gatewayType: PaymentGatewayType;
  status: SettlementStatus;
  currency: string;
  amount: string;
  scheduledFor: string;
  processedAt?: string;
  referenceId?: string;
  createdAt: string;
}

export interface OrderPickup {
  id: string;
  orderId: string;
  tenantId: string;
  sellerId: string;
  status: PickupStatus;
  actualPickupAt?: string;
  detailsSubmittedAt?: string;
  approvedAt?: string;
  rejectionReason?: string;
  actualDetails?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}
