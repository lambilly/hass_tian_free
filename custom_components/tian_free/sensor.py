"""Sensor platform for Tian API integration."""
import logging
import asyncio
import aiohttp
import async_timeout
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    DEVICE_NAME,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    JOKE_API_URL,
    MORNING_API_URL,
    EVENING_API_URL,
    POETRY_API_URL,
    SONG_CI_API_URL,
    YUAN_QU_API_URL,
    HISTORY_API_URL,
    SENTENCE_API_URL,
    COUPLET_API_URL,
    MAXIM_API_URL,
    CONF_API_KEY,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=24)  # 每天更新一次

# 全局缓存，避免重复调用API
_data_cache = {}
_cache_timestamp = {}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    api_key = config_entry.data[CONF_API_KEY]
    
    # 创建设备信息
    device_info = DeviceInfo(
        identifiers={(DOMAIN, "tian_info_query")},
        name=DEVICE_NAME,
        manufacturer=DEVICE_MANUFACTURER,
        model=DEVICE_MODEL,
        configuration_url="https://www.tianapi.com/",
    )
    
    # 创建多个传感器实体，每个API对应一个实体
    sensors = [
        TianJokeSensor(api_key, device_info, config_entry.entry_id),
        TianMorningSensor(api_key, device_info, config_entry.entry_id),
        TianEveningSensor(api_key, device_info, config_entry.entry_id),
        TianPoetrySensor(api_key, device_info, config_entry.entry_id),
        TianSongCiSensor(api_key, device_info, config_entry.entry_id),
        TianYuanQuSensor(api_key, device_info, config_entry.entry_id),
        TianHistorySensor(api_key, device_info, config_entry.entry_id),
        TianSentenceSensor(api_key, device_info, config_entry.entry_id),
        TianCoupletSensor(api_key, device_info, config_entry.entry_id),
        TianMaximSensor(api_key, device_info, config_entry.entry_id),
        TianScrollingContentSensor(api_key, device_info, config_entry.entry_id),
    ]
    
    # 设置 update_before_add=True 确保首次添加时立即更新数据
    async_add_entities(sensors, update_before_add=True)
    
    # 记录集成加载成功
    _LOGGER.info("天聚数行免费版集成 v1.0.0 加载成功，实体已创建并开始首次更新")

class TianJokeSensor(SensorEntity):
    """天聚数行笑话传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "每日笑话"
        self._attr_unique_id = f"{entry_id}_joke"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:emoticon-lol"
        self._state = "等待更新"
        self._attributes = {}
        self._available = True

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取笑话数据
            joke_data = await self._fetch_cached_data("joke", self._fetch_joke_data)
            
            if joke_data:
                joke_list = joke_data.get("result", {}).get("list", [])
                
                if joke_list:
                    joke_result = joke_list[0]
                else:
                    joke_result = {}
                
                # 设置状态为更新时间
                current_time = self._get_current_time()
                self._state = current_time
                self._available = True
                
                # 设置属性
                self._attributes = {
                    "title": "每日笑话",
                    "code": joke_data.get("code", 0),
                    "name": joke_result.get("title", ""),  # 新增name属性
                    "content": joke_result.get("content", ""),
                    "update_time": current_time
                }
                
                _LOGGER.info("天聚数行笑话更新成功")
                
            else:
                self._available = False
                self._state = "API请求失败"
                _LOGGER.error("无法获取天聚数行笑话，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行笑话传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_joke_data(self):
        """获取笑话数据."""
        url = f"{JOKE_API_URL}?key={self._api_key}&num=1"
        return await self._fetch_api_data(url)

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        # 检查缓存是否有效（1小时内）
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < 3600):  # 1小时缓存
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:  # 确保数据有效
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            _LOGGER.info("已更新缓存数据: %s", cache_key)
        return data

    async def _fetch_api_data(self, url: str):
        """获取API数据."""
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(15):
                response = await session.get(url)
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("API响应: %s", data)
                    
                    # 检查API返回的错误码
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:  # 频率限制
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:  # 常见错误码
                        _LOGGER.error("API密钥错误: %s", data.get("msg", "未知错误"))
                    else:
                        _LOGGER.error("API返回错误[%s]: %s", data.get("code"), data.get("msg", "未知错误"))
                else:
                    _LOGGER.error("HTTP请求失败: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API请求超时")
        except Exception as e:
            _LOGGER.error("获取API数据时出错: %s", e)
        
        return None

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        from datetime import datetime
        return int(datetime.now().timestamp())

class TianMorningSensor(SensorEntity):
    """天聚数行早安传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "早安心语"
        self._attr_unique_id = f"{entry_id}_morning"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:weather-sunny"
        self._state = "等待更新"
        self._attributes = {}
        self._available = True

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取早安数据
            morning_data = await self._fetch_cached_data("morning", self._fetch_morning_data)
            
            if morning_data:
                morning_content = morning_data.get("result", {}).get("content", "")
                
                # 优化早安内容处理逻辑
                if not morning_content or morning_content == "":
                    morning_content = "早安！新的一天开始了！"
                elif "早安" not in morning_content:
                    morning_content = f"早安！{morning_content}"
                
                # 设置状态为更新时间
                current_time = self._get_current_time()
                self._state = current_time
                self._available = True
                
                # 设置属性
                self._attributes = {
                    "title": "早安心语",
                    "code": morning_data.get("code", 0),
                    "content": morning_content,
                    "update_time": current_time
                }
                
                _LOGGER.info("天聚数行早安更新成功")
                
            else:
                self._available = False
                self._state = "API请求失败"
                _LOGGER.error("无法获取天聚数行早安，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行早安传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_morning_data(self):
        """获取早安数据."""
        url = f"{MORNING_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        # 检查缓存是否有效（1小时内）
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < 3600):  # 1小时缓存
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:  # 确保数据有效
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            _LOGGER.info("已更新缓存数据: %s", cache_key)
        return data

    async def _fetch_api_data(self, url: str):
        """获取API数据."""
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(15):
                response = await session.get(url)
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("API响应: %s", data)
                    
                    # 检查API返回的错误码
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:  # 频率限制
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:  # 常见错误码
                        _LOGGER.error("API密钥错误: %s", data.get("msg", "未知错误"))
                    else:
                        _LOGGER.error("API返回错误[%s]: %s", data.get("code"), data.get("msg", "未知错误"))
                else:
                    _LOGGER.error("HTTP请求失败: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API请求超时")
        except Exception as e:
            _LOGGER.error("获取API数据时出错: %s", e)
        
        return None

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        from datetime import datetime
        return int(datetime.now().timestamp())

class TianEveningSensor(SensorEntity):
    """天聚数行晚安传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "晚安心语"
        self._attr_unique_id = f"{entry_id}_evening"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:weather-night"
        self._state = "等待更新"
        self._attributes = {}
        self._available = True

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取晚安数据
            evening_data = await self._fetch_cached_data("evening", self._fetch_evening_data)
            
            if evening_data:
                evening_content = evening_data.get("result", {}).get("content", "")
                
                # 优化晚安内容处理逻辑
                if not evening_content or evening_content == "":
                    evening_content = "晚安！好梦！"
                elif "晚安" not in evening_content:
                    evening_content = f"{evening_content}晚安！"
                
                # 设置状态为更新时间
                current_time = self._get_current_time()
                self._state = current_time
                self._available = True
                
                # 设置属性
                self._attributes = {
                    "title": "晚安心语",
                    "code": evening_data.get("code", 0),
                    "content": evening_content,
                    "update_time": current_time
                }
                
                _LOGGER.info("天聚数行晚安更新成功")
                
            else:
                self._available = False
                self._state = "API请求失败"
                _LOGGER.error("无法获取天聚数行晚安，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行晚安传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_evening_data(self):
        """获取晚安数据."""
        url = f"{EVENING_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        # 检查缓存是否有效（1小时内）
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < 3600):  # 1小时缓存
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:  # 确保数据有效
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            _LOGGER.info("已更新缓存数据: %s", cache_key)
        return data

    async def _fetch_api_data(self, url: str):
        """获取API数据."""
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(15):
                response = await session.get(url)
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("API响应: %s", data)
                    
                    # 检查API返回的错误码
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:  # 频率限制
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:  # 常见错误码
                        _LOGGER.error("API密钥错误: %s", data.get("msg", "未知错误"))
                    else:
                        _LOGGER.error("API返回错误[%s]: %s", data.get("code"), data.get("msg", "未知错误"))
                else:
                    _LOGGER.error("HTTP请求失败: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API请求超时")
        except Exception as e:
            _LOGGER.error("获取API数据时出错: %s", e)
        
        return None

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        from datetime import datetime
        return int(datetime.now().timestamp())

class TianPoetrySensor(SensorEntity):
    """天聚数行唐诗传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "唐诗鉴赏"
        self._attr_unique_id = f"{entry_id}_poetry"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:book-open-variant"
        self._state = "等待更新"
        self._attributes = {}
        self._available = True

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取唐诗数据
            poetry_data = await self._fetch_cached_data("poetry", self._fetch_poetry_data)
            
            if poetry_data:
                poetry_list = poetry_data.get("result", {}).get("list", [])
                poetry_first = poetry_list[0] if poetry_list else {}
                
                # 设置状态为更新时间
                current_time = self._get_current_time()
                self._state = current_time
                self._available = True
                
                # 设置属性
                self._attributes = {
                    "title": "唐诗鉴赏",
                    "code": poetry_data.get("code", 0),
                    "content": poetry_first.get("content", ""),
                    "source": poetry_first.get("title", ""),  # 新增source属性
                    "author": poetry_first.get("author", ""),
                    "intro": poetry_first.get("intro", ""),
                    "kind": poetry_first.get("kind", ""),
                    "update_time": current_time
                }
                
                _LOGGER.info("天聚数行唐诗更新成功")
                
            else:
                self._available = False
                self._state = "API请求失败"
                _LOGGER.error("无法获取天聚数行唐诗，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行唐诗传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_poetry_data(self):
        """获取唐诗数据."""
        url = f"{POETRY_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        # 检查缓存是否有效（1小时内）
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < 3600):  # 1小时缓存
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:  # 确保数据有效
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            _LOGGER.info("已更新缓存数据: %s", cache_key)
        return data

    async def _fetch_api_data(self, url: str):
        """获取API数据."""
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(15):
                response = await session.get(url)
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("API响应: %s", data)
                    
                    # 检查API返回的错误码
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:  # 频率限制
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:  # 常见错误码
                        _LOGGER.error("API密钥错误: %s", data.get("msg", "未知错误"))
                    else:
                        _LOGGER.error("API返回错误[%s]: %s", data.get("code"), data.get("msg", "未知错误"))
                else:
                    _LOGGER.error("HTTP请求失败: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API请求超时")
        except Exception as e:
            _LOGGER.error("获取API数据时出错: %s", e)
        
        return None

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        from datetime import datetime
        return int(datetime.now().timestamp())

class TianSongCiSensor(SensorEntity):
    """天聚数行宋词传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "最美宋词"
        self._attr_unique_id = f"{entry_id}_songci"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:book-music"
        self._state = "等待更新"
        self._attributes = {}
        self._available = True

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取宋词数据
            song_ci_data = await self._fetch_cached_data("songci", self._fetch_song_ci_data)
            
            if song_ci_data:
                song_ci_result = song_ci_data.get("result", {})
                
                # 设置状态为更新时间
                current_time = self._get_current_time()
                self._state = current_time
                self._available = True
                
                # 设置属性
                self._attributes = {
                    "title": "最美宋词",
                    "code": song_ci_data.get("code", 0),
                    "content": song_ci_result.get("content", ""),
                    "source": song_ci_result.get("source", ""),  # 新增source属性
                    "author": song_ci_result.get("author", ""),
                    "update_time": current_time
                }
                
                _LOGGER.info("天聚数行宋词更新成功")
                
            else:
                self._available = False
                self._state = "API请求失败"
                _LOGGER.error("无法获取天聚数行宋词，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行宋词传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_song_ci_data(self):
        """获取宋词数据."""
        url = f"{SONG_CI_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        # 检查缓存是否有效（1小时内）
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < 3600):  # 1小时缓存
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:  # 确保数据有效
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            _LOGGER.info("已更新缓存数据: %s", cache_key)
        return data

    async def _fetch_api_data(self, url: str):
        """获取API数据."""
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(15):
                response = await session.get(url)
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("API响应: %s", data)
                    
                    # 检查API返回的错误码
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:  # 频率限制
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:  # 常见错误码
                        _LOGGER.error("API密钥错误: %s", data.get("msg", "未知错误"))
                    else:
                        _LOGGER.error("API返回错误[%s]: %s", data.get("code"), data.get("msg", "未知错误"))
                else:
                    _LOGGER.error("HTTP请求失败: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API请求超时")
        except Exception as e:
            _LOGGER.error("获取API数据时出错: %s", e)
        
        return None

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        from datetime import datetime
        return int(datetime.now().timestamp())

class TianYuanQuSensor(SensorEntity):
    """天聚数行元曲传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "精选元曲"
        self._attr_unique_id = f"{entry_id}_yuanqu"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:music"
        self._state = "等待更新"
        self._attributes = {}
        self._available = True

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取元曲数据
            yuan_qu_data = await self._fetch_cached_data("yuanqu", self._fetch_yuan_qu_data)
            
            if yuan_qu_data:
                yuan_qu_list = yuan_qu_data.get("result", {}).get("list", [])
                yuan_qu_first = yuan_qu_list[0] if yuan_qu_list else {}
                
                # 设置状态为更新时间
                current_time = self._get_current_time()
                self._state = current_time
                self._available = True
                
                # 设置属性
                self._attributes = {
                    "title": "精选元曲",
                    "code": yuan_qu_data.get("code", 0),
                    "content": yuan_qu_first.get("content", ""),
                    "source": yuan_qu_first.get("title", ""),  # 新增source属性
                    "author": yuan_qu_first.get("author", ""),
                    "note": yuan_qu_first.get("note", ""),
                    "translation": yuan_qu_first.get("translation", ""),
                    "update_time": current_time
                }
                
                _LOGGER.info("天聚数行元曲更新成功")
                
            else:
                self._available = False
                self._state = "API请求失败"
                _LOGGER.error("无法获取天聚数行元曲，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行元曲传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_yuan_qu_data(self):
        """获取元曲数据."""
        url = f"{YUAN_QU_API_URL}?key={self._api_key}&num=1&page=1"
        return await self._fetch_api_data(url)

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        # 检查缓存是否有效（1小时内）
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < 3600):  # 1小时缓存
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:  # 确保数据有效
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            _LOGGER.info("已更新缓存数据: %s", cache_key)
        return data

    async def _fetch_api_data(self, url: str):
        """获取API数据."""
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(15):
                response = await session.get(url)
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("API响应: %s", data)
                    
                    # 检查API返回的错误码
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:  # 频率限制
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:  # 常见错误码
                        _LOGGER.error("API密钥错误: %s", data.get("msg", "未知错误"))
                    else:
                        _LOGGER.error("API返回错误[%s]: %s", data.get("code"), data.get("msg", "未知错误"))
                else:
                    _LOGGER.error("HTTP请求失败: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API请求超时")
        except Exception as e:
            _LOGGER.error("获取API数据时出错: %s", e)
        
        return None

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        from datetime import datetime
        return int(datetime.now().timestamp())

class TianHistorySensor(SensorEntity):
    """天聚数行历史传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "简说历史"
        self._attr_unique_id = f"{entry_id}_history"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:calendar-clock"
        self._state = "等待更新"
        self._attributes = {}
        self._available = True

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取历史数据
            history_data = await self._fetch_cached_data("history", self._fetch_history_data)
            
            if history_data:
                history_result = self._extract_result(history_data)
                
                # 设置状态为更新时间
                current_time = self._get_current_time()
                self._state = current_time
                self._available = True
                
                # 设置属性
                self._attributes = {
                    "title": "简说历史",
                    "code": history_data.get("code", 0),
                    "content": history_result.get("content", "暂无历史内容"),
                    "update_time": current_time
                }
                
                _LOGGER.info("天聚数行历史更新成功")
                
            else:
                self._available = False
                self._state = "API请求失败"
                _LOGGER.error("无法获取天聚数行历史，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行历史传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_history_data(self):
        """获取历史数据."""
        url = f"{HISTORY_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

    def _extract_result(self, data):
        """从API响应数据中提取result字段，处理可能的列表结构."""
        if not data:
            _LOGGER.warning("传入的数据为空")
            return {}
            
        result = data.get("result", {})
        
        # 如果result是列表
        if isinstance(result, list):
            if result:
                _LOGGER.debug("检测到列表结构的result，使用第一个元素")
                return result[0]
            else:
                _LOGGER.warning("result列表为空，返回默认值")
                return {}
        
        # 如果result是字典，直接返回
        elif isinstance(result, dict):
            return result
        
        # 其他情况返回空字典
        else:
            _LOGGER.warning("未知的result类型: %s，返回默认值", type(result))
            return {}

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        # 检查缓存是否有效（1小时内）
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < 3600):  # 1小时缓存
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:  # 确保数据有效
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            _LOGGER.info("已更新缓存数据: %s", cache_key)
        return data

    async def _fetch_api_data(self, url: str):
        """获取API数据."""
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(15):
                response = await session.get(url)
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("API响应: %s", data)
                    
                    # 检查API返回的错误码
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:  # 频率限制
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:  # 常见错误码
                        _LOGGER.error("API密钥错误: %s", data.get("msg", "未知错误"))
                    else:
                        _LOGGER.error("API返回错误[%s]: %s", data.get("code"), data.get("msg", "未知错误"))
                else:
                    _LOGGER.error("HTTP请求失败: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API请求超时")
        except Exception as e:
            _LOGGER.error("获取API数据时出错: %s", e)
        
        return None

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        from datetime import datetime
        return int(datetime.now().timestamp())

class TianSentenceSensor(SensorEntity):
    """天聚数行名句传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "古籍名句"
        self._attr_unique_id = f"{entry_id}_sentence"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:format-quote-close"
        self._state = "等待更新"
        self._attributes = {}
        self._available = True

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取名句数据
            sentence_data = await self._fetch_cached_data("sentence", self._fetch_sentence_data)
            
            if sentence_data:
                sentence_result = self._extract_result(sentence_data)
                
                # 设置状态为更新时间
                current_time = self._get_current_time()
                self._state = current_time
                self._available = True
                
                # 设置属性
                self._attributes = {
                    "title": "古籍名句",
                    "code": sentence_data.get("code", 0),
                    "content": sentence_result.get("content", "暂无名句内容"),
                    "source": sentence_result.get("source", "未知来源"),
                    "update_time": current_time
                }
                
                _LOGGER.info("天聚数行名句更新成功")
                
            else:
                self._available = False
                self._state = "API请求失败"
                _LOGGER.error("无法获取天聚数行名句，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行名句传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_sentence_data(self):
        """获取名句数据."""
        url = f"{SENTENCE_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

    def _extract_result(self, data):
        """从API响应数据中提取result字段，处理可能的列表结构."""
        if not data:
            _LOGGER.warning("传入的数据为空")
            return {}
            
        result = data.get("result", {})
        
        # 如果result是列表
        if isinstance(result, list):
            if result:
                _LOGGER.debug("检测到列表结构的result，使用第一个元素")
                return result[0]
            else:
                _LOGGER.warning("result列表为空，返回默认值")
                return {}
        
        # 如果result是字典，直接返回
        elif isinstance(result, dict):
            return result
        
        # 其他情况返回空字典
        else:
            _LOGGER.warning("未知的result类型: %s，返回默认值", type(result))
            return {}

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        # 检查缓存是否有效（1小时内）
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < 3600):  # 1小时缓存
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:  # 确保数据有效
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            _LOGGER.info("已更新缓存数据: %s", cache_key)
        return data

    async def _fetch_api_data(self, url: str):
        """获取API数据."""
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(15):
                response = await session.get(url)
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("API响应: %s", data)
                    
                    # 检查API返回的错误码
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:  # 频率限制
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:  # 常见错误码
                        _LOGGER.error("API密钥错误: %s", data.get("msg", "未知错误"))
                    else:
                        _LOGGER.error("API返回错误[%s]: %s", data.get("code"), data.get("msg", "未知错误"))
                else:
                    _LOGGER.error("HTTP请求失败: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API请求超时")
        except Exception as e:
            _LOGGER.error("获取API数据时出错: %s", e)
        
        return None

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        from datetime import datetime
        return int(datetime.now().timestamp())

class TianCoupletSensor(SensorEntity):
    """天聚数行对联传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "经典对联"
        self._attr_unique_id = f"{entry_id}_couplet"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:brush"
        self._state = "等待更新"
        self._attributes = {}
        self._available = True

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取对联数据
            couplet_data = await self._fetch_cached_data("couplet", self._fetch_couplet_data)
            
            if couplet_data:
                couplet_result = self._extract_result(couplet_data)
                
                # 设置状态为更新时间
                current_time = self._get_current_time()
                self._state = current_time
                self._available = True
                
                # 设置属性
                self._attributes = {
                    "title": "经典对联",
                    "code": couplet_data.get("code", 0),
                    "content": couplet_result.get("content", "暂无对联内容"),
                    "update_time": current_time
                }
                
                _LOGGER.info("天聚数行对联更新成功")
                
            else:
                self._available = False
                self._state = "API请求失败"
                _LOGGER.error("无法获取天聚数行对联，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行对联传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_couplet_data(self):
        """获取对联数据."""
        url = f"{COUPLET_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

    def _extract_result(self, data):
        """从API响应数据中提取result字段，处理可能的列表结构."""
        if not data:
            _LOGGER.warning("传入的数据为空")
            return {}
            
        result = data.get("result", {})
        
        # 如果result是列表
        if isinstance(result, list):
            if result:
                _LOGGER.debug("检测到列表结构的result，使用第一个元素")
                return result[0]
            else:
                _LOGGER.warning("result列表为空，返回默认值")
                return {}
        
        # 如果result是字典，直接返回
        elif isinstance(result, dict):
            return result
        
        # 其他情况返回空字典
        else:
            _LOGGER.warning("未知的result类型: %s，返回默认值", type(result))
            return {}

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        # 检查缓存是否有效（1小时内）
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < 3600):  # 1小时缓存
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:  # 确保数据有效
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            _LOGGER.info("已更新缓存数据: %s", cache_key)
        return data

    async def _fetch_api_data(self, url: str):
        """获取API数据."""
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(15):
                response = await session.get(url)
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("API响应: %s", data)
                    
                    # 检查API返回的错误码
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:  # 频率限制
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:  # 常见错误码
                        _LOGGER.error("API密钥错误: %s", data.get("msg", "未知错误"))
                    else:
                        _LOGGER.error("API返回错误[%s]: %s", data.get("code"), data.get("msg", "未知错误"))
                else:
                    _LOGGER.error("HTTP请求失败: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API请求超时")
        except Exception as e:
            _LOGGER.error("获取API数据时出错: %s", e)
        
        return None

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        from datetime import datetime
        return int(datetime.now().timestamp())

class TianMaximSensor(SensorEntity):
    """天聚数行格言传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "英文格言"
        self._attr_unique_id = f"{entry_id}_maxim"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:translate"
        self._state = "等待更新"
        self._attributes = {}
        self._available = True

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取格言数据
            maxim_data = await self._fetch_cached_data("maxim", self._fetch_maxim_data)
            
            if maxim_data:
                maxim_result = self._extract_result(maxim_data)
                
                # 设置状态为更新时间
                current_time = self._get_current_time()
                self._state = current_time
                self._available = True
                
                # 设置属性
                self._attributes = {
                    "title": "英文格言",
                    "code": maxim_data.get("code", 0),
                    "en": maxim_result.get("en", ""),
                    "zh": maxim_result.get("zh", ""),
                    "update_time": current_time
                }
                
                _LOGGER.info("天聚数行格言更新成功")
                
            else:
                self._available = False
                self._state = "API请求失败"
                _LOGGER.error("无法获取天聚数行格言，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行格言传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_maxim_data(self):
        """获取格言数据."""
        url = f"{MAXIM_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

    def _extract_result(self, data):
        """从API响应数据中提取result字段，处理可能的列表结构."""
        if not data:
            _LOGGER.warning("传入的数据为空")
            return {}
            
        result = data.get("result", {})
        
        # 如果result是列表
        if isinstance(result, list):
            if result:
                _LOGGER.debug("检测到列表结构的result，使用第一个元素")
                return result[0]
            else:
                _LOGGER.warning("result列表为空，返回默认值")
                return {}
        
        # 如果result是字典，直接返回
        elif isinstance(result, dict):
            return result
        
        # 其他情况返回空字典
        else:
            _LOGGER.warning("未知的result类型: %s，返回默认值", type(result))
            return {}

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        # 检查缓存是否有效（1小时内）
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < 3600):  # 1小时缓存
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:  # 确保数据有效
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            _LOGGER.info("已更新缓存数据: %s", cache_key)
        return data

    async def _fetch_api_data(self, url: str):
        """获取API数据."""
        session = async_get_clientsession(self.hass)
        
        try:
            async with async_timeout.timeout(15):
                response = await session.get(url)
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("API响应: %s", data)
                    
                    # 检查API返回的错误码
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:  # 频率限制
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:  # 常见错误码
                        _LOGGER.error("API密钥错误: %s", data.get("msg", "未知错误"))
                    else:
                        _LOGGER.error("API返回错误[%s]: %s", data.get("code"), data.get("msg", "未知错误"))
                else:
                    _LOGGER.error("HTTP请求失败: %s", response.status)
        except asyncio.TimeoutError:
            _LOGGER.error("API请求超时")
        except Exception as e:
            _LOGGER.error("获取API数据时出错: %s", e)
        
        return None

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        from datetime import datetime
        return int(datetime.now().timestamp())
        
class TianScrollingContentSensor(SensorEntity):
    """天聚数行滚动内容传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "滚动内容"
        self._attr_unique_id = f"{entry_id}_scrolling_content"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:message-text"
        self._state = self._get_current_time()  # 初始状态设为当前时间
        self._attributes = {}
        self._available = True
        self._current_time_slot = None
        self._retry_count = 0
        self._max_retries = 3
        self._has_data = False  # 标记是否有数据

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_update(self):
        """Update sensor data - 使用缓存数据，避免频繁调用API."""
        # 首先更新状态为当前时间
        current_time = self._get_current_time()
        self._state = current_time
        
        try:
            # 检查缓存数据是否可用
            if not self._is_cache_ready():
                self._retry_count += 1
                if self._retry_count <= self._max_retries:
                    _LOGGER.warning("滚动内容：等待其他传感器数据更新 (重试 %d/%d)", 
                                   self._retry_count, self._max_retries)
                    # 如果没有数据且是首次加载，设置默认提示信息
                    if not self._has_data:
                        self._set_default_attributes(current_time, "等待数据加载，请稍后重新加载")
                    return
                else:
                    _LOGGER.error("滚动内容：无法获取数据，已达到最大重试次数")
                    self._available = False
                    # 设置错误提示信息
                    self._set_default_attributes(current_time, "数据加载失败，请重新加载")
                    return

            # 重置重试计数
            self._retry_count = 0
            
            # 从缓存获取数据
            morning_data = _data_cache.get("morning", {})
            evening_data = _data_cache.get("evening", {})
            maxim_data = _data_cache.get("maxim", {})
            joke_data = _data_cache.get("joke", {})
            sentence_data = _data_cache.get("sentence", {})
            couplet_data = _data_cache.get("couplet", {})
            history_data = _data_cache.get("history", {})
            poetry_data = _data_cache.get("poetry", {})
            song_ci_data = _data_cache.get("songci", {})
            yuan_qu_data = _data_cache.get("yuanqu", {})

            # 提取各数据内容
            morning_content = morning_data.get("result", {}).get("content", "早安！新的一天开始了！")
            evening_content = evening_data.get("result", {}).get("content", "晚安！好梦！")
            maxim_result = maxim_data.get("result", {})
            joke_list = joke_data.get("result", {}).get("list", [{}])
            sentence_result = sentence_data.get("result", {})
            couplet_result = couplet_data.get("result", {})
            history_result = history_data.get("result", {})
            poetry_list = poetry_data.get("result", {}).get("list", [{}])
            song_ci_result = song_ci_data.get("result", {})
            yuan_qu_list = yuan_qu_data.get("result", {}).get("list", [{}])

            # 获取第一条数据
            joke_first = joke_list[0] if joke_list else {}
            poetry_first = poetry_list[0] if poetry_list else {}
            yuan_qu_first = yuan_qu_list[0] if yuan_qu_list else {}

            # 根据当前时间段确定显示内容
            scrolling_content = self._get_scrolling_content(
                morning_content,
                evening_content,
                maxim_result,
                joke_first,
                sentence_result,
                couplet_result,
                history_result,
                poetry_first,
                song_ci_result,
                yuan_qu_first
            )
            
            # 设置属性
            self._available = True
            self._has_data = True
            
            self._attributes = {
                "title": scrolling_content["title"],
                "title2": scrolling_content["title2"],  # 修改为title2
                "subtitle": scrolling_content["subtitle"],
                "content1": scrolling_content["content1"],
                "content2": scrolling_content["content2"],
                "align": scrolling_content["align"],
                "subalign": scrolling_content["subalign"],
                "time_slot": scrolling_content["time_slot"],
                "update_time": current_time
            }
            
            _LOGGER.info("天聚数行滚动内容更新成功，当前时段: %s", scrolling_content["time_slot"])
                
        except Exception as e:
            _LOGGER.error("更新天聚数行滚动内容传感器时出错: %s", e)
            self._available = False
            # 设置错误提示信息
            self._set_default_attributes(current_time, f"更新失败: {str(e)}")

    def _set_default_attributes(self, current_time, message):
        """设置默认属性，当没有数据时使用."""
        self._attributes = {
            "title": "滚动内容",
            "title2": "滚动内容",  # 修改为title2
            "subtitle": "",
            "content1": message,
            "content2": message,
            "align": "center",
            "subalign": "center",
            "time_slot": "默认时段",
            "update_time": current_time
        }

    def _is_cache_ready(self):
        """检查缓存数据是否就绪."""
        required_keys = ["morning", "evening", "maxim", "joke", "sentence", 
                        "couplet", "history", "poetry", "songci", "yuanqu"]
        
        for key in required_keys:
            if key not in _data_cache or not _data_cache[key]:
                return False
        
        # 检查是否有有效的结果数据
        for key in required_keys:
            data = _data_cache[key]
            if not data.get("result"):
                return False
                
        return True

    def _format_line_breaks(self, text):
        """格式化HTML换行（使用<br>）."""
        if text is None:
            return ""
        text_str = str(text)
        # 在中文标点符号（。？！）后面添加<br>，但不包括文本末尾
        return text_str.replace("。", "。<br>").replace("？", "？<br>").replace("！", "！<br>").replace("<br><br>", "<br>").rstrip("<br>")

    def _format_plain_breaks(self, text):
        """格式化纯文本换行（使用\\n）."""
        if text is None:
            return ""
        text_str = str(text)
        # 在中文标点符号（。？！）后面添加\n，但不包括文本末尾
        return text_str.replace("。", "。\n").replace("？", "？\n").replace("！", "！\n").replace("\n\n", "\n").rstrip("\n")

    def _remove_emoji(self, text):
        """移除文本中的表情符号."""
        import re
        # 匹配常见的表情符号
        emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"  # 表情符号
                           u"\U0001F300-\U0001F5FF"  # 符号和象形文字
                           u"\U0001F680-\U0001F6FF"  # 交通和地图符号
                           u"\U0001F1E0-\U0001F1FF"  # 旗帜 (iOS)
                           "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    def _get_scrolling_content(self, morning_content, evening_content, maxim_result, 
                             joke_result, sentence_result, couplet_result, history_result,
                             poetry_result, song_ci_result, yuan_qu_result):
        """根据当前时间段获取滚动内容."""
        from datetime import datetime
        
        now = datetime.now()
        total_minutes = now.hour * 60 + now.minute
        
        # 处理早安内容
        if "早安" not in morning_content:
            morning_content = f"早安！{morning_content}"
        
        # 处理晚安内容
        if "晚安" not in evening_content:
            evening_content = f"{evening_content}晚安！"
        
        # 处理笑话数据
        joke_title = joke_result.get("title", "今日笑话")
        joke_content = joke_result.get("content", "暂无笑话内容")
        
        # 处理名句数据
        sentence_source = sentence_result.get("source", "古籍")
        sentence_content = sentence_result.get("content", "暂无名句内容")
        # 对名句内容进行换行处理
        sentence_content_formatted = self._format_line_breaks(sentence_content)
        sentence_content_plain = self._format_plain_breaks(sentence_content)
        
        # 处理对联数据
        couplet_content = couplet_result.get("content", "暂无对联内容")
        
        # 处理历史数据
        history_content = history_result.get("content", "暂无历史内容")
        
        # 处理唐诗数据
        poetry_author = poetry_result.get("author", "未知作者")
        poetry_title = poetry_result.get("title", "无题")
        poetry_content = poetry_result.get("content", "暂无唐诗内容")
        # 对唐诗内容进行换行处理
        poetry_content_formatted = self._format_line_breaks(poetry_content)
        poetry_content_plain = self._format_plain_breaks(poetry_content)
        
        # 处理宋词数据
        song_ci_source = song_ci_result.get("source", "宋词")
        song_ci_content = song_ci_result.get("content", "暂无宋词内容")
        # 对宋词内容进行换行处理
        song_ci_content_formatted = self._format_line_breaks(song_ci_content)
        song_ci_content_plain = self._format_plain_breaks(song_ci_content)
        
        # 处理元曲数据
        yuan_qu_author = yuan_qu_result.get("author", "未知作者")
        yuan_qu_title = yuan_qu_result.get("title", "无题")
        yuan_qu_content = yuan_qu_result.get("content", "暂无元曲内容")
        # 对元曲内容进行换行处理
        yuan_qu_content_formatted = self._format_line_breaks(yuan_qu_content)
        yuan_qu_content_plain = self._format_plain_breaks(yuan_qu_content)
        
        # 处理格言数据
        maxim_en = maxim_result.get("en", "No maxim available")
        maxim_zh = maxim_result.get("zh", "暂无格言")
        
        # 时间段判断（删除了谜语时段，将其分配给其他内容）
        if total_minutes >= 5*60+30 and total_minutes < 8*60+30:  # 5:30-8:29
            title = "🌅早安问候"
            return {
                "title": title,
                "title2": self._remove_emoji(title),  # 修改为title2，移除表情符号
                "subtitle": "",
                "content1": morning_content,
                "content2": morning_content,
                "align": "left",
                "subalign": "center",
                "time_slot": "早安时段"
            }
        elif total_minutes >= 8*60+30 and total_minutes < 11*60:  # 8:30-10:59
            title = "☘️英文格言"
            return {
                "title": title,
                "title2": self._remove_emoji(title),  # 修改为title2，移除表情符号
                "subtitle": "",
                "content1": f"【英文】{maxim_en}<br>【中文】{maxim_zh}",
                "content2": f"【英文】{maxim_en}\n【中文】{maxim_zh}",
                "align": "left",
                "subalign": "center",
                "time_slot": "格言时段"
            }
        elif total_minutes >= 11*60 and total_minutes < 13*60:  # 11:00-12:59
            title = "🌻每日笑话"
            return {
                "title": title,
                "title2": self._remove_emoji(title),  # 修改为title2，移除表情符号
                "subtitle": joke_title,
                "content1": joke_content,
                "content2": f"{joke_title}\n{joke_content}",
                "align": "left",
                "subalign": "center",
                "time_slot": "笑话时段"
            }
        elif total_minutes >= 13*60 and total_minutes < 14*60+30:  # 13:00-14:29 (延长了名句时段)
            title = "🌻古籍名句"
            return {
                "title": title,
                "title2": self._remove_emoji(title),  # 修改为title2，移除表情符号
                "subtitle": f"《{sentence_source}》",
                "content1": sentence_content_formatted,  # content1不含出处信息
                "content2": f"《{sentence_source}》\n{sentence_content_plain}",  # content2包含出处信息
                "align": "center",
                "subalign": "center",
                "time_slot": "名句时段"
            }
        elif total_minutes >= 14*60+30 and total_minutes < 16*60:  # 14:30-15:59 (延长了对联时段)
            title = "🔖经典对联"
            return {
                "title": title,
                "title2": self._remove_emoji(title),  # 修改为title2，移除表情符号
                "subtitle": "",
                "content1": couplet_content,
                "content2": couplet_content,
                "align": "center",
                "subalign": "center",
                "time_slot": "对联时段"
            }
        elif total_minutes >= 16*60 and total_minutes < 18*60:  # 16:00-17:59 (延长了历史时段)
            title = "🏷️简说历史"
            return {
                "title": title,
                "title2": self._remove_emoji(title),  # 修改为title2，移除表情符号
                "subtitle": "",
                "content1": history_content,
                "content2": history_content,
                "align": "left",
                "subalign": "center",
                "time_slot": "历史时段"
            }
        elif total_minutes >= 18*60 and total_minutes < 19*60+30:  # 18:00-19:29
            title = "🔖唐诗鉴赏"
            return {
                "title": title,
                "title2": self._remove_emoji(title),  # 修改为title2，移除表情符号
                "subtitle": f"{poetry_author} · 《{poetry_title}》",
                "content1": poetry_content_formatted,  # content1不含作者和标题信息
                "content2": f"{poetry_author} · 《{poetry_title}》\n{poetry_content_plain}",  # content2包含作者和标题信息
                "align": "center",
                "subalign": "center",
                "time_slot": "唐诗时段"
            }
        elif total_minutes >= 19*60+30 and total_minutes < 21*60:  # 19:30-20:59
            title = "🌼最美宋词"
            return {
                "title": title,
                "title2": self._remove_emoji(title),  # 修改为title2，移除表情符号
                "subtitle": song_ci_source,
                "content1": song_ci_content_formatted,  # content1不含出处信息
                "content2": f"{song_ci_source}\n{song_ci_content_plain}",  # content2包含出处信息
                "align": "center",
                "subalign": "center",
                "time_slot": "宋词时段"
            }
        elif total_minutes >= 21*60 and total_minutes < 22*60+30:  # 21:00-22:29 (延长了元曲时段)
            title = "🔖精选元曲"
            return {
                "title": title,
                "title2": self._remove_emoji(title),  # 修改为title2，移除表情符号
                "subtitle": f"{yuan_qu_author} · 《{yuan_qu_title}》",
                "content1": yuan_qu_content_formatted,  # content1不含作者和标题信息
                "content2": f"{yuan_qu_author} · 《{yuan_qu_title}》\n{yuan_qu_content_plain}",  # content2包含作者和标题信息
                "align": "center",
                "subalign": "center",
                "time_slot": "元曲时段"
            }
        else:  # 22:30-次日5:29
            title = "🌃晚安问候"
            return {
                "title": title,
                "title2": self._remove_emoji(title),  # 修改为title2，移除表情符号
                "subtitle": "",
                "content1": evening_content,
                "content2": evening_content,
                "align": "left",
                "subalign": "center",
                "time_slot": "晚安时段"
            }

    def _get_current_time(self):
        """获取当前时间字符串."""
        from datetime import datetime
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")