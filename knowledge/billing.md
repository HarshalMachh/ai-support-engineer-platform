# Billing, Invoices and Payments

## Plans

Acme Cloud offers Starter, Business and Enterprise plans. Plans are billed monthly or annually
in advance. Plan changes are available under **Settings → Billing → Plan**.

- **Upgrades** take effect immediately. The customer is charged a prorated amount for the
  remainder of the current billing period.
- **Downgrades** take effect at the start of the next billing period. No partial refunds are issued
  for downgrades.

## Invoices

Invoices are generated on the billing date and emailed to the billing contact. All past invoices
can be downloaded as PDF from **Settings → Billing → Invoices**. To change the company name, VAT
number or billing address shown on future invoices, update **Billing details**. Issued invoices
cannot be edited; support can re-issue an invoice within 30 days of the original date.

## Failed payments

When a card payment fails:

1. The customer receives an email and a banner appears in the dashboard.
2. Payment is retried automatically after 3, 5 and 7 days.
3. If all retries fail, the account enters a **14-day grace period**, after which it is downgraded
   to the free tier. Data is never deleted because of failed payments.

Common reasons for failures: expired card, insufficient funds, 3-D Secure authentication not
completed, or the bank blocking an international transaction. The customer can update the card
under **Settings → Billing → Payment method** and click **Retry payment**.

## Duplicate charges

A duplicate charge is almost always a pending authorization that disappears within 3–5 business
days. Support should check the billing console: if two *settled* charges exist for the same invoice,
refund the duplicate from **Billing console → Invoice → Refund**.

## Refund policy

- Annual plans may be refunded in full within 14 days of purchase.
- Monthly plans are not refunded for partial months.
- Refunds return to the original payment method in 5–10 business days.

Refunds above $500 require approval from the billing team lead.

## Information to collect

- account ID or workspace name
- invoice number
- last four digits of the card (never the full card number)
- date and amount of the charge
