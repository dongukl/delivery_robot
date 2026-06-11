import rclpy
from rclpy.node import Node

from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
# 특정 좌표로 이동하라는 명령

from geometry_msgs.msg import PoseStamped
# 목적기 좌표를 담는 메시지 타입

from action_msgs.msg import GoalStatus
import math # yaw -> quaternaion 변환

class Nav2Client(Node):
    def __init__(self):
        super().__init__('nav2_client')
        self._client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        # 'navigate_to_pose' : Nav2 액션 서버 이름 (고정값, 바꾸면 안 됨)

        self._current_goal_handle = None

    def send_goal(self, x:float, y:float, yaw:float, on_result_callback):
        '''
        파라미터
        x, y : 목적지 좌표
        yaw  : 도착시 로봇의 방향
        on_result_callback : 이동 완료/실패 시 호출할 콜백 함수 
        '''

        self.get_logger().info(f'목적지 전송 : x = {x:.2f}, y = {y:.2f}')
        while not self._client.wait_for_server(timeout_sec=1.0):
            self.get_logger().info('Waiting server ...')

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self._make_pose(x, y, yaw)

        send_future = self._client.send_goal_async(
            goal_msg,
            feedback_callback=self._feedback_callback
        )
        send_future.add_done_callback(lambda f: self._goal_response_callback(f, on_result_callback))
    
    def cancle_goal(self):
        if self._current_goal_handle:
            self._current_goal_handle.cancle_goal_async()
            self.get_logger().info('목표 취소 요청')

    def _make_pose(self, x:float, y:float, yaw:float) -> PoseStamped:
        """
        x, y, yaw 값을 PoseStamped 메시지로 변환

        왜 필요한가?
        - Nav2는 좌표를 PoseStamped 형식으로 받음
        - yaw(라디안)를 quaternion으로 변환해야 함
          (ROS2는 방향을 quaternion으로 표현)
        """
         
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y

        pose.pose.orientation.z = math.sin(yaw / 2)
        pose.pose.orientation.w = math.cos(yaw / 2)
        
        return pose
    

    def _goal_response_callback(self, future, on_result_callback):
        """
        Goal 전송 후 Nav2가 수락/거부했는지 확인하는 콜백
        
        Nav2가 거부하는 경우: 목적지가 장애물 안이거나, 경로를 못 찾을 때
        """

        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().warn('Nav2가 목표 거부')
            on_result_callback(success=False)
            return
        
        self._current_goal_handle = goal_handle

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda f: self._result_callback(f, on_result_callback)
        )

    def _result_callback(self, future, on_result_callback):
        status = future.result().status
        success = (status == GoalStatus.STATUS_SUCCEEDED)

        self.get_logger().info(f'주행 결과: {"성공" if success else "실패"} (status={status})')
        on_result_callback(success=success)

    def _feedback_callback(self, feedback_msg):
        dist = feedback_msg.feedback.distance_remaining
        self.get_logger().info(f'남은 거리 : {dist:.2f}m, throttle_duration_sec=2.0')