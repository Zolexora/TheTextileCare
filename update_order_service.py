import re
with open("backend/app/services/order.py", "r") as f:
    content = f.read()

# Add imports for the new models
import_match = re.search(r'from app.models.catalog import (.*?)\n', content)
if import_match:
    old_import = import_match.group(0)
    new_import = old_import.replace('ServiceItem', 'ServiceItem, ServiceConfigurationVersion, PricePolicyVersion')
    content = content.replace(old_import, new_import)

# Modify _validate_and_snapshot_items to fetch policies
validate_items_regex = r'(def _validate_and_snapshot_items.*?addons_by_id\[str\(addon_req\.service_addon_id\)\] = addon\n\n)(.*?)(result\.append\({)'
match = re.search(validate_items_regex, content, re.DOTALL)
if match:
    prefix = match.group(1)
    indent = match.group(2)
    append_call = match.group(3)
    
    new_code = """
            # Fetch active policy and configuration version
            policy_version = (
                self.db.query(PricePolicyVersion)
                .filter(
                    PricePolicyVersion.service_id == svc.id,
                    PricePolicyVersion.tenant_id == catalog.tenant_id,
                )
                .order_by(PricePolicyVersion.version.desc())
                .first()
            )
            config_version = (
                self.db.query(ServiceConfigurationVersion)
                .filter(
                    ServiceConfigurationVersion.service_id == svc.id,
                    ServiceConfigurationVersion.tenant_id == catalog.tenant_id,
                )
                .order_by(ServiceConfigurationVersion.version.desc())
                .first()
            )
            
            price_policy_snapshot = {}
            if policy_version:
                price_policy_snapshot = {
                    "version": policy_version.version,
                    "recalculation_enabled": policy_version.recalculation_enabled,
                    "price_change_policy": policy_version.price_change_policy,
                    "price_rejection_policy": policy_version.price_rejection_policy
                }
"""
    content = content[:match.start()] + prefix + new_code + "\n            " + append_call + content[match.end():]

# Modify the result.append dictionary
append_dict_regex = r'(result\.append\({.*?)(}\))'
match = re.search(append_dict_regex, content, re.DOTALL)
if match:
    dict_content = match.group(1)
    suffix = match.group(2)
    new_dict_content = dict_content + """,
                "service_config_version_id": config_version.id if config_version else None,
                "price_policy_version_id": policy_version.id if policy_version else None,
                "price_policy_snapshot": price_policy_snapshot,
"""
    content = content[:match.start()] + new_dict_content + suffix + content[match.end():]

# Modify create_order OrderItem creation
create_item_regex = r'(order_item = OrderItem\([\s\S]*?)(pricing_snapshot=_to_json_safe\(price_item\.model_dump\(\)\) if price_item else {},\n\s*\))'
match = re.search(create_item_regex, content)
if match:
    new_fields = """
                service_configuration_version_id=catalog_item_data.get("service_config_version_id"),
                price_policy_version_id=catalog_item_data.get("price_policy_version_id"),
                applicable_rate=_round(price_item.unit_price) if price_item else Decimal("0.00"),
                price_policy_snapshot=catalog_item_data.get("price_policy_snapshot", {}),
"""
    content = content[:match.end(1)] + new_fields + match.group(2) + content[match.end():]

with open("backend/app/services/order.py", "w") as f:
    f.write(content)

