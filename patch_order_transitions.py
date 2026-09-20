with open("backend/app/models/order.py", "r") as f:
    content = f.read()

content = content.replace(
    'OrderStatus.IN_PROGRESS: [OrderStatus.COMPLETED],',
    'OrderStatus.IN_PROGRESS: [OrderStatus.COMPLETED, OrderStatus.CANCELLED],'
)
with open("backend/app/models/order.py", "w") as f:
    f.write(content)
