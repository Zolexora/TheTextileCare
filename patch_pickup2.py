import re

with open("backend/app/services/pickup.py", "r") as f:
    content = f.read()

recalc_code = """
        # --- Automatic Recalculation Phase 8 ---
        from app.models.order import Order
        order = self.db.get(Order, pickup.order_id)
        
        needs_recalc = False
        for item in order.items:
            if item.price_policy_snapshot and item.price_policy_snapshot.get("recalculation_enabled"):
                needs_recalc = True
                break
                
        if needs_recalc:
            from app.schemas.pricing import PricingCalculationRequest, PricingCalculationItemRequest
            from app.services.pricing import PricingService
            pricing_svc = PricingService(self.db)
            
            # Reconstruct PricingCalculationRequest from actual_details
            # actual_details might be like {"items": [{"service_id": "...", "service_item_id": "...", "verified_quantity": 5}]}
            items = []
            actual_items_map = {}
            if actual_details and "items" in actual_details:
                for ad in actual_details["items"]:
                    key = (str(ad.get("service_id")), str(ad.get("service_item_id")))
                    actual_items_map[key] = ad
            
            for item in order.items:
                # Get updated quantity or fallback to original
                key = (str(item.service_id), str(item.service_item_id))
                updated_qty = item.quantity
                updated_weight = None
                if key in actual_items_map:
                    ad = actual_items_map[key]
                    if "verified_quantity" in ad:
                        updated_qty = ad["verified_quantity"]
                    if "measured_weight_kg" in ad:
                        updated_weight = ad["measured_weight_kg"]
                        
                items.append(PricingCalculationItemRequest(
                    service_id=item.service_id,
                    service_item_id=item.service_item_id,
                    quantity=updated_qty,
                    weight=updated_weight,
                    unit_type=item.unit_type,
                    addon_ids=[a.service_addon_id for a in item.addons]
                ))
                
            pricing_request = PricingCalculationRequest(
                seller_id=order.seller_id,
                branch_id=order.branch_id,
                currency=order.currency,
                items=items,
            )
            
            pricing_result = pricing_svc.calculate(tenant_id=tenant_id, request=pricing_request)
            
            # Update order totals
            from decimal import Decimal, ROUND_HALF_UP
            def _round(v: Decimal) -> Decimal:
                return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                
            order.subtotal = _round(pricing_result.subtotal)
            order.discount_total = _round(pricing_result.total_discounts)
            order.surcharge_total = _round(pricing_result.total_surcharges)
            order.tax_total = _round(pricing_result.total_tax)
            order.grand_total = _round(pricing_result.grand_total)
            
            import json
            def _decimal_default(obj):
                import uuid
                if isinstance(obj, Decimal): return str(obj)
                if isinstance(obj, uuid.UUID): return str(obj)
                raise TypeError
            order.pricing_snapshot = json.loads(json.dumps(pricing_result.model_dump(), default=_decimal_default))
            
            for idx, item in enumerate(order.items):
                if idx < len(pricing_result.items):
                    price_item = pricing_result.items[idx]
                    item.quantity = price_item.quantity
                    item.unit_price = _round(price_item.unit_price)
                    item.subtotal = _round(price_item.subtotal)
                    item.discount_amount = _round(price_item.discounts)
                    item.surcharge_amount = _round(price_item.surcharges)
                    item.tax_amount = _round(price_item.tax)
                    item.total_amount = _round(price_item.total)
                    item.pricing_snapshot = json.loads(json.dumps(price_item.model_dump(), default=_decimal_default))
"""

target = r'(result = self\.repo\.submit_actual_details\([\s\S]*?\n\s*actual_details=actual_details,\n\s*\))'
match = re.search(target, content)
if match:
    content = content[:match.end()] + "\n" + recalc_code + "\n" + content[match.end():]
    with open("backend/app/services/pickup.py", "w") as f:
        f.write(content)
else:
    print("Could not find insertion point for recalculation")
