import uvicorn
import os
import logging
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 환경 변수 로드
load_dotenv()

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    print(f"서버 시작 중... http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=True, log_level="debug") 