import rclpy
from rclpy.node import Node
import yaml
import time

from delivery_robot.metrics_logger import MetricsLogger
from delivery_robot.nav2_client import Nav2Client
from delivery_robot.state_machine import StateMachine, DeliveryState

class MissionManager(Node):
    """
    배달 미션 전체를 조율하는 메인 노드
    Nav2Client 와 StateMachine 두개를 연결해서 미션 전체 흐름제어

    흐름: 
    yaml 파일 읽기 -> 목적지 순서대로 Goal 전송 -> 결과에 따라 다음행동
    """

    def __init__(self):
        super().__init__('mission_manager')
        # 파라미터 선언 및 파라미터값 가져오기
        self.declare_parameter('config_path', '')
        config_path = self.get_parameter('config_path').value

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        point_dict = {p['id']: p for p in config['delivery_points']}

        # mission_sequence 순서대로 목표지 리스트 생성
        self.sequence = [point_dict[id] for id in config['mission_sequence']]

        # 재시도 설정값
        self.max_retried = config.get('max_retries', 3)
        self.retry_wait = config.get('retry_wait_sec', 5.0)

        # 내부 변수
        self.current_idx = 0
        self.retry_count = 0

        self.sm = StateMachine(self.get_logger())
        self.nav = Nav2Client(self)
        self.metrics = MetricsLogger(self.get_logger())

        self.timer = self.create_timer(0.5, self.run_loop)

        self.get_logger().info('미션 매니저 시작')
        self.get_logger().info(
            f'총 {len(self.sequence)}개의 목적지: '
            f'{[p["name"] for p in self.sequence]}'
        )

    # 메인 루프
    def run_loop(self):
        state = self.sm.state

        if state == DeliveryState.IDLE:
            if self.current_idx >= len(self.sequence):
                self.sm.transition(DeliveryState.MISSION_DONE)
                return
            # 다음 목적지로 이동
            self._go_to_current()

        elif state == DeliveryState.ARRIVED:
            name = self.sequence[self.current_idx]['name']
            self.get_logger().info(f'도착: {name}')
            self.metrics.record_arrival(          # ← 추가
                self.sequence[self.current_idx]['id'],
                self.retry_count
            )
            self.sm.transition(DeliveryState.WAITING)

            # 3초 대기 >> 배달 전달
            time.sleep(3.0)

            self.current_idx += 1
            self.retry_count = 0
            self.sm.transition(DeliveryState.IDLE)

        elif state == DeliveryState.FAILED:
            if self.retry_count < self.max_retried:
                self.get_logger().warn(
                    f'재시도 {self.retry_count+1} / {self.max_retried}'
                    f'- {self.retry_wait}초 후'
                )
                self.sm.transition(DeliveryState.RECOVERING)
                time.sleep(self.retry_wait)
                self.retry_count += 1
                self._go_to_current()
            else:
                name = self.sequence[self.current_idx]['name']
                self.get_logger().error(
                    f'최대 재시도 초과 - {name}스킵'
                )
                self.metrics.record_skip(             
                    self.sequence[self.current_idx]['id'],
                    self.retry_count
                )    
                self.current_idx += 1
                self.retry_count = 0
                self.sm.transition(DeliveryState.IDLE)

        elif state == DeliveryState.MISSION_DONE:
            self.get_logger().info('=' * 40)
            self.get_logger().info('전체 미션 완료')
            self.metrics.save()
            self.get_logger().info('=' * 40)
            # 타이머 종료
            self.timer.cancel()

    def _go_to_current(self):
        pt = self.sequence[self.current_idx]
        self.get_logger().info(
            f'이동 시작 : {pt["name"]}'
            f'({pt["x"]:.2f}, {pt["y"]:.2f})'
        )
        self.metrics.record_departure(pt['id'])

        self.sm.transition(DeliveryState.MOVING)

        self.nav.send_goal(
            pt['x'], pt['y'], pt['yaw'],
            on_result_callback=self._on_nav_result
        )
    
    def _on_nav_result(self, success: bool):
        if success:
            self.sm.transition(DeliveryState.ARRIVED)
        else:
            self.sm.transition(DeliveryState.FAILED)


def main(args=None):
    rclpy.init(args=args)
    node = MissionManager()

    try:
        rclpy.spin(node)
    
    except KeyboardInterrupt:
        node.get_logger().info('미션 중단')

    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()