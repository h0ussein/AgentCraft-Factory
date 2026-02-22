import os
import requests

def get_weather(city: str) -> str:
    """
    Retrieves current weather information for a specified city.

    Args:
        city: The name of the city for which to get weather information.

    Returns:
        A string containing the current weather description, temperature,
        humidity, and wind speed, or an error message if the city is not found
        or the API key is missing.
    """
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        return 'Please add your OPENWEATHER_API_KEY in settings'

    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': city,
        'appid': api_key,
        'units': 'metric'  # Use 'imperial' for Fahrenheit
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        weather_data = response.json()

        if weather_data.get('cod') == '404':
            return f"Could not find weather for city: {city}. Please check the city name."

        main_data = weather_data.get('main', {})
        weather_description = weather_data['weather'][0]['description'] if weather_data.get('weather') else 'N/A'
        temperature = main_data.get('temp', 'N/A')
        feels_like = main_data.get('feels_like', 'N/A')
        humidity = main_data.get('humidity', 'N/A')
        wind_speed = weather_data.get('wind', {}).get('speed', 'N/A')

        result = (
            f"Weather in {city}:\n"
            f"Description: {weather_description.capitalize()}\n"
            f"Temperature: {temperature}°C (Feels like: {feels_like}°C)\n"
            f"Humidity: {humidity}%\n"
            f"Wind Speed: {wind_speed} m/s"
        )
        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return "Unauthorized: Please check your OpenWeatherMap API key."
        elif e.response.status_code == 404:
            return f"Could not find weather for city: {city}. Please check the city name."
        return f"HTTP error occurred: {e}"
    except requests.exceptions.ConnectionError:
        return "Connection error: Could not connect to the weather service. Please check your internet connection."
    except requests.exceptions.Timeout:
        return "Timeout error: The request to the weather service timed out."
    except requests.exceptions.RequestException as e:
        return f"An unexpected error occurred: {e}"
    except KeyError:
        return "Error parsing weather data. The API response format might have changed or is incomplete."