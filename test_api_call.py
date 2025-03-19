import requests

# 금일 데이터 수집 API 호출
url = "http://localhost:8000/api/collect/today"
response = requests.post(url)

# 결과 출력
print(f"상태 코드: {response.status_code}")
print(f"응답 내용: {response.text}") 