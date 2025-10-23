# Tianju Data Free Version Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

This is a custom integration for Home Assistant designed to fetch various cultural information content from [Tianju Data], including morning/night greetings, Tang poetry, Song lyrics, Yuan songs, today in history, English quotes, ancient book quotes, and more. The free version is specifically customized for Tianju Data regular members (free).

## 🆓 Why Develop a Free Version?

Since Tianju Data API regular members can only apply for up to 10 free API interfaces, we've specially developed this free version integration to allow broader users to access these high-quality cultural contents.

### Free Version Features:
- ✅ **Completely Free** - No paid API key required
- ✅ **Curated Content** - Retains the most popular 10 API interfaces. Besides morning/night greetings (default), the other 8 APIs are optional - you don't need to apply for all 10 APIs at once
- ✅ **Independent Entities** - Each API corresponds to an independent sensor for easy use
- ✅ **Smart Caching** - 1-hour cache mechanism to avoid API call limits
- ✅ **Rotating Display** - Switches display content based on set rotation intervals
- ✅ **Timed Display** - Intelligently switches display content based on time periods

## 📋 Included Content

This integration includes the following 12 sensor entities:

1. **Daily Joke** - Light moments, updated daily
2. **Morning Greeting** - Warm greetings for a beautiful day
3. **Evening Greeting** - Warm wishes to accompany your sleep
4. **Tang Poetry Appreciation** - Classic Tang poetry, cultural treasures
5. **Beautiful Song Lyrics** - Graceful and bold, lasting lyrical charm
6. **Selected Yuan Songs** - Opera essence, artistic heritage
7. **Brief History** - Historical knowledge, learning from the past
8. **Ancient Book Quotes** - Classic quotes, wisdom crystallization
9. **Classic Couplets** - Traditional couplets, cultural charm
10. **English Quotes** - Bilingual quotes, enlightening wisdom
11. **Rotating Content** - Rotating display, shows throughout the day
12. **Timed Content** - Timed switching, shows throughout the day

(**Morning Greeting, Evening Greeting, Rotating Content, and Timed Content are fixed, while the other 8 are optional**)

## 🚀 Installation

### Method 1: Via HACS Installation (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed
2. In HACS "Integrations" page, click the three-dot menu in the upper right corner, select "Custom repositories"
3. Add repository URL: https://github.com/lambilly/hass_tian_free/, category select "Integration"
4. Search for "Tianju Data Free Version" in HACS
5. Click Download
6. Restart Home Assistant

### Method 2: Manual Installation

1. Download the entire `tian_free` folder
2. Place it in the `custom_components` directory
3. Restart Home Assistant
4. Add "Tianju Data Free Version" in the integrations page

## ⚙️ Configuration

1. In Home Assistant, go to "Configuration" -> "Integrations"
2. Click "+ Add Integration"
3. Search for "Tianju Data Free Version"
4. Enter your Tianju Data API key (32-bit)
5. Click "Submit"

## 🔧 API Key Acquisition

1. Visit [Tianju Data Official Website](https://www.tianapi.com/)
2. Register an account and log in
3. Apply for free API keys in the console
4. Each account can apply for 10 free API interfaces

## 📊 Entity Attributes

Each sensor entity includes the following attributes:
- `title`: Entity title
- `code`: API return status code
- `update_time`: Last update time
- Other content-related attributes

## 📰 Card Display (Requires HACS installation: Lovelace HTML Jinja2 Template card)
```yaml
type: custom:html-template-card
content: >
  {% set entity = 'sensor.gun_dong_nei_rong' %}<div style="color: white;"><p
  align="left"><h3 style="color: white; margin-bottom: 0px;">【{{
  state_attr(entity, 'title') }}】</h3><p align="{{ state_attr(entity,
  'subalign') }}" style="color: yellow; margin: 0px 0;"><b>{{ state_attr(entity,
  'subtitle') }}</b></p></div> <p align="{{ state_attr(entity, 'align') }}"
  style="color: white; font-size: 1.0em; margin-top: 10px;">{{
  state_attr(entity, 'content1') }}
```

## 🕒 Timed Content Sensor Schedule

The rotating content sensor switches display content based on set intervals (1-60 minutes):
The timed content sensor automatically switches display content based on time periods, with the basic schedule as follows (actual schedule will adjust based on the number of APIs selected):

- **05:00-07:59** 🌅 Morning Greetings
- **08:00-09:59** ☘️ English Quotes
- **10:00-10:59** 🌻 Daily Jokes
- **11:00-12:59** 🌻 Ancient Book Quotes
- **13:00-14:59** 🔖 Classic Couplets
- **15:00-16:59** 🏷️ Brief History
- **17:00-18:59** 🔖 Tang Poetry Appreciation
- **19:00-20:59** 🌼 Beautiful Song Lyrics
- **21:00-21:59** 🔖 Selected Yuan Songs
- **22:00-04:59** 🌃 Evening Greetings

## 🔄 Update Frequency

- All sensors automatically update once daily
- Cache mechanism: Repeated calls within 1 hour use cached data
- Supports manual immediate updates

## 🐛 Troubleshooting

### Common Issues

**Q: API Key Error**
A: Please confirm the API key is a 32-character string and valid on the Tianju Data official website

**Q: Entity shows "API Request Failed"**
A: Check network connection, confirm API key is valid and hasn't exceeded call limits

**Q: Rotating content shows "Waiting for data loading"**
A: First installation requires waiting for all sensors to complete initial updates, or manually reload

**Q: How to reload the integration?**
A: Click "Reload Tianju Data Free Version" in Developer Tools

## 📄 License

This project uses the MIT License

## 🙏 Acknowledgments

Thanks to Tianju Data for providing free API services

Thanks to the Home Assistant community

Thanks to all contributors and users

## 🐛 Issue Reporting

If you encounter any problems or have improvement suggestions, please submit an Issue in the GitHub repository.

---

**Note**: This integration is for personal learning and non-commercial use only. Please comply with Tianju Data's API usage terms.
