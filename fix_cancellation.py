with open("backend/app/models/order.py", "r") as f:
    content = f.read()

# Revert CUSTOMER_CANCELLABLE_STATUSES
content = content.replace(
    'OrderStatus.CONFIRMED,\n    OrderStatus.IN_PROGRESS,\n}',
    'OrderStatus.CONFIRMED,\n}'
)

# Wait, if I revert ALLOWED_TRANSITIONS as well, then `IN_PROGRESS` -> `CANCELLED` is forbidden.
# Let's just revert CUSTOMER_CANCELLABLE_STATUSES so the test passes, 
# and keep ALLOWED_TRANSITIONS with IN_PROGRESS -> CANCELLED?
# Let's check rule 26.
# If the test `test_customer_cannot_cancel_in_progress_order` exists, it means the system explicitly forbids normal customer cancellation during IN_PROGRESS.
# But `PickupService` rejecting a pickup and policy being CANCEL is a system action.
with open("backend/app/models/order.py", "w") as f:
    f.write(content)
