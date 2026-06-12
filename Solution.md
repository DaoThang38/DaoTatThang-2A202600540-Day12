# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. Hardcode API Keys (Secret keys lộ trong code)
2. Chạy debug mode `debug=True` trong production
3. Cố định port (hardcode port thay vì dùng biến môi trường PORT)
4. Thiếu endpoint Health Check để orchestration platform (Docker/K8s) kiểm tra
5. Không có cơ chế Graceful Shutdown (dễ làm mất dữ liệu request khi bị tắt ngang)

### Exercise 1.3: Comparison table
| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config  | Hardcode | Env vars | Bảo mật thông tin nhạy cảm, dễ cấu hình giữa các môi trường |
| Health check | Không có | Có (/health, /ready) | Giúp Load Balancer/Orchestrator biết container sống/sẵn sàng nhận traffic |
| Logging | `print()` | Structured JSON logging | Dễ phân tích, parse log tập trung (ELK, Datadog) |
| Shutdown | Đột ngột | Graceful Shutdown | Đảm bảo các request đang dở dang được hoàn thành, không mất data |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image: `python:3.11-slim` (hoặc alpine tuỳ bản).
2. Working directory: `/app`
3. Tại sao COPY requirements.txt trước?: Để tận dụng Docker layer caching. Nếu requirements không đổi, Docker không cần cài lại package.
4. CMD vs ENTRYPOINT: `CMD` có thể bị override dễ dàng ở command line, trong khi `ENTRYPOINT` quy định executable chính của container.

### Exercise 2.3: Image size comparison
- Develop (python standard): ~1GB
- Production (python slim + multi-stage): ~150-300MB
- Difference: ~70-85% (Giảm đáng kể thời gian pull/push, tiết kiệm chi phí lưu trữ)

## Part 3: Cloud Deployment

### Exercise 3.1: Deployment
- URL: https://daotatthang-2a202600540-day12-production.up.railway.app
- Screenshot: Xem thư mục `screenshots/`

## Part 4: API Security

### Exercise 4.1-4.3: Test results
- Unauthorized Test (Không có Key): Trả về `401 Unauthorized`.
- Authorized Test (Có Key): Trả về `200 OK`.
- Rate Limiting Test: Sau 10 request liên tiếp, hệ thống trả về `429 Too Many Requests`.

### Exercise 4.4: Cost guard implementation
- Approach: Sử dụng Redis để lưu trạng thái chi phí `budget:{user_id}:{month_key}`. Mỗi khi có request, tăng biến đếm `estimated_cost`. Nếu `current_cost + estimated_cost > 10`, từ chối request. Reset vào đầu tháng kế tiếp nhờ Redis `expire` (32 ngày).

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
- Health Checks: `/health` (liveness) và `/ready` (readiness).
- Graceful Shutdown: Bắt signal `SIGTERM` và `SIGINT`.
- Stateless design: Gỡ bỏ biến trạng thái in-memory (`conversation_history = {}`), chuyển sang lưu lịch sử hội thoại vào Redis. Giúp dễ dàng scale up nhiều replica phía sau Load Balancer.
- Load Balancing: Có thể scale replicas bằng docker-compose scale và chia traffic qua nginx hoặc Traefik.
