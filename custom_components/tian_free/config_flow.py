"""Config flow for Tian API integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from .const import DOMAIN, NAME, CONF_API_KEY, CONF_SCROLL_INTERVAL

class TianConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tian API."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            scroll_interval = user_input[CONF_SCROLL_INTERVAL]
            
            # 验证API密钥长度
            if len(api_key) == 32:
                return self.async_create_entry(
                    title=NAME,
                    data={
                        CONF_API_KEY: api_key,
                        CONF_SCROLL_INTERVAL: scroll_interval
                    }
                )
            else:
                errors["base"] = "invalid_api_key_format"

        data_schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_SCROLL_INTERVAL, default=5): vol.All(
                vol.Coerce(int), 
                vol.Range(min=1, max=60)
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "name": NAME
            }
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return TianOptionsFlow(config_entry)

class TianOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Tian API."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_SCROLL_INTERVAL,
                    default=self.config_entry.options.get(CONF_SCROLL_INTERVAL, 5)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            })
        )