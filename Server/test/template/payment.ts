export interface IPaymentGateway {
    processPayment(amount: number): boolean;
    refundPayment(transactionId: string): boolean;
}

export class StripeGateway implements IPaymentGateway {
    processPayment(amount: number): boolean {
        console.log(`Processing $${amount} via Stripe...`);
        return true;
    }

    refundPayment(transactionId: string): boolean {
        console.log(`Refunding transaction ${transactionId} via Stripe...`);
        return true;
    }
}

export function handleCheckout(gateway: IPaymentGateway, total: number) {
    const success = gateway.processPayment(total);
    if (success) {
        console.log("Checkout complete!");
    } else {
        console.log("Checkout failed.");
    }
}
