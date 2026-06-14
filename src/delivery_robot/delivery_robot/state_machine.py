from enum import Enum, auto
# Enum: 이름 있는 상수들의 집합을 만들 때 사용
# 예: 신호등 상태 → RED, YELLOW, GREEN 처럼 정해진 값들만 쓸 때 유용
# auto(): 값을 자동으로 1, 2, 3... 순서로 할당해줌 (직접 숫자 안 써도 됨)

class DeliveryState(Enum):
    """
    배달 로봇의 상태를 정의하는 열거형 클래스
    
    왜 필요한가?
    - 로봇이 지금 뭘 하고 있는지 명확하게 관리하기 위해
    - 문자열("moving", "idle")로 관리하면 오타 위험 있음
    - Enum으로 관리하면 정해진 값만 쓸 수 있어서 안전함
    """

    IDLE            = auto() # 대기중
    MOVING          = auto() # 이동중
    ARRIVED         = auto() # 도착
    WAITING         = auto() # 배달 대기
    FAILED          = auto() # 이동 실패
    RECOVERING      = auto() # 재시도 대기중
    MISSION_DONE    = auto() # 전체 미션 완료


class StateMachine:
    """
    배달 로봇의 상태를 관리하는 클래스

    왜필요한가?
    - 상태 정환능 한 곳에서 관리하면 디버깅 쉬움
    - 상태가 바뀔 때 마다 로그를 자동 출력
    - mission_manager.py가 이 클래스를 사용해서 상태를 바꿈

    """

    def __init__(self, logger):
        self.state = DeliveryState.IDLE
        self.logger = logger


    def transition(self, new_state: DeliveryState):
        # 상태를 변경하는 메서드
        self.logger.info(f'상태 전환: {self.state.name} -> {new_state.name}')
        self.state = new_state

    def is_state(self, state: DeliveryState) -> bool:
        # 현재 상태가 특정 상태인지 확인하는 메서드
        return self.state == state