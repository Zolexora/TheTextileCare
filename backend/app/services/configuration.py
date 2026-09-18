import uuid
from typing import Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.configuration import ConfigurationRepository
from app.schemas.configuration import ResolvedConfigurationResponse

class ConfigurationResolverService:
    def __init__(self, db: Session):
        self.repo = ConfigurationRepository(db)

    def resolve_context(self, tenant_id: uuid.UUID, application_key: str | None = None, is_public: bool = False) -> list[ResolvedConfigurationResponse]:
        definitions = self.repo.get_definitions()
        
        app_id = None
        if application_key:
            app = self.repo.get_application_by_key(application_key)
            if app:
                app_id = app.id
        
        # Load all tenant level and tenant-application level values
        all_values = self.repo.get_values_for_tenant(tenant_id, application_id=app_id)
        
        val_map = {}
        for v in all_values:
            # We store (definition_id, application_id) mapping
            val_map[(v.definition_id, v.application_id)] = v

        resolved = []
        for defn in definitions:
            if is_public and not defn.is_public:
                continue
            if defn.is_sensitive and is_public: # Double safeguard
                continue

            # Determine value by precedence
            final_value = defn.default_value
            
            # Tenant level override
            tenant_val = val_map.get((defn.id, None))
            if tenant_val:
                final_value = tenant_val.value
                
            # Tenant + Application level override
            if app_id:
                tenant_app_val = val_map.get((defn.id, app_id))
                if tenant_app_val:
                    final_value = tenant_app_val.value
                    
            resolved.append(ResolvedConfigurationResponse(
                key=defn.key,
                value=final_value,
                is_public=defn.is_public,
                domain=defn.domain
            ))
            
        return resolved

    def get_tenant_configuration(self, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
        # Returns raw stored values for the tenant (for management UI)
        values = self.repo.get_values_for_tenant(tenant_id)
        return [{"key": v.definition.key, "value": v.value, "application_id": v.application_id, "status": v.status} for v in values]
