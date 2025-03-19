import uvicorn
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    print(f"서버 시작 중... http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=True) 