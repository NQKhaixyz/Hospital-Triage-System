# Hệ Thống Quản Lý Khám Bệnh Đa Khoa (Hospital Triage System)

Hệ thống quản lý khám bệnh thông minh sử dụng mô hình **Định tuyến hàng đợi đa cấp (Multilevel Queue Routing)** — khái niệm kinh điển trong lập lịch CPU của hệ điều hành, được áp dụng vào bài toán y tế để tối ưu hóa luồng bệnh nhân và phân bổ bác sĩ một cách hiệu quả.

---

## Mục lục

- [Tổng quan](#tổng-quan)
- [Tính năng chính](#tính-năng-chính)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
  - [Cấu trúc dữ liệu](#cấu-trúc-dữ-liệu)
  - [Các thực thể](#các-thực-thể)
- [Thuật toán định tuyến đa cấp](#thuật-toán-định-tuyến-đa-cấp)
- [Cài đặt](#cài-đặt)
- [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
  - [Chạy hệ thống](#chạy-hệ-thống)
  - [Chạy kiểm thử](#chạy-kiểm-thử)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Chi tiết các module](#chi-tiết-các-module)
  - [hospital_triage.py](#hospital_triagepy)
  - [triage_system.py](#triage_systempy)
  - [billing_system.py](#billing_systempy)
- [Ví dụ minh họa](#ví-dụ-minh-họa)
- [Kết quả kiểm thử](#kết-quả-kiểm-thử)
- [Tác giả](#tác-giả)

---

## Tổng quan

Hệ thống được thiết kế để giải quyết bài toán quản lý khám bệnh trong bệnh viện đa khoa với các yêu cầu phức tạp:

- **Bệnh nhân**: Lưu trữ thông tin cá nhân, triệu chứng, mức độ nguy hiểm
- **Bác sĩ**: Quản lý thông tin, kinh nghiệm, thuộc khoa
- **Khoa**: 5 khoa chuyên môn (Nội tổng quát, Ngoại khoa, Nhi khoa, Sản khoa, Tai mũi họng)
- **Đặt lịch**: Giới hạn 4 bệnh nhân/khung giờ/bác sĩ
- **Ưu tiên**: 3 mức độ ưu tiên (Nguy kịch, Đặt trước, Vãng lai)
- **Tính tiền**: Tự động tính hóa đơn theo dịch vụ y tế
- **Dashboard**: Hiển thị thời gian thực trạng thái toàn bộ hệ thống

---

## Tính năng chính

### 1. Quản lý Bệnh nhân
- Lưu trữ: họ tên, ngày sinh, số điện thoại, địa chỉ, ngày nhập viện, triệu chứng, mức độ nguy hiểm
- Phân loại tự động theo mức độ ưu tiên
- Theo dõi trạng thái: đang chờ, đang khám, đã khám xong, đã thanh toán

### 2. Quản lý Bác sĩ
- Thông tin: họ tên, số điện thoại, số năm kinh nghiệm, thuộc khoa
- Mỗi bác sĩ có hàng đợi riêng cho bệnh nhân đặt lịch
- Theo dõi bệnh nhân đang khám và số bệnh nhân đã khám
- Mối quan hệ nhiều-nhiều: 1 bệnh nhân có thể được nhiều bác sĩ phụ trách

### 3. Quản lý Khoa
- 5 khoa: Nội tổng quát, Ngoại khoa, Nhi khoa, Sản khoa, Tai mũi họng
- Mỗi khoa có nhiều bác sĩ
- Hàng đợi cấp cứu chung cho toàn khoa
- Hàng đợi vãng lai chung cho toàn khoa

### 4. Đặt lịch khám
- Yêu cầu thông tin: họ tên, địa chỉ, số điện thoại, ngày sinh, ngày khám, giờ khám, bác sĩ thăm khám
- Giới hạn: tối đa 4 bệnh nhân trong 1 khung giờ/bác sĩ
- Bệnh nhân đặt lịch được ưu tiên mức 2
- Tự động thêm thông tin từ đơn đăng ký vào hệ thống

### 5. Check-in & Phân luồng thông minh
- **Ưu tiên 1 (Nguy kịch)**: Cảnh báo nguy cấp, khám ngay lập tức
- **Ưu tiên 2 (Đặt trước)**: Chỉ được ưu tiên khám đúng khung giờ đã đăng ký
- **Ưu tiên 3 (Vãng lai)**: Không chọn bác sĩ, ai rảnh thì khám
- **Xử lý trễ giờ**: Bệnh nhân đặt lịch đến trễ >15 phút tự động hạ xuống hàng đợi vãng lai
- **Lấp slot trống**: Nếu không có bệnh nhân đặt lịch hoặc chưa tới giờ, đẩy bệnh nhân vãng lai lên trước

### 6. Thuật toán Định tuyến Đa cấp
Khi bác sĩ nhấn "Đã khám xong", hệ thống tự động chọn bệnh nhân tiếp theo theo thứ tự:
1. **Ưu tiên 1**: Hàng đợi cấp cứu của khoa
2. **Ưu tiên 2**: Hàng đợi đặt trước của bác sĩ (đúng khung giờ)
3. **Ưu tiên 3**: Hàng đợi vãng lai của khoa

### 7. Cơ chế Aging (Chống đói)
- Bệnh nhân vãng lai chờ quá lâu (>120 phút) tự động thăng cấp lên ưu tiên 2
- Nếu tiếp tục chờ (>180 phút) tự động lên ưu tiên 1 (cấp cứu)
- Đảm bảo không có bệnh nhân nào bị bỏ quên

### 8. Dashboard thời gian thực
- Hiển thị STT bệnh nhân đang được mỗi bác sĩ khám tại mỗi phòng khoa
- Trạng thái bác sĩ: đang bận / đang rảnh
- Số lượng bệnh nhân chờ trong từng hàng đợi
- Bệnh nhân cấp cứu đang chờ

### 9. Hệ thống Tính tiền (Billing)
- Tự động tính hóa đơn sau khi bác sĩ khám xong
- Danh mục dịch vụ: khám, cấp cứu, xét nghiệm, X-quang, siêu âm, phẫu thuật, thuốc
- Theo dõi doanh thu theo khoa và toàn bệnh viện
- Đánh dấu đã thanh toán

### 10. Đồng hồ ảo (Virtual Clock)
- Mô phỏng thời gian thực để kiểm thử
- Tick từng khung giờ (15 phút/lần)
- Kiểm tra khung giờ khám, xử lý trễ giờ

---

## Kiến trúc hệ thống

### Cấu trúc dữ liệu

| Thành phần | Cấu trúc dữ liệu | Lý do sử dụng | Độ phức tạp |
|------------|------------------|---------------|-------------|
| Tra cứu nhanh | Hash Table (dict) | Tra cứu bệnh nhân, bác sĩ, khoa, lịch hẹn | O(1) |
| Hàng đợi Ưu tiên 1 (Nguy kịch) | Deque | Xử lý ngay lập tức, thêm/lấy O(1) | O(1) |
| Hàng đợi Ưu tiên 2 (Đặt trước) | Deque | Gắn với từng bác sĩ, đúng khung giờ | O(1) |
| Hàng đợi Ưu tiên 3 (Vãng lai) | Deque | Gắn với từng khoa, FIFO | O(1) |
| Quan hệ Bác sĩ-Bệnh nhân | Adjacency List | Lưu trữ quan hệ nhiều-nhiều | O(1) |
| Giới hạn Slot | Hash Map Counter | Key = (DoctorID, Date, TimeSlot) | O(1) |

### Các thực thể

```
Patient
├── id, name, dob, phone, address
├── admission_date, symptoms, danger_level
├── is_booked, ticket_number
├── appointment_time, assigned_doctor_id
└── status (waiting, in_exam, completed, billed)

Doctor
├── id, name, phone, experience_years, department_id
├── booked_queue (Deque - Priority 2)
├── current_patient_id
└── max_slots_per_hour = 4

Department
├── id, name
├── doctor_ids (Set)
├── emergency_queue (Deque - Priority 1)
└── walk_in_queue (Deque - Priority 3)

TriageSystem
├── patients: Dict[id, Patient]
├── doctors: Dict[id, Doctor]
├── departments: Dict[id, Department]
├── doctor_patient_graph: Dict[doctor_id, Set[patient_ids]]
├── patient_doctor_graph: Dict[patient_id, Set[doctor_ids]]
├── appointment_slots: Dict[(date, time_slot, doctor_id), count]
└── scheduled_appointments: Dict[(date, time_slot, doctor_id), List[patient_ids]]
```

---

## Thuật toán định tuyến đa cấp

```
Khi Bác sĩ D (thuộc khoa Dept_X) nhấn "Đã khám xong":

1. Lưu quan hệ bác sĩ-bệnh nhân vào đồ thị nhiều-nhiều

2. Tìm bệnh nhân tiếp theo:
   
   Bước 1: Kiểm tra emergency_queue của Dept_X
   ├── Nếu có: Lấy bệnh nhân đầu tiên (popleft)
   └── Nếu không: Chuyển Bước 2
   
   Bước 2: Kiểm tra booked_queue của bác sĩ D
   ├── Nếu có và đúng khung giờ: Lấy bệnh nhân đầu tiên
   └── Nếu không có hoặc chưa đến giờ: Chuyển Bước 3
   
   Bước 3: Kiểm tra walk_in_queue của Dept_X
   ├── Nếu có: Lấy bệnh nhân đầu tiên (FIFO)
   └── Nếu không: Bác sĩ ở trạng thái rảnh (Idle)

3. Cập nhật trạng thái bác sĩ và bệnh nhân
```

---

## Cài đặt

### Yêu cầu hệ thống
- Python 3.8+
- Không cần cài đặt thêm thư viện ngoài (chỉ dùng thư viện chuẩn Python)

### Cài đặt
```bash
# Clone hoặc tải mã nguồn về máy
git clone <repository-url>

# Di chuyển vào thư mục dự án
cd hospital-triage-system
```

---

## Hướng dẫn sử dụng

### Chạy hệ thống

```bash
# Chạy hệ thống chính với đầy đủ tính năng và kiểm thử
python hospital_triage.py
```

### Chạy kiểm thử riêng lẻ

```bash
# Kiểm thử module Triage System (check-in, định tuyến, hàng đợi)
python triage_system.py

# Kiểm thử module Billing System (tính tiền, doanh thu)
python billing_system.py
```

### Kết quả kiểm thử mong đợi

```
################################################################################
# HOSPITAL TRIAGE SYSTEM - COMPREHENSIVE TEST SUITE
################################################################################

[OK] PASS: Test 1: Appointments (5/5 booked, slot limit respected)
[OK] PASS: Test 2: Check-in (Queue correctly sorted by priority)
[OK] PASS: Test 3: Examinations (Multilevel queue routing works)
[OK] PASS: Test 4: Emergency Priority (Priority 1 always first)
[OK] PASS: Test 5: Walk-in (Walk-in patients fill empty slots)
[OK] PASS: Test 6: Late Demotion (Priority 2 -> 3 after >15 min late)
[OK] PASS: Test 7: Billing (Bill generated correctly)
[OK] PASS: Test 8: Dashboard (Real-time display working)

Total: 8/8 tests passed
```

---

## Cấu trúc dự án

```
hospital-triage-system/
├── hospital_triage.py      # Hệ thống chính + Demo + Dashboard + Virtual Clock
├── triage_system.py        # Core Triage System (Đặt lịch, Check-in, Định tuyến)
├── billing_system.py       # Hệ thống tính tiền (Bill, Revenue tracking)
├── README.md               # Tài liệu này
└── .gitignore              # (Tùy chọn)
```

---

## Chi tiết các module

### hospital_triage.py
**Chức năng**: Hệ thống chính tích hợp toàn bộ luồng nghiệp vụ

**Các class chính**:
- `VirtualClock`: Đồng hồ ảo để mô phỏng thời gian
- `Patient`: Thực thể bệnh nhân với độ ưu tiên
- `Doctor`: Thực thể bác sĩ với hàng đợi lịch hẹn
- `Department`: Khoa với hàng đợi chung
- `HospitalTriageSystem`: Hệ thống tổng quản lý toàn bộ
- `DemoScenario`: 8 bài kiểm thử toàn diện

**Luồng hoạt động**:
1. Khởi tạo 5 khoa + 2 bác sĩ/khoa
2. Tạo bệnh nhân và đặt lịch khám
3. Check-in với phân loại ưu tiên
4. Bác sĩ khám và nhấn "đã khám xong"
5. Hệ thống tự động đưa bệnh nhân tiếp theo vào
6. Tính hóa đơn sau khám xong
7. Hiển thị Dashboard thời gian thực

### triage_system.py
**Chức năng**: Cấu trúc dữ liệu cốt lõi và thuật toán định tuyến

**Các class chính**:
- `Patient`: Thông tin bệnh nhân cơ bản
- `Doctor`: Bác sĩ với hàng đợi đặt trước
- `Department`: Khoa với các hàng đợi (emergency, walk-in, priority)
- `TriageSystem`: Quản lý định tuyến đa cấp và quan hệ đồ thị

**Các phương thức quan trọng**:
- `book_appointment()`: Đặt lịch với giới hạn slot
- `check_in_patient()`: Check-in với phân loại ưu tiên
- `next_patient_for_doctor()`: Thuật toán định tuyến đa cấp
- `complete_examination()`: Hoàn thành khám và lấy bệnh nhân tiếp theo
- `promote_waited_patients()`: Cơ chế Aging (chống đói)

### billing_system.py
**Chức năng**: Quản lý hóa đơn và doanh thu

**Các class chính**:
- `Bill`: Hóa đơn với danh sách dịch vụ
- `BillingSystem`: Quản lý tất cả hóa đơn
- `TriageSystem`: Tích hợp billing với hệ thống khám bệnh

**Danh mục dịch vụ**:
| Dịch vụ | Giá (VNĐ) |
|---------|-----------|
| Khám bệnh (consultation) | 200.000 |
| Cấp cứu (emergency_care) | 500.000 |
| Xét nghiệm máu (blood_test) | 150.000 |
| X-quang (xray) | 300.000 |
| Siêu âm (ultrasound) | 400.000 |
| Phẫu thuật (surgery) | 2.000.000 |
| Thuốc (prescription) | 50.000 |

---

## Ví dụ minh họa

### Ví dụ 1: Đặt lịch khám

```python
from hospital_triage import *

# Khởi tạo hệ thống
clock = VirtualClock(datetime(2024, 1, 15, 8, 0, 0))
system = HospitalTriageSystem(clock)

# Tạo khoa và bác sĩ
system.add_department("Noi tong quat")
doctor = Doctor(id="D001", name="Dr. Nguyen", department="Noi tong quat")
system.add_doctor(doctor)

# Đăng ký bệnh nhân
patient = Patient(id="P001", name="Tran Van A", priority=3)
system.register_patient(patient)

# Đặt lịch khám lúc 09:00
system.book_appointment("P001", "D001", "09:00")
# Kết quả: True (đặt thành công)
```

### Ví dụ 2: Check-in đa mức ưu tiên

```python
# Check-in bệnh nhân nguy kịch (ưu tiên 1)
emergency_patient = Patient(id="P002", name="Nguyen Thi B", priority=1)
system.register_patient(emergency_patient)
system.check_in_patient("P002", "Noi tong quat")
# Bệnh nhân được đưa vào hàng đợi cấp cứu

# Check-in bệnh nhân đặt lịch (ưu tiên 2)
booked_patient = Patient(id="P003", name="Le Van C", priority=2)
booked_patient.appointment_time = clock.get_time()
system.register_patient(booked_patient)
system.check_in_patient("P003", "Noi tong quat")

# Check-in bệnh nhân vãng lai (ưu tiên 3)
walk_in_patient = Patient(id="P004", name="Pham Thi D", priority=3)
system.register_patient(walk_in_patient)
system.check_in_patient("P004", "Noi tong quat")
```

### Ví dụ 3: Bác sĩ khám và định tuyến tự động

```python
# Bác sĩ khám bệnh nhân hiện tại xong
# Hệ thống tự động chọn bệnh nhân tiếp theo theo thứ tự:
# 1. Cấp cứu → 2. Đặt trước → 3. Vãng lai

completed_patient = system.complete_examination("D001")
# Kết quả: Bệnh nhân nguy kịch (P002) được khám trước
```

### Ví dụ 4: Tính hóa đơn

```python
# Sau khi khám xong, tạo hóa đơn
services = ["examination", "blood_test", "prescription"]
bill = system.generate_bill("P001", services)

print(f"Tổng tiền: ${bill.amount}")
# Kết quả: $260.00 (100 + 80 + 30)
```

### Ví dụ 5: Dashboard thời gian thực

```python
# Hiển thị trạng thái toàn bộ hệ thống
print_dashboard(system, clock)

# Kết quả:
# ================================================================================
# HOSPITAL DASHBOARD - 10:15
# ================================================================================
# NOI TONG QUAT
# ----------------------------------------
# Doctors:
#   Dr. Nguyen: [RED] Busy - Examining Tran Van A
#   Dr. Tran: [GREEN] Available
# Queue: 2 patients waiting
#   - Nguyen Thi B (Priority 1: EMERGENCY)
#   - Le Van C (Priority 2: URGENT)
# ...
```

---

## Kết quả kiểm thử

### Test Suite đầy đủ (8 tests)

| Test | Mô tả | Kết quả |
|------|-------|---------|
| Test 1 | Booking Appointments & Slot Limit | PASS |
| Test 2 | Check-in with Priority Levels | PASS |
| Test 3 | Examination & Multilevel Queue Routing | PASS |
| Test 4 | Emergency Priority (Always First) | PASS |
| Test 5 | Walk-in Patients Fill Empty Slots | PASS |
| Test 6 | Late Patient Demotion (2→3) | PASS |
| Test 7 | Billing Generation | PASS |
| Test 8 | Real-time Dashboard | PASS |

**Tổng kết: 8/8 tests passed**

### Các trường hợp kiểm thử chi tiết

#### Test 1: Giới hạn slot đặt lịch
- Book 4 lịch hẹn với cùng 1 bác sĩ tại 10:00 → Thành công
- Book lịch thứ 5 → Từ chối (đã đạt giới hạn 4)

#### Test 2: Phân loại ưu tiên khi check-in
- Ưu tiên 1: Vào hàng đợi cấp cứu
- Ưu tiên 2: Vào hàng đợi đặt trước của bác sĩ
- Ưu tiên 3: Vào hàng đợi vãng lai

#### Test 3: Định tuyến đa cấp
- Khi bác sĩ khám xong, luôn lấy bệnh nhân cấp cứu trước
- Sau đó đến bệnh nhân đặt lịch đúng giờ
- Cuối cùng là bệnh nhân vãng lai

#### Test 4: Ưu tiên cấp cứu
- Thêm bệnh nhân thường vào hàng đợi trước
- Thêm bệnh nhân cấp cứu sau
- Khi phân bổ bác sĩ: cấp cứu luôn được khám trước

#### Test 5: Lấp slot trống
- Khi không có bệnh nhân đặt lịch, bệnh nhân vãng lai tự động được đưa vào
- Tối ưu hóa thời gian rảnh của bác sĩ

#### Test 6: Xử lý trễ giờ
- Bệnh nhân đặt lịch nhưng đến trễ >15 phút
- Tự động hạ xuống hàng đợi vãng lai (Priority 2 → 3)

#### Test 7: Tính hóa đơn
- Tạo hóa đơn với các dịch vụ: examination, blood_test, prescription
- Tổng tiền tính đúng: $260.00

#### Test 8: Dashboard
- Hiển thị đúng trạng thái tất cả bác sĩ (bận/rảnh)
- Hiển thị đúng số bệnh nhân trong từng hàng đợi
- Hiển thị đúng bệnh nhân cấp cứu

---

## Các điểm nổi bật về mặt kỹ thuật

### 1. Áp dụng thuật toán Hệ điều hành
- **Multilevel Queue Scheduling**: Lập lịch CPU trong hệ điều hành được áp dụng vào quản lý khám bệnh
- **Aging**: Chống đói (starvation) cho bệnh nhân vãng lai

### 2. Cấu trúc dữ liệu tối ưu
- Sử dụng Hash Table (dict) cho tra cứu O(1)
- Deque cho hàng đợi với thao tác hai đầu O(1)
- Đồ thị vô hướng (Adjacency List) cho quan hệ nhiều-nhiều

### 3. Xử lý Edge Cases
- Bệnh nhân đặt lịch nhưng đến trễ
- Bệnh nhân vãng lai chờ quá lâu
- Không có bác sĩ rảnh trong khoa
- Slot đặt lịch đã đầy

### 4. Thiết kế Module hóa
- Tách biệt rõ ràng giữa các module: Core, Billing, Demo
- Dễ dàng mở rộng và bảo trì
- Có thể tích hợp thêm giao diện web hoặc mobile

---

## Hướng phát triển tiếp theo

1. **Giao diện người dùng (GUI/Web)**: Xây dựng frontend để dễ sử dụng
2. **Cơ sở dữ liệu**: Tích hợp SQLite/PostgreSQL để lưu trữ lâu dài
3. **API RESTful**: Xây dựng API để tích hợp với các hệ thống khác
4. **Thông báo tự động**: Gửi SMS/Email nhắc lịch khám
5. **Báo cáo thống kê**: Doanh thu, số lượng bệnh nhân, hiệu suất bác sĩ
6. **Machine Learning**: Dự đoán thời gian chờ và tối ưu lịch khám

---

## Tác giả

**Dự án được phát triển bởi:** Sinh viên Kỹ thuật Máy tính

**Mục tiêu:** Ứng dụng các khái niệm cấu trúc dữ liệu và thuật toán (Hash Table, Deque, Graph, Multilevel Queue Scheduling) vào bài toán thực tế trong lĩnh vực y tế.

**Công nghệ sử dụng:** Python 3, thư viện chuẩn (collections, datetime, typing, dataclasses)

---

## Giấy phép

Dự án này được phát triển cho mục đích học tập và nghiên cứu.

---

*README.md được tạo tự động cho Hệ thống Quản lý Khám bệnh Đa khoa.*
