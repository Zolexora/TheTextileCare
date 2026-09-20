with open("backend/app/models/order.py", "r") as f:
    content = f.read()

content = content.replace(
    'OrderStatus.CONFIRMED,\n}',
    'OrderStatus.CONFIRMED,\n    OrderStatus.IN_PROGRESS,\n}'
)
with open("backend/app/models/order.py", "w") as f:
    f.write(content)
