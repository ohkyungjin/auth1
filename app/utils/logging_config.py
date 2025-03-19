import logging
import logging.config
import json
import os
from datetime import datetime
import traceback
from pathlib import Path

class StructuredJsonFormatter(logging.Formatter):
    """구조화된 JSON 형식으로 로그를 출력하는 포매터"""
    
    def __init__(self, fmt=None, datefmt=None, style='%', include_stack_info=False):
        super().__init__(fmt, datefmt, style)
        self.include_stack_info = include_stack_info
        
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 예외 정보 추가
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        # 스택 정보 추가 (선택적)
        if self.include_stack_info and record.stack_info:
            log_data["stack_info"] = record.stack_info
            
        # 추가 속성 처리
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", 
                          "filename", "funcName", "id", "levelname", "levelno", 
                          "lineno", "module", "msecs", "message", "msg", "name", 
                          "pathname", "process", "processName", "relativeCreated", 
                          "stack_info", "thread", "threadName"]:
                log_data[key] = value
                
        return json.dumps(log_data)

def setup_logging(log_level=logging.INFO, log_dir="logs"):
    """로깅 설정 함수"""
    # 로그 디렉토리 생성
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True, parents=True)
    
    # 현재 날짜로 로그 파일명 생성
    today = datetime.now().strftime("%Y%m%d")
    log_file = log_path / f"stock_api_{today}.log"
    error_log_file = log_path / f"stock_api_error_{today}.log"
    
    # 로깅 설정
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s"
            },
            "json": {
                "()": StructuredJsonFormatter,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filename": str(log_file),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filename": str(error_log_file),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8"
            }
        },
        "loggers": {
            "": {  # 루트 로거 설정
                "handlers": ["console", "file", "error_file"],
                "level": log_level,
                "propagate": True
            },
            "app": {
                "handlers": ["console", "file", "error_file"],
                "level": log_level,
                "propagate": False
            },
            "httpx": {
                "handlers": ["file"],
                "level": "WARNING",
                "propagate": False
            }
        }
    }
    
    # 로깅 설정 적용
    logging.config.dictConfig(config)
    
    logging.info(f"로깅 시스템 초기화 완료 (레벨: {logging.getLevelName(log_level)})")
    return logging.getLogger("app") 