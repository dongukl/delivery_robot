# metrics_logger.py
# 배달 미션 성능을 측정하고 CSV로 저장하는 클래스
#
# 왜 필요한가?
# - "됐다"로 끝내지 않고 수치로 결과를 보여줄 수 있음
# - DWB vs TEB 플래너 비교, 파라미터 튜닝 결과를 표로 정리 가능
# - 포트폴리오에서 "실험한 것"을 증명할 수 있음

import csv
import time
from pathlib import Path


class MetricsLogger:
    """
    배달 성능을 측정하고 CSV로 저장하는 클래스
    
    측정 항목:
    - 각 목적지별 소요 시간
    - 성공 / 스킵 여부
    - 재시도 횟수
    """

    def __init__(self, logger):
        # ROS2 노드의 logger를 받아서 저장
        self.logger  = logger
        self.records = []  # 측정 결과 리스트

        # 출발 시각 저장 딕셔너리
        # 예: {'B': 1234567890.0, 'C': 1234567900.0}
        self._depart_time = {}

        # CSV 저장 경로
        self.log_path = Path.home() / 'delivery_metrics.csv'

    def record_departure(self, point_id: str):
        """목적지로 출발할 때 호출 — 출발 시각 기록"""
        self._depart_time[point_id] = time.time()
        self.logger.info(f'[측정] {point_id} 출발')

    def record_arrival(self, point_id: str, retry_count: int):
        """목적지 도착 시 호출 — 소요 시간 계산 후 기록"""
        elapsed = time.time() - self._depart_time.get(point_id, time.time())
        self.records.append({
            'point_id':    point_id,
            'result':      'success',
            'duration_sec': round(elapsed, 2),
            'retry_count': retry_count
        })
        self.logger.info(
            f'[측정] {point_id} 도착 — 소요: {elapsed:.1f}초, '
            f'재시도: {retry_count}회')

    def record_skip(self, point_id: str, retry_count: int):
        """최대 재시도 초과로 스킵할 때 호출"""
        self.records.append({
            'point_id':    point_id,
            'result':      'skipped',
            'duration_sec': -1,
            'retry_count': retry_count
        })
        self.logger.warn(f'[측정] {point_id} 스킵 — 재시도: {retry_count}회')

    def save(self):
        """미션 완료 시 CSV로 저장"""
        with open(self.log_path, 'w', newline='') as f:
            writer = csv.DictWriter(
                f, fieldnames=['point_id', 'result', 'duration_sec', 'retry_count'])
            writer.writeheader()
            writer.writerows(self.records)

        self.logger.info(f'[측정] 결과 저장 완료: {self.log_path}')

        # 요약 출력
        success = [r for r in self.records if r['result'] == 'success']
        skipped = [r for r in self.records if r['result'] == 'skipped']
        self.logger.info('=' * 40)
        self.logger.info(f'성공: {len(success)}개 / 스킵: {len(skipped)}개')
        if success:
            avg = sum(r['duration_sec'] for r in success) / len(success)
            self.logger.info(f'평균 소요 시간: {avg:.1f}초')
        self.logger.info('=' * 40)