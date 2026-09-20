with open("backend/app/services/order.py", "r") as f:
    content = f.read()

content = content.replace('"addons_by_id": addons_by_id,\n            ,\n', '"addons_by_id": addons_by_id,\n')
with open("backend/app/services/order.py", "w") as f:
    f.write(content)
