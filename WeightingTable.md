# Thuật toán Sắp xếp Tác vụ bằng Phương trình Trọng số (Task Priority Scoring)

Mô hình toán học tối ưu hóa hiệu suất cá nhân và quản trị dựa trên Phân tích quyết định đa tiêu chí (MCDA), Thuật toán WSJF (Lean) và Ma trận Eisenhower.

## 1. Công thức toán học (Formula)

$$P = (W_I \cdot I + W_U \cdot U + W_R \cdot R + W_B \cdot B + W_A \cdot A) - (W_E \cdot E + W_D \cdot D + W_C \cdot C + W_F \cdot F) + S$$

*Trong đó: Các tiêu chí được chấm từ 1 đến 5. Urgency được điều chỉnh theo thời gian còn lại tới deadline: $U = U_0 + \frac{1}{1 + (h/24)^2}$, với $h$ là số giờ còn lại. Deadline nhập theo định dạng `dd/mm/yyyy HH:MM:SS` và phải ở tương lai.*

## 2. Bảng Trọng số Hệ thống (Weighting Table)

| Nhóm | Ký hiệu | Tiêu chí | Phép toán | Mô tả khoa học | Trọng số ($W$) |
| :--- | :---: | :--- | :---: | :--- | :---: |
| **POSITIVE** | $I$ | Importance | $+$ | Độ quan trọng cốt lõi (Eisenhower Matrix) | **25%** ($0.25$) |
| | $U$ | Urgency | $+$ | Độ khẩn cấp (Mere Urgency Effect) | **20%** ($0.20$) |
| | $R$ | ROI / Value | $+$ | Giá trị/Lợi nhuận đem lại (Lean Economics) | **15%** ($0.15$) |
| | $B$ | Blocking | $+$ | Độ nghẽn cổ chai của hệ thống (Cost of Delay) | **15%** ($0.15$) |
| | $A$ | Alignment | $+$ | Độ đồng bộ với mục tiêu lớn (Analytic Hierarchy Process) | **10%** ($0.10$) |
| **NEGATIVE** | $E$ | Effort | $-$ | Độ phức tạp/Thời gian thực hiện (WSJF) | **5%** ($0.05$) |
| | $D$ | Delegation | $-$ | Khả năng ủy quyền (Ivy Lee Rule) | **5%** ($0.05$) |
| | $C$ | Context | $-$ | Rào cản bối cảnh/Công cụ | **2%** ($0.02$) |
| | $F$ | Fatigue | $-$ | Mức độ hao tổn năng lượng (Decision Fatigue) | **3%** ($0.03$) |
| **SPECIAL** | $S$ | Regret Score | $+$ | Điểm phạt bổ sung nếu trì hoãn | Cộng trực tiếp |

---
*Hướng dẫn thực thi: Tính điểm $P$ cho toàn bộ tác vụ đầu ngày. Sắp xếp giảm dần. Chọn ra tối đa 6 tác vụ có điểm cao nhất để thực hiện theo quy tắc Ivy Lee.*
