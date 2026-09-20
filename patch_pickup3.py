import re

with open("backend/app/models/pickup.py", "r") as f:
    content = f.read()
    
# Add PRICE_DISPUTE to PickupStatus
if "PRICE_DISPUTE" not in content:
    content = content.replace('REJECTED = "REJECTED"', 'REJECTED = "REJECTED"\n    PRICE_DISPUTE = "PRICE_DISPUTE"')
    content = content.replace('COMPLETED = "COMPLETED"', 'COMPLETED = "COMPLETED"\n    CANCELLED = "CANCELLED"')
    with open("backend/app/models/pickup.py", "w") as f:
        f.write(content)

with open("backend/app/services/pickup.py", "r") as f:
    content = f.read()
    
# Modify approve_pickup to lock price
approve_target = r'(result = self\.repo\.approve_details\([\s\S]*?\n\s*customer_id=customer\.id,\n\s*\))'
approve_patch = """
        from app.models.order import Order
        order = self.db.get(Order, order_id)
        if order:
            from datetime import datetime, timezone
            order.price_locked_at = datetime.now(timezone.utc)
"""
match = re.search(approve_target, content)
if match:
    content = content[:match.end()] + "\n" + approve_patch + "\n" + content[match.end():]

# Modify reject_pickup logic
reject_target = r'(result = self\.repo\.reject_details\([\s\S]*?\n\s*reason=reason,\n\s*\))'
reject_patch = """
        # --- Customer Price Rejection Policy ---
        from app.models.order import Order
        order = self.db.get(Order, order_id)
        
        policy = "CANCEL" # Default
        if order:
            for item in order.items:
                if item.price_policy_snapshot and item.price_policy_snapshot.get("price_rejection_policy") == "PRICE_DISPUTE":
                    policy = "PRICE_DISPUTE"
                    break
        
        if policy == "CANCEL":
            from app.services.order import OrderService
            order_svc = OrderService(self.db)
            try:
                # Cancel the order
                order_svc.cancel_order_as_customer(customer_user_id, order_id, f"Customer rejected pickup details: {reason}")
            except Exception:
                pass
            result.status = "CANCELLED"
        elif policy == "PRICE_DISPUTE":
            result.status = "PRICE_DISPUTE"
"""
match = re.search(reject_target, content)
if match:
    content = content[:match.end()] + "\n" + reject_patch + "\n" + content[match.end():]

with open("backend/app/services/pickup.py", "w") as f:
    f.write(content)

