with open("backend/app/services/pickup.py", "r") as f:
    content = f.read()

content = content.replace(
    'order_svc.cancel_order_as_customer(customer_user_id, order_id, f"Customer rejected pickup details: {reason}")',
    'from app.models.order import OrderStatus\n                order_svc._transition(order, OrderStatus.CANCELLED, customer_user_id, f"Customer rejected pickup details: {reason}")'
)

with open("backend/app/services/pickup.py", "w") as f:
    f.write(content)
