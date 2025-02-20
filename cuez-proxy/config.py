from pydantic import Field
import json
from typing import Tuple, Any, Dict, Type
from pathlib import Path

from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

local_settings_file = 'config-local-settings.json'

class JsonAppSettingsSource(PydanticBaseSettingsSource):
  """
    A simple settings source class that loads variables from a JSON file
    at the project's root.

    Here we happen to choose to use the `env_file_encoding` from Config
    when reading `config.json`
    """

  def get_field_value(
      self, field: FieldInfo, field_name: str
  ) -> Tuple[Any, str, bool]:
    encoding = self.config.get('env_file_encoding')
    file_content_json = json.loads(
        Path(self.config.get('config_file')).read_text(encoding)
    )
    field_value = file_content_json.get(field_name)
    return field_value, field_name, False

  def prepare_field_value(
      self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
  ) -> Any:
    return value

  def __call__(self) -> Dict[str, Any]:
    d: Dict[str, Any] = {}

    for field_name, field in self.settings_cls.model_fields.items():
      field_value, field_key, value_is_complex = self.get_field_value(
          field, field_name
      )
      field_value = self.prepare_field_value(
          field_name, field, field_value, value_is_complex
      )
      if field_value is not None:
        d[field_key] = field_value

    return d

class LocalSettings(BaseSettings):
  # If you create ENV VARS with the same name in UPPER CASE, those will get replaced .
  # But use APP_ prefix.
  # Example : APP_PROJECT_ID

  model_config = SettingsConfigDict(env_prefix="APP_", env_file_encoding='utf-8', config_file=local_settings_file)

  PROJECT_ID: str | None = Field(None, description="Project Id")
  REGION: str | None = Field(None, description="Region")
  GEMINI_PROJECT_ID: str | None = Field(None, description="Gemini Project Id")
  GEMINI_REGION: str | None = Field(None, description="Gemini Region")
  CUEZ_API_HOST: str | None = Field(None, description="Cuez API host")
  CUEZ_API_PORT: str | None = Field(None, description="Cuez API port")
  CUEZ_USERNAME: str | None = Field(None, description="Cuez User Name")
  CUEZ_PASSWORD: str | None = Field(None, description="Cuez Password")

  @classmethod
  def settings_customise_sources(
      cls,
      settings_cls: Type[BaseSettings],
      init_settings: PydanticBaseSettingsSource,
      env_settings: PydanticBaseSettingsSource,
      dotenv_settings: PydanticBaseSettingsSource,
      file_secret_settings: PydanticBaseSettingsSource,
  ) -> Tuple[PydanticBaseSettingsSource, ...]:
    return (
        init_settings,
        env_settings,
        JsonAppSettingsSource(settings_cls),
        file_secret_settings,
    )
