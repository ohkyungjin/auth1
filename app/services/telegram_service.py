import asyncio
import logging
from telegram import Bot
from app.core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

class TelegramService:
    """텔레그램 알림 서비스"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token) if self.token else None
        
    async def send_message(self, message):
        """텔레그램으로 메시지 전송"""
        if not self.bot or not self.chat_id:
            logger.warning("텔레그램 설정이 완료되지 않았습니다.")
            return False
            
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
            logger.info(f"텔레그램 알림 전송 성공: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"텔레그램 알림 전송 실패: {str(e)}")
            return False
            
    async def send_data_collection_notification(self, market, data_count, file_path=None):
        """데이터 수집 완료 알림 전송"""
        message = f"""
<b>📊 주식 데이터 수집 완료</b>

- 시장: <b>{market}</b>
- 수집 데이터 수: <b>{data_count:,}개</b>
"""
        if file_path:
            message += f"- 저장 경로: <code>{file_path}</code>"
            
        return await self.send_message(message)
        
    async def send_error_notification(self, error_message):
        """오류 알림 전송"""
        message = f"""
<b>❌ 주식 데이터 수집 오류</b>

<code>{error_message}</code>
"""
        return await self.send_message(message) 