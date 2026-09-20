from __future__ import annotations

from enum import Enum


class RoleName(str, Enum):
    PLATFORM_ADMIN = 'PLATFORM_ADMIN'
    PLATFORM_SUPPORT = 'PLATFORM_SUPPORT'
    TENANT_OWNER = 'TENANT_OWNER'
    TENANT_ADMIN = 'TENANT_ADMIN'
    TENANT_MEMBER = 'TENANT_MEMBER'
    TENANT_VIEWER = 'TENANT_VIEWER'

    # Phase 2 Seller Roles
    SELLER_OWNER = 'SELLER_OWNER'
    SELLER_ADMIN = 'SELLER_ADMIN'
    STAFF = 'STAFF'
    VIEWER = 'VIEWER'

    # Phase 7 Customer Role
    CUSTOMER = 'CUSTOMER'

    # Phase 8 Driver Role
    DRIVER = 'DRIVER'


class PermissionName(str, Enum):
    TENANT_READ = 'tenant.read'
    TENANT_MANAGE = 'tenant.manage'
    MEMBERSHIP_READ = 'membership.read'
    MEMBERSHIP_MANAGE = 'membership.manage'
    ROLE_READ = 'role.read'
    ROLE_MANAGE = 'role.manage'
    USER_READ = 'user.read'
    USER_MANAGE = 'user.manage'
    AUDIT_READ = 'audit.read'

    # Phase 2 Seller Permissions
    SELLER_READ = 'seller.read'
    SELLER_MANAGE = 'seller.manage'
    SELLER_BRANCHES_READ = 'seller.branches.read'
    SELLER_BRANCHES_MANAGE = 'seller.branches.manage'
    SELLER_STAFF_READ = 'seller.staff.read'
    SELLER_STAFF_MANAGE = 'seller.staff.manage'
    SELLER_SETTINGS_READ = 'seller.settings.read'
    SELLER_SETTINGS_MANAGE = 'seller.settings.manage'

    # Phase 4 Catalog Permissions
    CATALOG_READ = 'catalog.read'
    CATALOG_MANAGE = 'catalog.manage'
    CATALOG_PUBLISH = 'catalog.publish'
    CATALOG_CATEGORIES_READ = 'catalog.categories.read'
    CATALOG_CATEGORIES_MANAGE = 'catalog.categories.manage'
    CATALOG_SERVICES_READ = 'catalog.services.read'
    CATALOG_SERVICES_MANAGE = 'catalog.services.manage'
    CATALOG_ADDONS_READ = 'catalog.addons.read'
    CATALOG_ADDONS_MANAGE = 'catalog.addons.manage'
    CATALOG_ITEMS_READ = 'catalog.items.read'
    CATALOG_ITEMS_MANAGE = 'catalog.items.manage'

    # Phase 3 Configuration Permissions
    CONFIGURATION_READ = 'configuration.read'
    CONFIGURATION_MANAGE = 'configuration.manage'
    CONFIGURATION_PUBLISH = 'configuration.publish'
    CONFIGURATION_DEFINITIONS_READ = 'configuration.definitions.read'
    CONFIGURATION_DEFINITIONS_MANAGE = 'configuration.definitions.manage'

    # Phase 5 Pricing Permissions
    PRICING_READ = 'pricing.read'
    PRICING_MANAGE = 'pricing.manage'

    # Phase 7 Order Permissions
    ORDER_READ = 'order.read'
    ORDER_MANAGE = 'order.manage'
    ORDER_CONFIRM = 'order.confirm'
    ORDER_PROCESS = 'order.process'
    ORDER_CANCEL = 'order.cancel'

    # Phase 7 Commercial, Billing, Payment & Settlement Permissions
    COMMERCIAL_READ = 'commercial.read'
    COMMERCIAL_MANAGE = 'commercial.manage'
    PAYMENT_READ = 'payment.read'
    PAYMENT_PROCESS = 'payment.process'
    BILLING_READ = 'billing.read'
    BILLING_MANAGE = 'billing.manage'
    SETTLEMENT_READ = 'settlement.read'
    SETTLEMENT_PROCESS = 'settlement.process'

    # Phase 8 Driver & Duty Logistics Permissions
    DRIVER_VIEW = 'driver.view'
    DRIVER_MANAGE = 'driver.manage'
    DUTY_VIEW = 'duty.view'
    DUTY_MANAGE = 'duty.manage'
    DUTY_REASSIGN = 'duty.reassign'
    OPERATIONS_ALERT_VIEW = 'operations_alert.view'


PLATFORM_ROLES = {
    RoleName.PLATFORM_ADMIN.value,
    RoleName.PLATFORM_SUPPORT.value,
}

TENANT_ROLES = {
    RoleName.TENANT_OWNER.value,
    RoleName.TENANT_ADMIN.value,
    RoleName.TENANT_MEMBER.value,
    RoleName.TENANT_VIEWER.value,
    RoleName.SELLER_OWNER.value,
    RoleName.SELLER_ADMIN.value,
    RoleName.STAFF.value,
    RoleName.VIEWER.value,
    RoleName.DRIVER.value,
}

# Role to Permissions matrix following least privilege
DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    RoleName.PLATFORM_ADMIN.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.TENANT_MANAGE.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.ROLE_READ.value,
        PermissionName.ROLE_MANAGE.value,
        PermissionName.USER_READ.value,
        PermissionName.USER_MANAGE.value,
        PermissionName.AUDIT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_MANAGE.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_BRANCHES_MANAGE.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_STAFF_MANAGE.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.SELLER_SETTINGS_MANAGE.value,

        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,

        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CONFIGURATION_MANAGE.value,
        PermissionName.CONFIGURATION_PUBLISH.value,
        PermissionName.CONFIGURATION_DEFINITIONS_READ.value,
        PermissionName.CONFIGURATION_DEFINITIONS_MANAGE.value,
        PermissionName.PRICING_READ.value,
        PermissionName.PRICING_MANAGE.value,
        PermissionName.ORDER_READ.value,
        PermissionName.ORDER_MANAGE.value,
        PermissionName.ORDER_CONFIRM.value,
        PermissionName.ORDER_PROCESS.value,
        PermissionName.ORDER_CANCEL.value,
        PermissionName.COMMERCIAL_READ.value,
        PermissionName.COMMERCIAL_MANAGE.value,
        PermissionName.PAYMENT_READ.value,
        PermissionName.PAYMENT_PROCESS.value,
        PermissionName.BILLING_READ.value,
        PermissionName.BILLING_MANAGE.value,
        PermissionName.SETTLEMENT_READ.value,
        PermissionName.SETTLEMENT_PROCESS.value,
        PermissionName.DRIVER_VIEW.value,
        PermissionName.DRIVER_MANAGE.value,
        PermissionName.DUTY_VIEW.value,
        PermissionName.DUTY_MANAGE.value,
        PermissionName.DUTY_REASSIGN.value,
        PermissionName.OPERATIONS_ALERT_VIEW.value,
    ],
    RoleName.PLATFORM_SUPPORT.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.ROLE_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.PRICING_READ.value,
        PermissionName.COMMERCIAL_READ.value,
        PermissionName.PAYMENT_READ.value,
        PermissionName.BILLING_READ.value,
        PermissionName.SETTLEMENT_READ.value,
    ],
    RoleName.TENANT_OWNER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.TENANT_MANAGE.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.ROLE_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_MANAGE.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_BRANCHES_MANAGE.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_STAFF_MANAGE.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.SELLER_SETTINGS_MANAGE.value,

        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,

        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CONFIGURATION_MANAGE.value,
        PermissionName.CONFIGURATION_PUBLISH.value,

        PermissionName.PRICING_READ.value,
        PermissionName.PRICING_MANAGE.value,
        PermissionName.ORDER_READ.value,
        PermissionName.ORDER_MANAGE.value,
        PermissionName.ORDER_CONFIRM.value,
        PermissionName.ORDER_PROCESS.value,
        PermissionName.ORDER_CANCEL.value,
        PermissionName.COMMERCIAL_READ.value,
        PermissionName.COMMERCIAL_MANAGE.value,
        PermissionName.PAYMENT_READ.value,
        PermissionName.PAYMENT_PROCESS.value,
        PermissionName.BILLING_READ.value,
        PermissionName.SETTLEMENT_READ.value,
        PermissionName.DRIVER_VIEW.value,
        PermissionName.DRIVER_MANAGE.value,
        PermissionName.DUTY_VIEW.value,
        PermissionName.DUTY_MANAGE.value,
        PermissionName.DUTY_REASSIGN.value,
        PermissionName.OPERATIONS_ALERT_VIEW.value,
    ],
    RoleName.TENANT_ADMIN.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.TENANT_MANAGE.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.ROLE_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_MANAGE.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_BRANCHES_MANAGE.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_STAFF_MANAGE.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.SELLER_SETTINGS_MANAGE.value,

        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,

        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CONFIGURATION_MANAGE.value,
        PermissionName.CONFIGURATION_PUBLISH.value,

        PermissionName.PRICING_READ.value,
        PermissionName.PRICING_MANAGE.value,
        PermissionName.ORDER_READ.value,
        PermissionName.ORDER_MANAGE.value,
        PermissionName.ORDER_CONFIRM.value,
        PermissionName.ORDER_PROCESS.value,
        PermissionName.ORDER_CANCEL.value,
        PermissionName.COMMERCIAL_READ.value,
        PermissionName.COMMERCIAL_MANAGE.value,
        PermissionName.PAYMENT_READ.value,
        PermissionName.PAYMENT_PROCESS.value,
        PermissionName.BILLING_READ.value,
        PermissionName.SETTLEMENT_READ.value,
        PermissionName.DRIVER_VIEW.value,
        PermissionName.DRIVER_MANAGE.value,
        PermissionName.DUTY_VIEW.value,
        PermissionName.DUTY_MANAGE.value,
        PermissionName.DUTY_REASSIGN.value,
        PermissionName.OPERATIONS_ALERT_VIEW.value,
    ],
    RoleName.TENANT_MEMBER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.USER_READ.value,
    ],
    RoleName.TENANT_VIEWER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.PRICING_READ.value,
        PermissionName.COMMERCIAL_READ.value,
        PermissionName.PAYMENT_READ.value,
        PermissionName.BILLING_READ.value,
    ],
    RoleName.SELLER_OWNER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.TENANT_MANAGE.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.ROLE_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_MANAGE.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_BRANCHES_MANAGE.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_STAFF_MANAGE.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.SELLER_SETTINGS_MANAGE.value,

        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,

        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CONFIGURATION_MANAGE.value,
        PermissionName.CONFIGURATION_PUBLISH.value,

        PermissionName.PRICING_READ.value,
        PermissionName.PRICING_MANAGE.value,
        PermissionName.ORDER_READ.value,
        PermissionName.ORDER_MANAGE.value,
        PermissionName.ORDER_CONFIRM.value,
        PermissionName.ORDER_PROCESS.value,
        PermissionName.ORDER_CANCEL.value,
        PermissionName.COMMERCIAL_READ.value,
        PermissionName.COMMERCIAL_MANAGE.value,
        PermissionName.PAYMENT_READ.value,
        PermissionName.PAYMENT_PROCESS.value,
        PermissionName.BILLING_READ.value,
        PermissionName.SETTLEMENT_READ.value,
        PermissionName.DRIVER_VIEW.value,
        PermissionName.DRIVER_MANAGE.value,
        PermissionName.DUTY_VIEW.value,
        PermissionName.DUTY_MANAGE.value,
        PermissionName.DUTY_REASSIGN.value,
        PermissionName.OPERATIONS_ALERT_VIEW.value,
    ],
    RoleName.SELLER_ADMIN.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_MANAGE.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_BRANCHES_MANAGE.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_STAFF_MANAGE.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.SELLER_SETTINGS_MANAGE.value,

        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,

        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CONFIGURATION_MANAGE.value,
        PermissionName.CONFIGURATION_PUBLISH.value,

        PermissionName.PRICING_READ.value,
        PermissionName.PRICING_MANAGE.value,
        PermissionName.ORDER_READ.value,
        PermissionName.ORDER_MANAGE.value,
        PermissionName.ORDER_CONFIRM.value,
        PermissionName.ORDER_PROCESS.value,
        PermissionName.ORDER_CANCEL.value,
        PermissionName.COMMERCIAL_READ.value,
        PermissionName.COMMERCIAL_MANAGE.value,
        PermissionName.PAYMENT_READ.value,
        PermissionName.PAYMENT_PROCESS.value,
        PermissionName.BILLING_READ.value,
        PermissionName.SETTLEMENT_READ.value,
        PermissionName.DRIVER_VIEW.value,
        PermissionName.DRIVER_MANAGE.value,
        PermissionName.DUTY_VIEW.value,
        PermissionName.DUTY_MANAGE.value,
        PermissionName.DUTY_REASSIGN.value,
        PermissionName.OPERATIONS_ALERT_VIEW.value,
    ],
    RoleName.STAFF.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.PRICING_READ.value,
        PermissionName.ORDER_READ.value,
        PermissionName.ORDER_PROCESS.value,
        PermissionName.COMMERCIAL_READ.value,
        PermissionName.PAYMENT_READ.value,
        PermissionName.DRIVER_VIEW.value,
        PermissionName.DUTY_VIEW.value,
        PermissionName.DUTY_MANAGE.value,
        PermissionName.DUTY_REASSIGN.value,
        PermissionName.OPERATIONS_ALERT_VIEW.value,
    ],
    RoleName.VIEWER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.PRICING_READ.value,
        PermissionName.ORDER_READ.value,
        PermissionName.COMMERCIAL_READ.value,
        PermissionName.PAYMENT_READ.value,
        PermissionName.BILLING_READ.value,
        PermissionName.DRIVER_VIEW.value,
        PermissionName.DUTY_VIEW.value,
        PermissionName.OPERATIONS_ALERT_VIEW.value,
    ],
    RoleName.DRIVER.value: [
        PermissionName.DRIVER_VIEW.value,
        PermissionName.DUTY_VIEW.value,
        PermissionName.DUTY_MANAGE.value,
    ],
    RoleName.CUSTOMER.value: [
        PermissionName.ORDER_READ.value,
        PermissionName.ORDER_CANCEL.value,
        PermissionName.PAYMENT_READ.value,
        PermissionName.PAYMENT_PROCESS.value,
    ],
}
