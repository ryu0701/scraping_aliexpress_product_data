import requests

url = "https://aliexpress-datahub.p.rapidapi.com/item_detail"

querystring = {"itemId":"1005005793490686","currency":"JPY"}

headers = {
	"X-RapidAPI-Key": "0d604a6fcdmsh916e02f7cd9c601p1fef00jsn85951b610d94",
	"X-RapidAPI-Host": "aliexpress-datahub.p.rapidapi.com"
}

response = requests.get(url, headers=headers, params=querystring)

print(response.json())