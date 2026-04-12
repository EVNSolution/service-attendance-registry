# service-attendance-registry

이 repo는 CLEVER MSA의 `기사 x 일자` 근태 truth를 소유하는 Django/DRF runtime repo다.

현재 역할:
- `attendance-registry-api` runtime
- dispatch-derived attendance signal sync
- daily attendance truth 조회와 internal bulk lookup

소유 범위:
- `AttendanceDay`
- `AttendanceSignal`
- `dispatch -> attendance` 해석 규칙

소유하지 않는 것:
- dispatch plan / upload preview truth
- delivery raw record / daily snapshot
- settlement run / settlement item / payout status

phase 1 current truth:
- active source는 `dispatch` 하나만 둔다
- `00 + zero workload`는 `day_off`
- `00 + positive workload`는 `exception`
- downstream은 `final_status`를 읽어 각자 exclusion rule을 적용한다

로컬 실행:
- `. .venv/bin/activate && python manage.py runserver 0.0.0.0:8000`
- `. .venv/bin/activate && python manage.py test -v 2`

정본 문서:
- 플랫폼 경계와 rollout 정본은 `../../docs/` 아래 문서를 따른다.
