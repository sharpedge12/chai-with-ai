import requests

BOT_TOKEN = "8215582690:AAEY_b-jsBhIS1GVT5-LcVEclVJI0mwktsQ"
CHAT_ID = "1254971535"
MESSAGE = "beep boop , ai will take over this world"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

payload = {
    "chat_id": CHAT_ID,
    "text": MESSAGE
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    print("Message sent successfully!")
else:
    print("Failed to send message")
    print(response.text)
