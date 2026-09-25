import stripe
from fastapi import APIRouter, HTTPException, Request, Header
from app.core.config import get_settings
from app.core.database import supabase  # <--- Make sure supabase client is imported

router = APIRouter(prefix="/api/billing", tags=["Billing & Subscriptions"])
settings = get_settings()

stripe.api_key = settings.STRIPE_SECRET_KEY

@router.post("/create-checkout")
def create_checkout_session(data: dict):
    user_id = data.get("user_id")
    email = data.get("email")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": settings.STRIPE_PRO_PRICE_ID,
                "quantity": 1,
            }],
            mode="subscription",
            client_reference_id=user_id,  # Links the Supabase user_id to Stripe
            customer_email=email,
            success_url="https://mailpolish.app/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://mailpolish.app/cancel",
        )
        return {"success": True, "checkout_url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Listen for successful payment completion
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # Extract the user_id and customer reference
        user_id = session.get("client_reference_id")
        stripe_customer_id = session.get("customer")
        
        if user_id:
            # INSTANT UPGRADE: Update Supabase user profile
            supabase.table("user_profiles").update({
                "tier": "pro",
                "subscription_status": "active",
                "stripe_customer_id": stripe_customer_id
            }).eq("id", user_id).execute()

    return {"status": "success"}