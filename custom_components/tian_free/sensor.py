"""Sensor platform for Tian API integration."""
import logging
import asyncio
import aiohttp
import async_timeout
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

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
    CONF_SCROLL_INTERVAL,
    SCROLL_CONTENT_TYPES,
)

_LOGGER = logging.getLogger(__name__)

# 全局缓存，避免重复调用API
_data_cache = {}
_cache_timestamp = {}
_retry_count = {}

class BaseTianSensor(SensorEntity):
    """天聚数行传感器基类."""
    
    SCAN_INTERVAL = timedelta(hours=24)
    CACHE_TIMEOUT = 43200
    
    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_device_info = device_info
        self._state = "等待更新"
        self._attributes = {}
        self._available = True
        self._entry_id = entry_id
        self._retry_count = 0
        self._max_retries = 2
        self._last_api_update_time = None  # 记录API数据获取时间
        self._data_fetched = False  # 标记数据是否已获取

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

    async def _fetch_cached_data(self, cache_key, fetch_func):
        """获取缓存数据，避免重复调用API."""
        global _data_cache, _cache_timestamp
        
        current_time = self._get_current_timestamp()
        if (cache_key in _data_cache and 
            cache_key in _cache_timestamp and 
            current_time - _cache_timestamp[cache_key] < self.CACHE_TIMEOUT):
            _LOGGER.debug("使用缓存数据: %s", cache_key)
            return _data_cache[cache_key]
        
        # 调用API获取新数据
        data = await fetch_func()
        if data and data.get("code") == 200:
            _data_cache[cache_key] = data
            _cache_timestamp[cache_key] = current_time
            # 记录API数据获取时间 - 只在成功获取数据时更新
            self._last_api_update_time = self._get_current_time()
            self._data_fetched = True
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
                    
                    if data.get("code") == 200:
                        return data
                    elif data.get("code") == 130:
                        _LOGGER.warning("API调用频率超限，请稍后再试")
                        return None
                    elif data.get("code") == 100:
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
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_date(self):
        """获取当前日期字符串."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d")
    
    def _get_current_timestamp(self):
        """获取当前时间戳."""
        return int(datetime.now().timestamp())

    async def _schedule_daily_update(self):
        """安排每日更新."""
        now = datetime.now()
        tomorrow = now.replace(hour=0, minute=1, second=0, microsecond=0) + timedelta(days=1)
        delay = (tomorrow - now).total_seconds()
        
        async def daily_update_callback(_):
            await self.async_update()
            await self._schedule_daily_update()
        
        self.hass.loop.call_later(delay, asyncio.create_task, daily_update_callback(None))
        _LOGGER.info("已安排每日更新，将在 %s 执行", tomorrow)

    async def async_added_to_hass(self):
        """当实体添加到Home Assistant时调用."""
        await super().async_added_to_hass()
        await self._schedule_daily_update()

class TianJokeSensor(BaseTianSensor):
    """天聚数行笑话传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        super().__init__(api_key, device_info, entry_id)
        self._attr_name = "每日笑话"
        self._attr_unique_id = f"{entry_id}_joke"
        self._attr_icon = "mdi:emoticon-lol"

    async def async_update(self):
        """Update sensor data."""
        try:
            joke_data = await self._fetch_cached_data("joke", self._fetch_joke_data)
            
            if joke_data:
                joke_list = joke_data.get("result", {}).get("list", [])
                joke_result = joke_list[0] if joke_list else {}
                
                current_date = self._get_current_date()
                self._state = current_date
                self._available = True
                
                # 只在成功获取API数据时更新update_time，否则保持之前的值
                update_time = self._last_api_update_time if self._data_fetched else self._get_current_time()
                
                self._attributes = {
                    "title": "每日笑话",
                    "code": joke_data.get("code", 0),
                    "name": joke_result.get("title", ""),
                    "content": joke_result.get("content", ""),
                    "update_time": update_time,  # API数据获取时间，24小时内保持不变
                    "update_date": current_date
                }
                
                _LOGGER.info("天聚数行笑话更新成功")
                self._retry_count = 0
                
            else:
                if self._retry_count < self._max_retries:
                    self._retry_count += 1
                    _LOGGER.warning("笑话更新失败，将在30分钟后重试 (%d/%d)", 
                                   self._retry_count, self._max_retries)
                    
                    async def retry_update(_):
                        await self.async_update()
                    
                    self.hass.loop.call_later(1800, asyncio.create_task, retry_update(None))
                else:
                    self._available = False
                    self._state = "API请求失败"
                    _LOGGER.error("无法获取天聚数行笑话，已达到最大重试次数")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行笑话传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_joke_data(self):
        """获取笑话数据."""
        url = f"{JOKE_API_URL}?key={self._api_key}&num=1"
        return await self._fetch_api_data(url)

class TianMorningSensor(BaseTianSensor):
    """天聚数行早安传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        super().__init__(api_key, device_info, entry_id)
        self._attr_name = "早安心语"
        self._attr_unique_id = f"{entry_id}_morning"
        self._attr_icon = "mdi:weather-sunny"

    async def async_update(self):
        """Update sensor data."""
        try:
            morning_data = await self._fetch_cached_data("morning", self._fetch_morning_data)
            
            if morning_data:
                morning_content = morning_data.get("result", {}).get("content", "")
                
                if not morning_content or morning_content == "":
                    morning_content = "早安！新的一天开始了！"
                elif "早安" not in morning_content:
                    morning_content = f"早安！{morning_content}"
                
                current_date = self._get_current_date()
                self._state = current_date
                self._available = True
                
                # 只在成功获取API数据时更新update_time
                update_time = self._last_api_update_time if self._data_fetched else self._get_current_time()
                
                self._attributes = {
                    "title": "早安心语",
                    "code": morning_data.get("code", 0),
                    "content": morning_content,
                    "update_time": update_time,  # API数据获取时间，24小时内保持不变
                    "update_date": current_date
                }
                
                _LOGGER.info("天聚数行早安更新成功")
                self._retry_count = 0
                
            else:
                if self._retry_count < self._max_retries:
                    self._retry_count += 1
                    _LOGGER.warning("早安更新失败，将在30分钟后重试 (%d/%d)", 
                                   self._retry_count, self._max_retries)
                    
                    async def retry_update(_):
                        await self.async_update()
                    
                    self.hass.loop.call_later(1800, asyncio.create_task, retry_update(None))
                else:
                    self._available = False
                    self._state = "API请求失败"
                    _LOGGER.error("无法获取天聚数行早安，已达到最大重试次数")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行早安传感器时出错: %s", e)
            self._available = False
            self._state = f"更新失败: {str(e)}"

    async def _fetch_morning_data(self):
        """获取早安数据."""
        url = f"{MORNING_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)
class TianEveningSensor(BaseTianSensor):
    """天聚数行晚安传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        super().__init__(api_key, device_info, entry_id)
        self._attr_name = "晚安心语"
        self._attr_unique_id = f"{entry_id}_evening"
        self._attr_icon = "mdi:weather-night"

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
                
                # 设置状态为当前日期
                current_date = self._get_current_date()
                self._state = current_date
                self._available = True

                # 使用API数据获取时间作为update_time
                update_time = self._last_api_update_time if self._data_fetched else self._get_current_time()
                
                # 设置属性
                self._attributes = {
                    "title": "晚安心语",
                    "code": evening_data.get("code", 0),
                    "content": evening_content,
                    "update_time": update_time,
                    "update_date": current_date
                }
                
                _LOGGER.info("天聚数行晚安更新成功")
                
            else:
                self._available = False
                self._state = self._get_current_date()  # 即使失败也保持日期状态
                _LOGGER.error("无法获取天聚数行晚安，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行晚安传感器时出错: %s", e)
            self._available = False
            self._state = self._get_current_date()  # 即使异常也保持日期状态

    async def _fetch_evening_data(self):
        """获取晚安数据."""
        url = f"{EVENING_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

class TianPoetrySensor(BaseTianSensor):
    """天聚数行唐诗传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        super().__init__(api_key, device_info, entry_id)
        self._attr_name = "唐诗鉴赏"
        self._attr_unique_id = f"{entry_id}_poetry"
        self._attr_icon = "mdi:book-open-variant"

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取唐诗数据
            poetry_data = await self._fetch_cached_data("poetry", self._fetch_poetry_data)
            
            if poetry_data:
                poetry_list = poetry_data.get("result", {}).get("list", [])
                poetry_first = poetry_list[0] if poetry_list else {}
                
                # 设置状态为当前日期
                current_date = self._get_current_date()
                self._state = current_date
                self._available = True

                # 使用API数据获取时间作为update_time
                update_time = self._last_api_update_time if self._data_fetched else self._get_current_time()
                
                # 设置属性
                self._attributes = {
                    "title": "唐诗鉴赏",
                    "code": poetry_data.get("code", 0),
                    "content": poetry_first.get("content", ""),
                    "source": poetry_first.get("title", ""),
                    "author": poetry_first.get("author", ""),
                    "intro": poetry_first.get("intro", ""),
                    "kind": poetry_first.get("kind", ""),
                    "update_time": update_time,
                    "update_date": current_date
                }
                
                _LOGGER.info("天聚数行唐诗更新成功")
                
            else:
                self._available = False
                self._state = self._get_current_date()  # 即使失败也保持日期状态
                _LOGGER.error("无法获取天聚数行唐诗，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行唐诗传感器时出错: %s", e)
            self._available = False
            self._state = self._get_current_date()  # 即使异常也保持日期状态

    async def _fetch_poetry_data(self):
        """获取唐诗数据."""
        url = f"{POETRY_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

class TianSongCiSensor(BaseTianSensor):
    """天聚数行宋词传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        super().__init__(api_key, device_info, entry_id)
        self._attr_name = "最美宋词"
        self._attr_unique_id = f"{entry_id}_songci"
        self._attr_icon = "mdi:book-music"

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取宋词数据
            song_ci_data = await self._fetch_cached_data("songci", self._fetch_song_ci_data)
            
            if song_ci_data:
                song_ci_result = song_ci_data.get("result", {})
                
                # 设置状态为当前日期
                current_date = self._get_current_date()
                self._state = current_date
                self._available = True
                
                # 使用API数据获取时间作为update_time
                update_time = self._last_api_update_time if self._data_fetched else self._get_current_time()

                # 设置属性
                self._attributes = {
                    "title": "最美宋词",
                    "code": song_ci_data.get("code", 0),
                    "content": song_ci_result.get("content", ""),
                    "source": song_ci_result.get("source", ""),
                    "author": song_ci_result.get("author", ""),
                    "update_time": update_time,
                    "update_date": current_date
                }
                
                _LOGGER.info("天聚数行宋词更新成功")
                
            else:
                self._available = False
                self._state = self._get_current_date()  # 即使失败也保持日期状态
                _LOGGER.error("无法获取天聚数行宋词，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行宋词传感器时出错: %s", e)
            self._available = False
            self._state = self._get_current_date()  # 即使异常也保持日期状态

    async def _fetch_song_ci_data(self):
        """获取宋词数据."""
        url = f"{SONG_CI_API_URL}?key={self._api_key}"
        return await self._fetch_api_data(url)

class TianYuanQuSensor(BaseTianSensor):
    """天聚数行元曲传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        super().__init__(api_key, device_info, entry_id)
        self._attr_name = "精选元曲"
        self._attr_unique_id = f"{entry_id}_yuanqu"
        self._attr_icon = "mdi:music"

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取元曲数据
            yuan_qu_data = await self._fetch_cached_data("yuanqu", self._fetch_yuan_qu_data)
            
            if yuan_qu_data:
                yuan_qu_list = yuan_qu_data.get("result", {}).get("list", [])
                yuan_qu_first = yuan_qu_list[0] if yuan_qu_list else {}
                
                # 设置状态为当前日期
                current_date = self._get_current_date()
                self._state = current_date
                self._available = True

                # 使用API数据获取时间作为update_time
                update_time = self._last_api_update_time if self._data_fetched else self._get_current_time()
                
                # 设置属性
                self._attributes = {
                    "title": "精选元曲",
                    "code": yuan_qu_data.get("code", 0),
                    "content": yuan_qu_first.get("content", ""),
                    "source": yuan_qu_first.get("title", ""),
                    "author": yuan_qu_first.get("author", ""),
                    "note": yuan_qu_first.get("note", ""),
                    "translation": yuan_qu_first.get("translation", ""),
                    "update_time": update_time,
                    "update_date": current_date
                }
                
                _LOGGER.info("天聚数行元曲更新成功")
                
            else:
                self._available = False
                self._state = self._get_current_date()  # 即使失败也保持日期状态
                _LOGGER.error("无法获取天聚数行元曲，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行元曲传感器时出错: %s", e)
            self._available = False
            self._state = self._get_current_date()  # 即使异常也保持日期状态

    async def _fetch_yuan_qu_data(self):
        """获取元曲数据."""
        url = f"{YUAN_QU_API_URL}?key={self._api_key}&num=1&page=1"
        return await self._fetch_api_data(url)

class TianHistorySensor(BaseTianSensor):
    """天聚数行历史传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        super().__init__(api_key, device_info, entry_id)
        self._attr_name = "简说历史"
        self._attr_unique_id = f"{entry_id}_history"
        self._attr_icon = "mdi:calendar-clock"

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取历史数据
            history_data = await self._fetch_cached_data("history", self._fetch_history_data)
            
            if history_data:
                history_result = self._extract_result(history_data)
                
                # 设置状态为当前日期
                current_date = self._get_current_date()
                self._state = current_date
                self._available = True

                # 使用API数据获取时间作为update_time
                update_time = self._last_api_update_time if self._data_fetched else self._get_current_time()
                
                # 设置属性
                self._attributes = {
                    "title": "简说历史",
                    "code": history_data.get("code", 0),
                    "content": history_result.get("content", "暂无历史内容"),
                    "update_time": update_time,
                    "update_date": current_date
                }
                
                _LOGGER.info("天聚数行历史更新成功")
                
            else:
                self._available = False
                self._state = self._get_current_date()  # 即使失败也保持日期状态
                _LOGGER.error("无法获取天聚数行历史，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行历史传感器时出错: %s", e)
            self._available = False
            self._state = self._get_current_date()  # 即使异常也保持日期状态

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

class TianSentenceSensor(BaseTianSensor):
    """天聚数行名句传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        super().__init__(api_key, device_info, entry_id)
        self._attr_name = "古籍名句"
        self._attr_unique_id = f"{entry_id}_sentence"
        self._attr_icon = "mdi:format-quote-close"

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取名句数据
            sentence_data = await self._fetch_cached_data("sentence", self._fetch_sentence_data)
            
            if sentence_data:
                sentence_result = self._extract_result(sentence_data)
                
                # 设置状态为当前日期
                current_date = self._get_current_date()
                self._state = current_date
                self._available = True

                # 使用API数据获取时间作为update_time
                update_time = self._last_api_update_time if self._data_fetched else self._get_current_time()
                
                # 设置属性
                self._attributes = {
                    "title": "古籍名句",
                    "code": sentence_data.get("code", 0),
                    "content": sentence_result.get("content", "暂无名句内容"),
                    "source": sentence_result.get("source", "未知来源"),
                    "update_time": update_time,
                    "update_date": current_date
                }
                
                _LOGGER.info("天聚数行名句更新成功")
                
            else:
                self._available = False
                self._state = self._get_current_date()  # 即使失败也保持日期状态
                _LOGGER.error("无法获取天聚数行名句，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行名句传感器时出错: %s", e)
            self._available = False
            self._state = self._get_current_date()  # 即使异常也保持日期状态

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

class TianCoupletSensor(BaseTianSensor):
    """天聚数行对联传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        super().__init__(api_key, device_info, entry_id)
        self._attr_name = "经典对联"
        self._attr_unique_id = f"{entry_id}_couplet"
        self._attr_icon = "mdi:brush"

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取对联数据
            couplet_data = await self._fetch_cached_data("couplet", self._fetch_couplet_data)
            
            if couplet_data:
                couplet_result = self._extract_result(couplet_data)
                
                # 设置状态为当前日期
                current_date = self._get_current_date()
                self._state = current_date
                self._available = True

                # 使用API数据获取时间作为update_time
                update_time = self._last_api_update_time if self._data_fetched else self._get_current_time()
                
                # 设置属性
                self._attributes = {
                    "title": "经典对联",
                    "code": couplet_data.get("code", 0),
                    "content": couplet_result.get("content", "暂无对联内容"),
                    "update_time": update_time,
                    "update_date": current_date
                }
                
                _LOGGER.info("天聚数行对联更新成功")
                
            else:
                self._available = False
                self._state = self._get_current_date()  # 即使失败也保持日期状态
                _LOGGER.error("无法获取天聚数行对联，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行对联传感器时出错: %s", e)
            self._available = False
            self._state = self._get_current_date()  # 即使异常也保持日期状态

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

class TianMaximSensor(BaseTianSensor):
    """天聚数行格言传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        super().__init__(api_key, device_info, entry_id)
        self._attr_name = "英文格言"
        self._attr_unique_id = f"{entry_id}_maxim"
        self._attr_icon = "mdi:translate"

    async def async_update(self):
        """Update sensor data."""
        try:
            # 获取格言数据
            maxim_data = await self._fetch_cached_data("maxim", self._fetch_maxim_data)
            
            if maxim_data:
                maxim_result = self._extract_result(maxim_data)
                
                # 设置状态为当前日期
                current_date = self._get_current_date()
                self._state = current_date
                self._available = True

                # 使用API数据获取时间作为update_time
                update_time = self._last_api_update_time if self._data_fetched else self._get_current_time()
                
                # 设置属性
                self._attributes = {
                    "title": "英文格言",
                    "code": maxim_data.get("code", 0),
                    "en": maxim_result.get("en", ""),
                    "zh": maxim_result.get("zh", ""),
                    "update_time": update_time,
                    "update_date": current_date
                }
                
                _LOGGER.info("天聚数行格言更新成功")
                
            else:
                self._available = False
                self._state = self._get_current_date()  # 即使失败也保持日期状态
                _LOGGER.error("无法获取天聚数行格言，请检查API密钥是否正确")
                
        except Exception as e:
            _LOGGER.error("更新天聚数行格言传感器时出错: %s", e)
            self._available = False
            self._state = self._get_current_date()  # 即使异常也保持日期状态

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


class TianTimeSlotContentSensor(SensorEntity):
    """天聚数行时段内容传感器（原定期内容）."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "时段内容"
        self._attr_unique_id = f"{entry_id}_time_slot_content"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:calendar-clock"
        self._state = self._get_current_date()
        self._attributes = {}
        self._available = True
        self._last_time_slot = None
        self._last_update_time = None  # 记录时段触发更新时间

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
        """Update sensor data - 使用缓存数据，时段变化时触发."""
        current_date = self._get_current_date()
        self._state = current_date
        
        try:
            # 检查缓存数据是否可用
            if not self._is_cache_ready():
                self._set_default_attributes(current_date, "等待数据加载，请稍后查看")
                _LOGGER.debug("时段内容：缓存数据未就绪")
                return

            # 获取当前时间段
            current_time_slot = self._get_current_time_slot()
            
            # 如果时段发生变化，则更新内容
            if current_time_slot != self._last_time_slot:
                self._last_time_slot = current_time_slot
                
                # 记录时段触发时间
                self._last_update_time = self._get_current_time()
                
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
                time_slot_content = self._get_time_slot_content(
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
                
                # 设置属性 - update_time为时段触发时的时间
                self._available = True
                
                self._attributes = {
                    "title": time_slot_content["title"],
                    "title2": time_slot_content["title2"],
                    "subtitle": time_slot_content["subtitle"],
                    "content1": time_slot_content["content1"],
                    "content2": time_slot_content["content2"],
                    "align": time_slot_content["align"],
                    "subalign": time_slot_content["subalign"],
                    "time_slot": time_slot_content["time_slot"],
                    "update_time": self._last_update_time,  # 时段触发时的时间
                    "update_date": current_date
                }
                
                _LOGGER.debug("天聚数行时段内容更新成功，当前时段: %s", time_slot_content["time_slot"])
            else:
                # 时段未变化，保持之前的update_time
                if self._last_update_time:
                    self._attributes["update_time"] = self._last_update_time
                
        except Exception as e:
            _LOGGER.error("更新天聚数行时段内容传感器时出错: %s", e)
            self._available = False

    def _get_current_time_slot(self):
        """获取当前时间段."""
        from datetime import datetime
        now = datetime.now()
        total_minutes = now.hour * 60 + now.minute
        
        if total_minutes >= 5*60 and total_minutes < 8*60:
            return "早安时段"
        elif total_minutes >= 8*60 and total_minutes < 10*60:
            return "格言时段"
        elif total_minutes >= 10*60 and total_minutes < 12*60:
            return "笑话时段"
        elif total_minutes >= 12*60 and total_minutes < 14*60:
            return "名句时段"
        elif total_minutes >= 14*60 and total_minutes < 16*60:
            return "对联时段"
        elif total_minutes >= 16*60 and total_minutes < 18*60:
            return "历史时段"
        elif total_minutes >= 18*60 and total_minutes < 20*60:
            return "唐诗时段"
        elif total_minutes >= 20*60 and total_minutes < 22*60:
            return "宋词时段"
        elif total_minutes >= 22*60 and total_minutes < 23*60+59:
            return "元曲时段"
        else:
            return "晚安时段"

    def _set_default_attributes(self, current_date, message):
        """设置默认属性，当没有数据时使用."""
        self._attributes = {
            "title": "时段内容",
            "title2": "时段内容",
            "subtitle": "",
            "content1": message,
            "content2": message,
            "align": "center",
            "subalign": "center",
            "time_slot": "默认时段",
            "update_time": self._get_current_time(),
            "update_date": current_date
        }

    def _is_cache_ready(self):
        """检查缓存数据是否就绪."""
        required_keys = ["morning", "evening", "maxim", "joke", "sentence", 
                        "couplet", "history", "poetry", "songci", "yuanqu"]
        
        for key in required_keys:
            if key not in _data_cache or not _data_cache[key]:
                return False
        
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
        return text_str.replace("。", "。<br>").replace("？", "？<br>").replace("！", "！<br>").replace("<br><br>", "<br>").rstrip("<br>")

    def _format_plain_breaks(self, text):
        """格式化纯文本换行（使用\\n）."""
        if text is None:
            return ""
        text_str = str(text)
        return text_str.replace("。", "。\n").replace("？", "？\n").replace("！", "！\n").replace("\n\n", "\n").rstrip("\n")

    def _remove_emoji(self, text):
        """移除文本中的表情符号."""
        import re
        emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"
                           u"\U0001F300-\U0001F5FF"
                           u"\U0001F680-\U0001F6FF"
                           u"\U0001F1E0-\U0001F1FF"
                           "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    def _get_time_slot_content(self, morning_content, evening_content, maxim_result, 
                              joke_result, sentence_result, couplet_result, history_result,
                              poetry_result, song_ci_result, yuan_qu_result):
        """根据当前时间段获取时段内容."""
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
        poetry_content_formatted = self._format_line_breaks(poetry_content)
        poetry_content_plain = self._format_plain_breaks(poetry_content)
        
        # 处理宋词数据
        song_ci_source = song_ci_result.get("source", "宋词")
        song_ci_content = song_ci_result.get("content", "暂无宋词内容")
        song_ci_content_formatted = self._format_line_breaks(song_ci_content)
        song_ci_content_plain = self._format_plain_breaks(song_ci_content)
        
        # 处理元曲数据
        yuan_qu_author = yuan_qu_result.get("author", "未知作者")
        yuan_qu_title = yuan_qu_result.get("title", "无题")
        yuan_qu_content = yuan_qu_result.get("content", "暂无元曲内容")
        yuan_qu_content_formatted = self._format_line_breaks(yuan_qu_content)
        yuan_qu_content_plain = self._format_plain_breaks(yuan_qu_content)
        
        # 处理格言数据
        maxim_en = maxim_result.get("en", "No maxim available")
        maxim_zh = maxim_result.get("zh", "暂无格言")
        
        # 时间段判断
        if total_minutes >= 5*60 and total_minutes < 8*60:
            title = "🌅早安问候"
            return {
                "title": title,
                "title2": self._remove_emoji(title),
                "subtitle": "",
                "content1": morning_content,
                "content2": morning_content,
                "align": "left",
                "subalign": "center",
                "time_slot": "早安时段"
            }
        elif total_minutes >= 8*60 and total_minutes < 10*60:
            title = "☘️英文格言"
            return {
                "title": title,
                "title2": self._remove_emoji(title),
                "subtitle": "",
                "content1": f"【英文】{maxim_en}<br>【中文】{maxim_zh}",
                "content2": f"【英文】{maxim_en}\n【中文】{maxim_zh}",
                "align": "left",
                "subalign": "center",
                "time_slot": "格言时段"
            }
        elif total_minutes >= 10*60 and total_minutes < 12*60:
            title = "🌻每日笑话"
            return {
                "title": title,
                "title2": self._remove_emoji(title),
                "subtitle": joke_title,
                "content1": joke_content,
                "content2": f"{joke_title}\n{joke_content}",
                "align": "left",
                "subalign": "center",
                "time_slot": "笑话时段"
            }
        elif total_minutes >= 12*60 and total_minutes < 14*60:
            title = "🌻古籍名句"
            return {
                "title": title,
                "title2": self._remove_emoji(title),
                "subtitle": f"《{sentence_source}》",
                "content1": sentence_content_formatted,
                "content2": f"《{sentence_source}》\n{sentence_content_plain}",
                "align": "center",
                "subalign": "center",
                "time_slot": "名句时段"
            }
        elif total_minutes >= 14*60 and total_minutes < 16*60:
            title = "🔖经典对联"
            return {
                "title": title,
                "title2": self._remove_emoji(title),
                "subtitle": "",
                "content1": couplet_content,
                "content2": couplet_content,
                "align": "center",
                "subalign": "center",
                "time_slot": "对联时段"
            }
        elif total_minutes >= 16*60 and total_minutes < 18*60:
            title = "🏷️简说历史"
            return {
                "title": title,
                "title2": self._remove_emoji(title),
                "subtitle": "",
                "content1": history_content,
                "content2": history_content,
                "align": "left",
                "subalign": "center",
                "time_slot": "历史时段"
            }
        elif total_minutes >= 18*60 and total_minutes < 20*60:
            title = "🔖唐诗鉴赏"
            return {
                "title": title,
                "title2": self._remove_emoji(title),
                "subtitle": f"{poetry_author} · 《{poetry_title}》",
                "content1": poetry_content_formatted,
                "content2": f"{poetry_author} · 《{poetry_title}》\n{poetry_content_plain}",
                "align": "center",
                "subalign": "center",
                "time_slot": "唐诗时段"
            }
        elif total_minutes >= 12*60 and total_minutes < 22*60:
            title = "🌼最美宋词"
            return {
                "title": title,
                "title2": self._remove_emoji(title),
                "subtitle": song_ci_source,
                "content1": song_ci_content_formatted,
                "content2": f"{song_ci_source}\n{song_ci_content_plain}",
                "align": "center",
                "subalign": "center",
                "time_slot": "宋词时段"
            }
        elif total_minutes >= 22*60 and total_minutes < 23*60+59:
            title = "🔖精选元曲"
            return {
                "title": title,
                "title2": self._remove_emoji(title),
                "subtitle": f"{yuan_qu_author} · 《{yuan_qu_title}》",
                "content1": yuan_qu_content_formatted,
                "content2": f"{yuan_qu_author} · 《{yuan_qu_title}》\n{yuan_qu_content_plain}",
                "align": "center",
                "subalign": "center",
                "time_slot": "元曲时段"
            }
        else:
            title = "🌃晚安问候"
            return {
                "title": title,
                "title2": self._remove_emoji(title),
                "subtitle": "",
                "content1": evening_content,
                "content2": evening_content,
                "align": "left",
                "subalign": "center",
                "time_slot": "晚安时段"
            }

    def _get_current_time(self):
        """获取当前时间字符串."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_date(self):
        """获取当前日期字符串."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d")

class TianScrollingContentSensor(SensorEntity):
    """天聚数行滚动内容传感器."""

    def __init__(self, api_key: str, device_info: DeviceInfo, entry_id: str, scroll_interval: int):
        """Initialize the sensor."""
        self._api_key = api_key
        self._attr_name = "滚动内容"
        self._attr_unique_id = f"{entry_id}_scrolling_content"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:message-text"
        self._state = self._get_current_date()
        self._attributes = {}
        self._available = True
        self._scroll_interval = scroll_interval
        self._current_index = 0
        self._content_types = SCROLL_CONTENT_TYPES  # 使用更新后的内容类型列表
        self._unsub_timer = None
        self._last_scroll_update_time = None  # 记录滚动内容更新时间

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

    async def async_added_to_hass(self):
        """当实体添加到Home Assistant时调用."""
        await super().async_added_to_hass()
        self._start_scrolling_timer()

    async def async_will_remove_from_hass(self):
        """当实体从Home Assistant移除时调用."""
        if self._unsub_timer:
            self._unsub_timer()
        await super().async_will_remove_from_hass()

    def _start_scrolling_timer(self):
        """启动滚动定时器."""
        if self._unsub_timer:
            self._unsub_timer()
        
        self._unsub_timer = async_track_time_interval(
            self.hass,
            self._update_scrolling_content,
            timedelta(minutes=self._scroll_interval)
        )
        
        _LOGGER.info("滚动内容定时器已启动，间隔: %d 分钟", self._scroll_interval)
        
        self.hass.async_create_task(self._update_scrolling_content(None))

    async def _update_scrolling_content(self, _):
        """更新滚动内容."""
        current_date = self._get_current_date()
        self._state = current_date
        
        try:
            if not self._is_cache_ready():
                self._set_default_attributes(current_date, "等待数据加载，请稍后查看")
                _LOGGER.debug("滚动内容：缓存数据未就绪")
                return

            content_type = self._content_types[self._current_index]
            scrolling_content = self._get_content_by_type(content_type)
            
            if scrolling_content:
                self._available = True
                
                # 记录滚动内容更新时间
                self._last_scroll_update_time = self._get_current_time()
                
                self._attributes = {
                    "title": scrolling_content["title"],
                    "title2": scrolling_content["title2"],
                    "subtitle": scrolling_content["subtitle"],
                    "content1": scrolling_content["content1"],
                    "content2": scrolling_content["content2"],
                    "align": scrolling_content["align"],
                    "subalign": scrolling_content["subalign"],
                    "content_type": content_type,
                    "update_time": self._last_scroll_update_time,  # 滚动内容更新时的时间
                    "update_date": current_date
                }
                
                _LOGGER.debug("滚动内容更新成功，当前类型: %s", content_type)
                self._current_index = (self._current_index + 1) % len(self._content_types)
            else:
                self._set_default_attributes(current_date, "无法获取内容数据")
                    
        except Exception as e:
            _LOGGER.error("更新滚动内容传感器时出错: %s", e)
            self._available = False

    def _get_content_by_type(self, content_type):
        """根据内容类型获取对应的内容."""
        data = _data_cache.get(content_type, {})
        
        if not data or not data.get("result"):
            return None
        
        result = data.get("result", {})
        
        if content_type == "joke":
            joke_list = result.get("list", [{}])
            joke_result = joke_list[0] if joke_list else {}
            return {
                "title": "🌻每日笑话",
                "title2": "每日笑话",
                "subtitle": joke_result.get("title", "今日笑话"),
                "content1": joke_result.get("content", "暂无笑话内容"),
                "content2": f"{joke_result.get('title', '今日笑话')}\n{joke_result.get('content', '暂无笑话内容')}",
                "align": "left",
                "subalign": "center"
            }
        
        elif content_type == "poetry":
            poetry_list = result.get("list", [{}])
            poetry_result = poetry_list[0] if poetry_list else {}
            poetry_content = poetry_result.get("content", "暂无唐诗内容")
            poetry_content_formatted = self._format_line_breaks(poetry_content)
            poetry_content_plain = self._format_plain_breaks(poetry_content)
            return {
                "title": "🔖唐诗鉴赏",
                "title2": "唐诗鉴赏",
                "subtitle": f"{poetry_result.get('author', '未知作者')} · 《{poetry_result.get('title', '无题')}》",
                "content1": poetry_content_formatted,
                "content2": f"{poetry_result.get('author', '未知作者')} · 《{poetry_result.get('title', '无题')}》\n{poetry_content_plain}",
                "align": "center",
                "subalign": "center"
            }
        
        elif content_type == "songci":
            song_ci_content = result.get("content", "暂无宋词内容")
            song_ci_content_formatted = self._format_line_breaks(song_ci_content)
            song_ci_content_plain = self._format_plain_breaks(song_ci_content)
            return {
                "title": "🌼最美宋词",
                "title2": "最美宋词",
                "subtitle": result.get("source", "宋词"),
                "content1": song_ci_content_formatted,
                "content2": f"{result.get('source', '宋词')}\n{song_ci_content_plain}",
                "align": "center",
                "subalign": "center"
            }
        
        elif content_type == "yuanqu":
            yuan_qu_list = result.get("list", [{}])
            yuan_qu_result = yuan_qu_list[0] if yuan_qu_list else {}
            yuan_qu_content = yuan_qu_result.get("content", "暂无元曲内容")
            yuan_qu_content_formatted = self._format_line_breaks(yuan_qu_content)
            yuan_qu_content_plain = self._format_plain_breaks(yuan_qu_content)
            return {
                "title": "🔖精选元曲",
                "title2": "精选元曲",
                "subtitle": f"{yuan_qu_result.get('author', '未知作者')} · 《{yuan_qu_result.get('title', '无题')}》",
                "content1": yuan_qu_content_formatted,
                "content2": f"{yuan_qu_result.get('author', '未知作者')} · 《{yuan_qu_result.get('title', '无题')}》\n{yuan_qu_content_plain}",
                "align": "center",
                "subalign": "center"
            }
        
        elif content_type == "history":
            history_content = result.get("content", "暂无历史内容")
            return {
                "title": "🏷️简说历史",
                "title2": "简说历史",
                "subtitle": "",
                "content1": history_content,
                "content2": history_content,
                "align": "left",
                "subalign": "center"
            }
        
        elif content_type == "sentence":
            sentence_source = result.get("source", "古籍")
            sentence_content = result.get("content", "暂无名句内容")
            sentence_content_formatted = self._format_line_breaks(sentence_content)
            sentence_content_plain = self._format_plain_breaks(sentence_content)
            return {
                "title": "🌻古籍名句",
                "title2": "古籍名句",
                "subtitle": f"《{sentence_source}》",
                "content1": sentence_content_formatted,
                "content2": f"《{sentence_source}》\n{sentence_content_plain}",
                "align": "center",
                "subalign": "center"
            }
        
        elif content_type == "couplet":
            couplet_content = result.get("content", "暂无对联内容")
            return {
                "title": "🔖经典对联",
                "title2": "经典对联",
                "subtitle": "",
                "content1": couplet_content,
                "content2": couplet_content,
                "align": "center",
                "subalign": "center"
            }
        
        elif content_type == "maxim":
            maxim_en = result.get("en", "No maxim available")
            maxim_zh = result.get("zh", "暂无格言")
            return {
                "title": "☘️英文格言",
                "title2": "英文格言",
                "subtitle": "",
                "content1": f"【英文】{maxim_en}<br>【中文】{maxim_zh}",
                "content2": f"【英文】{maxim_en}\n【中文】{maxim_zh}",
                "align": "left",
                "subalign": "center"
            }
        
        return None

    def _set_default_attributes(self, current_date, message):
        """设置默认属性，当没有数据时使用."""
        self._attributes = {
            "title": "滚动内容",
            "title2": "滚动内容",
            "subtitle": "",
            "content1": message,
            "content2": message,
            "align": "center",
            "subalign": "center",
            "content_type": "unknown",
            "update_time": self._get_current_time(),
            "update_date": current_date
        }

    def _is_cache_ready(self):
        """检查缓存数据是否就绪."""
        for content_type in self._content_types:
            if content_type not in _data_cache or not _data_cache[content_type]:
                return False
            if not _data_cache[content_type].get("result"):
                return False
        return True

    def _format_line_breaks(self, text):
        """格式化HTML换行（使用<br>）."""
        if text is None:
            return ""
        text_str = str(text)
        return text_str.replace("。", "。<br>").replace("？", "？<br>").replace("！", "！<br>").replace("<br><br>", "<br>").rstrip("<br>")

    def _format_plain_breaks(self, text):
        """格式化纯文本换行（使用\\n）."""
        if text is None:
            return ""
        text_str = str(text)
        return text_str.replace("。", "。\n").replace("？", "？\n").replace("！", "！\n").replace("\n\n", "\n").rstrip("\n")

    def _remove_emoji(self, text):
        """移除文本中的表情符号."""
        import re
        emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"
                           u"\U0001F300-\U0001F5FF"
                           u"\U0001F680-\U0001F6FF"
                           u"\U0001F1E0-\U0001F1FF"
                           "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    def _get_current_time(self):
        """获取当前时间字符串."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_current_date(self):
        """获取当前日期字符串."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d")

    def update_scroll_interval(self, new_interval):
        """更新滚动间隔."""
        if 1 <= new_interval <= 60:
            self._scroll_interval = new_interval
            self._start_scrolling_timer()
            _LOGGER.info("滚动内容间隔已更新为: %d 分钟", new_interval)
        else:
            _LOGGER.error("无效的滚动间隔: %d，必须在1-60分钟之间", new_interval)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    api_key = config_entry.data[CONF_API_KEY]
    scroll_interval = config_entry.data.get(CONF_SCROLL_INTERVAL, 5)
    
    device_info = DeviceInfo(
        identifiers={(DOMAIN, "tian_info_query")},
        name=DEVICE_NAME,
        manufacturer=DEVICE_MANUFACTURER,
        model=DEVICE_MODEL,
        configuration_url="https://www.tianapi.com/",
    )
    
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
        TianTimeSlotContentSensor(api_key, device_info, config_entry.entry_id),
        TianScrollingContentSensor(api_key, device_info, config_entry.entry_id, scroll_interval),
    ]
    
    async_add_entities(sensors, update_before_add=True)
    _LOGGER.info("天聚数行免费版集成 v1.1.0 加载成功，实体已创建并开始首次更新")