import uuid
from typing import Any, Sequence
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from app.models.configuration import Application, ApplicationModule, ConfigurationDefinition, ConfigurationValue

class ConfigurationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_applications(self) -> Sequence[Application]:
        return self.db.scalars(select(Application)).all()

    def get_application_by_key(self, key: str) -> Application | None:
        return self.db.scalar(select(Application).where(Application.key == key))

    def create_application(self, obj_in: dict[str, Any]) -> Application:
        app = Application(**obj_in)
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        return app

    def get_definitions(self) -> Sequence[ConfigurationDefinition]:
        return self.db.scalars(select(ConfigurationDefinition)).all()

    def get_definition(self, definition_id: uuid.UUID) -> ConfigurationDefinition | None:
        return self.db.get(ConfigurationDefinition, definition_id)

    def get_definition_by_key(self, key: str) -> ConfigurationDefinition | None:
        return self.db.scalar(select(ConfigurationDefinition).where(ConfigurationDefinition.key == key))

    def create_definition(self, obj_in: dict[str, Any]) -> ConfigurationDefinition:
        definition = ConfigurationDefinition(**obj_in)
        self.db.add(definition)
        self.db.commit()
        self.db.refresh(definition)
        return definition

    def update_definition(self, db_obj: ConfigurationDefinition, obj_in: dict[str, Any]) -> ConfigurationDefinition:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get_values_for_tenant(
        self, tenant_id: uuid.UUID, application_id: uuid.UUID | None = None
    ) -> Sequence[ConfigurationValue]:
        stmt = select(ConfigurationValue).where(
            ConfigurationValue.tenant_id == tenant_id,
            ConfigurationValue.status == 'PUBLISHED'
        )
        if application_id:
            stmt = stmt.where(
                or_(
                    ConfigurationValue.application_id.is_(None),
                    ConfigurationValue.application_id == application_id
                )
            )
        else:
            stmt = stmt.where(ConfigurationValue.application_id.is_(None))
        return self.db.scalars(stmt).all()

    def get_value(self, tenant_id: uuid.UUID, definition_id: uuid.UUID, application_id: uuid.UUID | None = None) -> ConfigurationValue | None:
        stmt = select(ConfigurationValue).where(
            ConfigurationValue.tenant_id == tenant_id,
            ConfigurationValue.definition_id == definition_id,
            ConfigurationValue.status == 'PUBLISHED'
        )
        if application_id:
            stmt = stmt.where(ConfigurationValue.application_id == application_id)
        else:
            stmt = stmt.where(ConfigurationValue.application_id.is_(None))
        return self.db.scalar(stmt)

    def set_value(
        self,
        tenant_id: uuid.UUID,
        definition_id: uuid.UUID,
        value: Any,
        user_id: uuid.UUID | None = None,
        application_id: uuid.UUID | None = None,
    ) -> ConfigurationValue:
        existing = self.get_value(tenant_id, definition_id, application_id)
        if existing:
            existing.value = value
            existing.version += 1
            existing.updated_by = user_id
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            new_value = ConfigurationValue(
                tenant_id=tenant_id,
                definition_id=definition_id,
                application_id=application_id,
                value=value,
                created_by=user_id,
                updated_by=user_id,
                status='PUBLISHED',
                version=1
            )
            self.db.add(new_value)
            self.db.commit()
            self.db.refresh(new_value)
            return new_value
