import requests

date = input("Input Date (YYYY-MM-DD): ")

params = {
    "latitude": 43.7401,
    "longitude": 7.4266,
    "start_date": date,
    "end_date": date,
    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
    "hourly": "relative_humidity_2m",
    "timezone": "auto",
    "temperature_unit": "fahrenheit",
    "precipitation_unit": "mm"
}

data = requests.get(
    "https://archive-api.open-meteo.com/v1/archive",
    params=params
).json()

high = data["daily"]["temperature_2m_max"][0]
low = data["daily"]["temperature_2m_min"][0]
rain = data["daily"]["precipitation_sum"][0]

humidity = data["hourly"]["relative_humidity_2m"]
avg_humidity = sum(humidity) / len(humidity)

print(f"Date: {date}")
print(f"High: {high:.1f}°F")
print(f"Low: {low:.1f}°F")
print(f"Humidity: {avg_humidity:.1f}%")
print(f"Rainfall: {rain:.1f} mm")

track_condition = "WET" if rain > 0 else "DRY"
print(f"Condition: {track_condition}")