import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
                           QHeaderView, QLabel)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QColor, QIcon
from PyQt6.QtMultimedia import QSoundEffect
import win32print
import win32ui
from win32con import MM_TEXT
import win32con
import requests
import json
from websockets.sync.client import connect
import threading
import os
import time
import pytz

URL_API = "https://bebien.dzfullstack.com/api"
URL_WS  = "wss://bebien.dzfullstack.com/app/hioxd1v9gttoxqpkmzkb"

# URL_WS  = "ws://127.0.0.1:8080/app/hioxd1v9gttoxqpkmzkb"
# URL_API = "http://127.0.0.1:8000/api"

class WebSocketThread(QThread):
    data_received = pyqtSignal()  # Signal để thông báo cần cập nhật dữ liệu
    play_sound = pyqtSignal()     # Signal để phát âm thanh
    
    def __init__(self):
        super().__init__()
        self.is_running = True
        self.websocket = None
    
    def run(self):
        while self.is_running:
            try:
                with connect(URL_WS) as websocket:
                    self.websocket = websocket
                    print("Đã kết nối tới WebSocket server!")
                    
                    # Đăng ký kênh "in-bep"
                    subscribe_message = {
                        "event": "pusher:subscribe",
                        "data": {
                            "channel": "in-bep"
                        }
                    }
                    websocket.send(json.dumps(subscribe_message))
                    print("Đã đăng ký kênh in-bep")
                    
                    while self.is_running:
                        try:
                            message = websocket.recv()
                            if not self.is_running:  # Kiểm tra lại trước khi xử lý message
                                break
                            data = json.loads(message)
                            if "event" in data and data["event"] == "eventInBep":
                                try:
                                    event_data = json.loads(data["data"])
                                    if event_data.get("data", {}).get("status") == True:
                                        print("Nhận được tín hiệu cập nhật")
                                        self.data_received.emit()  # Cập nhật dữ liệu trước
                                        self.play_sound.emit()    # Phát âm thanh sau
                                except json.JSONDecodeError:
                                    print("Lỗi parse JSON từ event data")
                            
                        except Exception as e:
                            if not self.is_running:  # Không in lỗi nếu đang tắt thread
                                break
                            print(f"Lỗi khi nhận dữ liệu: {str(e)}")
                            break
                            
            except Exception as e:
                if not self.is_running:  # Không in lỗi nếu đang tắt thread
                    break
                print(f"Lỗi kết nối WebSocket: {str(e)}")
                
            if self.is_running:
                print("Đang thử kết nối lại sau 5 giây...")
                import time
                time.sleep(5)
    
    def stop(self):
        """Dừng WebSocket thread một cách an toàn"""
        self.is_running = False
        if self.websocket:
            try:
                # Gửi message unsubscribe trước khi đóng
                unsubscribe_message = {
                    "event": "pusher:unsubscribe",
                    "data": {
                        "channel": "in-bep"
                    }
                }
                self.websocket.send(json.dumps(unsubscribe_message))
                self.websocket.close()
            except:
                pass  # Bỏ qua lỗi khi đóng websocket
        self.websocket = None

class IPCheckThread(QThread):
    def __init__(self):
        super().__init__()
        self.is_running = True
        
    def run(self):
        while self.is_running:
            try:
                # Lấy IP public
                response = requests.get('https://api.ipify.org?format=json')
                if response.status_code == 200:
                    ip_data = response.json()
                    public_ip = ip_data['ip']
                    
                    # Gửi IP lên API
                    response = requests.post(
                        f"{URL_API}/bep/set-ip",
                        json={"ip": public_ip},
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        print(f"Đã cập nhật IP public: {public_ip}")
                    else:
                        print(f"Lỗi khi gửi IP lên API: {response.status_code}")
                        
            except Exception as e:
                print(f"Lỗi khi kiểm tra IP: {str(e)}")
            
            # Chờ 3 phút
            for _ in range(180):  # 3 phút = 180 giây
                if not self.is_running:
                    break
                time.sleep(1)
    
    def stop(self):
        self.is_running = False

class OrderManagementWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quản Lý Đơn Món")
        
        # Khởi tạo âm thanh
        self.sound_effect = QSoundEffect()
        sound_path = os.path.join(os.path.dirname(__file__), "notification.wav")
        self.sound_effect.setSource(QUrl.fromLocalFile(sound_path))
        self.sound_effect.setVolume(1.0)
        
        # Thêm icon cho ứng dụng
        app_icon = QIcon("icon.ico")  # Thay "icon.ico" bằng đường dẫn đến file .ico của bạn
        self.setWindowIcon(app_icon)
        
        self.mon_an_theo_ban = []
        
        # Khởi tạo WebSocket thread
        self.ws_thread = WebSocketThread()
        self.ws_thread.data_received.connect(self.update_data)
        self.ws_thread.play_sound.connect(self.play_notification_sound)
        self.ws_thread.start()
        
        # Khởi tạo IP check thread
        self.ip_thread = IPCheckThread()
        self.ip_thread.start()
        
        # Khởi tạo timer để cập nhật thời gian chờ
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_waiting_time)
        self.update_timer.start(30000)  # 30000ms = 30 giây
        
        self.resize(1200, 700)
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Bảng bên trái
        self.left_table = QTableWidget()
        self.left_table.setColumnCount(6)
        
        # Thiết lập font cho header
        header_font = QFont("Arial", 11, QFont.Weight.ExtraBold)  # Tăng size và độ đậm
        self.left_table.horizontalHeader().setFont(header_font)
        self.left_table.setHorizontalHeaderLabels(["TÊN MÓN ĂN", "SỐ LƯỢNG", "CHẾ BIẾN", "TÊN BÀN", "THỜI GIAN", "ACTION"])
        
        # Ẩn cột STT bên trái
        self.left_table.verticalHeader().setVisible(False)
        
        # Thiết lập chiều cao hàng và căn giữa cột số lượng
        self.left_table.verticalHeader().setDefaultSectionSize(35)  # Giảm chiều cao hàng
        self.left_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Vô hiệu hóa khả năng edit và select
        self.left_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.left_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.left_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        
        left_layout.addWidget(self.left_table)
        
        # Layout bên phải - Đơn món theo nhóm
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Bảng bên phải
        self.right_table = QTableWidget()
        self.right_table.setColumnCount(4)
        
        # Thiết lập font cho header bảng phải
        self.right_table.horizontalHeader().setFont(header_font)
        self.right_table.setHorizontalHeaderLabels(["TÊN MÓN", "SỐ LƯỢNG", "BÀN", "ACTION"])
        
        # Ẩn cột STT bên phải
        self.right_table.verticalHeader().setVisible(False)
        
        # Thiết lập chiều cao hàng và căn giữa cột số lượng
        self.right_table.verticalHeader().setDefaultSectionSize(35)  # Giảm chiều cao hàng
        self.right_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Vô hiệu hóa khả năng edit và select cho bảng bên phải
        self.right_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.right_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.right_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        
        right_layout.addWidget(self.right_table)
        
        # Thêm các widget vào layout chính
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)
        
        # Thiết lập style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QTableWidget::item {
                padding: 3px;
                padding-left: 15px;  /* Tăng padding bên trái cho tất cả các item */
                font-size: 15pt;  /* Tăng kích thước chữ trong item */
            }
            QHeaderView::section {
                background-color: #0078D7;
                color: white;
                padding: 5px;
                border: none;
                font-weight: bold;  /* In đậm title cột */
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 3px 8px;  /* Giảm padding */
                border-radius: 3px;
                min-height: 22px;  /* Giảm chiều cao tối thiểu */
                max-height: 22px;  /* Giảm chiều cao tối đa */
                font-weight: bold;  /* In đậm chữ trong button */
                font-size: 10pt;  /* Điều chỉnh cỡ chữ trong button */
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QLabel {
                color: #333;
                margin: 10px 0;
            }
        """)
        
        # Khởi tạo dữ liệu ban đầu
        self.update_data()
        
    def chia_van_ban_thanh_dong(self, dc, van_ban, max_width):
        """
        Chia văn bản thành các dòng phù hợp với chiều rộng tối đa
        """
        if not van_ban:
            return [""]
        
        if dc.GetTextExtent(van_ban)[0] <= max_width:
            return [van_ban]
        
        cac_tu = van_ban.split()
        cac_dong = []
        dong_hien_tai = ""
        
        for tu in cac_tu:
            dong_kiem_tra = dong_hien_tai + " " + tu if dong_hien_tai else tu
            
            if dc.GetTextExtent(dong_kiem_tra)[0] <= max_width:
                dong_hien_tai = dong_kiem_tra
            else:
                if dong_hien_tai:
                    cac_dong.append(dong_hien_tai)
                
                if dc.GetTextExtent(tu)[0] <= max_width:
                    dong_hien_tai = tu
                else:
                    tu_tam = ""
                    for ky_tu in tu:
                        if dc.GetTextExtent(tu_tam + ky_tu)[0] <= max_width:
                            tu_tam += ky_tu
                        else:
                            cac_dong.append(tu_tam)
                            tu_tam = ky_tu
                    
                    if tu_tam:
                        dong_hien_tai = tu_tam
        
        if dong_hien_tai:
            cac_dong.append(dong_hien_tai)
        
        return cac_dong

    def in_hoa_don_may_mac_dinh(self, so_ban, mon_an):
        """In hóa đơn cho một món ăn cụ thể của một bàn"""
        try:
            may_in_mac_dinh = win32print.GetDefaultPrinter()
            hprinter = win32print.OpenPrinter(may_in_mac_dinh)
            printer_info = win32print.GetPrinter(hprinter, 2)
            dc = win32ui.CreateDC()
            dc.CreatePrinterDC(may_in_mac_dinh)
            dc.StartDoc('Hóa đơn')
            dc.StartPage()
            
            page_width = dc.GetDeviceCaps(win32con.PHYSICALWIDTH)
            page_height = dc.GetDeviceCaps(win32con.PHYSICALHEIGHT)
            
            dc.SetMapMode(MM_TEXT)
            
            # Font cho tất cả nội dung (cùng cỡ chữ)
            font_chung = win32ui.CreateFont({
                "name": "Arial",
                "height": 56,  # Cỡ chữ lớn và đồng nhất
                "weight": 700,  # In đậm
            })
            
            x_start = int(page_width * 0.1)
            y_current = 15 
            
            dc.SelectObject(font_chung)
            
            for mon in mon_an:
                ban_text = f"{mon['ten_ban']}"
                sl_text = f"SL: {mon['so_luong']}"
                ban_width = dc.GetTextExtent(ban_text)[0]
                x_sl = x_start + ban_width + 100 
                
                dc.TextOut(x_start, y_current, ban_text)
                dc.TextOut(x_sl, y_current, sl_text)
                y_current += 85 
                dc.TextOut(x_start, y_current, mon['ten_mat_hang'])
                y_current += 200 
            
            dc.EndPage()
            dc.EndDoc()
            
            win32print.ClosePrinter(hprinter)
            return True
            
        except Exception as e:
            return False

    def call_api_xong_mon_theo_ban(self, mon_id):
        """Gọi API xong món theo bàn"""
        try:
            response = requests.post(
                f"{URL_API}/bep/xong-mon-theo-ban",
                json={"id": mon_id},
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                return True
            else:
                print(response.json())
                print(f"Lỗi khi cập nhật trạng thái món {mon_id}: {response.status_code}")
                return False
        except Exception as e:
            print(f"Lỗi khi gọi API xong món theo bàn: {str(e)}")
            return False

    def call_api_xong_mon_theo_nhom(self, list_id):
        """Gọi API xong món theo nhóm"""
        try:
            # Chuyển chuỗi id thành list
            list_id = [int(id.strip()) for id in list_id.split(',')]
            response = requests.post(
                f"{URL_API}/bep/xong-mon-theo-nhom",
                json={"list_id": list_id},
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                return True
            else:
                print(f"Lỗi khi cập nhật trạng thái các món: {response.status_code}")
                return False
        except Exception as e:
            return False

    def print_order(self, ban, mon_an):
        """In hóa đơn cho một món ăn cụ thể của một bàn"""
        try:
            # Gọi API trước
            if self.call_api_xong_mon_theo_ban(mon_an["id"]):
                # Nếu API thành công, tiến hành in
                mon_can_in = [mon_an]
                ket_qua = self.in_hoa_don_may_mac_dinh(so_ban=ban, mon_an=mon_can_in)
                if ket_qua:
                    self.update_data()
                else:
                    print(f"Lỗi khi in hóa đơn cho món {mon_an['ten_mat_hang']} - Bàn {ban}")
        except Exception as e:
            print(f"Lỗi khi xử lý in hóa đơn: {str(e)}")

    def update_data(self):
        """Cập nhật dữ liệu cho cả hai bảng"""
        try:
            response = requests.get(f"{URL_API}/bep/data")
            if response.status_code == 200:
                data = response.json()
                self.mon_an_theo_ban = data['left_data']
                self.update_left_table()
                self.update_right_table(data['right_data'])
                print("Đã cập nhật dữ liệu thành công")
            else:
                print(f"Lỗi khi lấy dữ liệu: {response.status_code}")
        except Exception as e:
            print(f"Lỗi khi cập nhật dữ liệu: {str(e)}")

    def update_left_table(self):
        """Cập nhật bảng bên trái với dữ liệu mới"""
        # Xóa dữ liệu cũ
        self.left_table.setRowCount(0)
        
        # Thiết lập lại số cột và tiêu đề
        self.left_table.setColumnCount(6)
        self.left_table.setHorizontalHeaderLabels(["TÊN MÓN ĂN", "SỐ LƯỢNG", "CHẾ BIẾN", "TÊN BÀN", "THỜI GIAN", "ACTION"])

        # Kiểm tra nếu không có dữ liệu
        if len(self.mon_an_theo_ban) == 0:
            self.left_table.setRowCount(1)
            no_data_item = QTableWidgetItem("Đã xong tất cả các món")
            no_data_item.setForeground(QColor("red"))
            font = QFont()
            font.setBold(True)
            no_data_item.setFont(font)
            no_data_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.left_table.setItem(0, 0, no_data_item)
            self.left_table.setSpan(0, 0, 1, 6)
            return

        # Đếm số dòng ngăn cách cần thiết
        so_dong_ngan_cach = 0
        for i in range(1, len(self.mon_an_theo_ban)):
            if self.mon_an_theo_ban[i]["ten_ban"] != self.mon_an_theo_ban[i-1]["ten_ban"]:
                so_dong_ngan_cach += 1

        # Tính tổng số hàng cần thiết
        total_rows = len(self.mon_an_theo_ban) + so_dong_ngan_cach
        self.left_table.setRowCount(total_rows)

        current_row = 0

        # Thêm dữ liệu
        for i, mon in enumerate(self.mon_an_theo_ban):
            # Thêm dòng ngăn cách nếu bàn khác với bàn trước đó (trừ bàn đầu tiên)
            if i > 0 and mon["ten_ban"] != self.mon_an_theo_ban[i-1]["ten_ban"]:
                separator_item = QTableWidgetItem("")
                separator_item.setBackground(QColor("#f39c12"))
                self.left_table.setItem(current_row, 0, separator_item)
                self.left_table.setSpan(current_row, 0, 1, 6)
                self.left_table.setRowHeight(current_row, 2)  # Giảm chiều cao xuống 2px
                current_row += 1
            
            # Tên món
            ten_mon_item = QTableWidgetItem(mon["ten_mat_hang"])
            self.left_table.setItem(current_row, 0, ten_mon_item)
            
            # Số lượng - Chuyển sang float và format lại
            so_luong = float(mon['so_luong'])
            so_luong_item = QTableWidgetItem(f"{so_luong:g} {mon['ten_don_vi']}")  # :g sẽ bỏ số 0 không cần thiết
            so_luong_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.left_table.setItem(current_row, 1, so_luong_item)
            
            # Ghi chú (Chế biến)
            ghi_chu_item = QTableWidgetItem(mon["ghi_chu"] if mon["ghi_chu"] else "")
            self.left_table.setItem(current_row, 2, ghi_chu_item)
            
            # Tên bàn
            ban_item = QTableWidgetItem(mon["ten_ban"])
            self.left_table.setItem(current_row, 3, ban_item)
            
            # Thời gian chờ
            created_at = mon["created_at"]
            thoi_gian_cho = self.tinh_thoi_gian_cho(created_at)
            thoi_gian_item = QTableWidgetItem(f"{thoi_gian_cho} phút")
            thoi_gian_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.left_table.setItem(current_row, 4, thoi_gian_item)
            
            # Nút Xong
            btn = QPushButton("Xong")
            btn.ban = mon["ten_ban"]
            # Cập nhật số lượng trong mon_an trước khi gán cho button
            mon["so_luong"] = f"{float(mon['so_luong']):g}"
            btn.mon_an = mon
            btn.clicked.connect(lambda checked, b=btn: self.print_order(b.ban, b.mon_an))
            self.left_table.setCellWidget(current_row, 5, btn)
            
            self.left_table.setRowHeight(current_row, 35)
            current_row += 1

    def tinh_thoi_gian_cho(self, created_at):
        """Tính thời gian chờ từ thời điểm tạo đơn"""
        try:
            from datetime import datetime

            # Chuyển created_at thành datetime với múi giờ UTC
            created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            # Lấy múi giờ của Việt Nam
            vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            
            # Chuyển created_time sang múi giờ Việt Nam
            created_time_vn = created_time.astimezone(vietnam_tz)
            
            # Lấy thời gian hiện tại với múi giờ Việt Nam
            now = datetime.now(vietnam_tz)
            
            # Tính khoảng thời gian
            diff = now - created_time_vn
            return int(diff.total_seconds() / 60)  # Chuyển sang phút
        except Exception as e:
            print(f"Lỗi khi tính thời gian chờ: {str(e)}")
            return 0

    def parse_ten_ban_tong_so_luong(self, ten_ban_tong_so_luong):
        """Parse chuỗi thông tin bàn và số lượng
        Input: "Bàn A11: 1 Phần, Bàn C14: 1 Phần"
        Output: [{"ten_ban": "A11", "so_luong": 1}, {"ten_ban": "C14", "so_luong": 1}]
        """
        result = []
        # Tách các bàn (phân tách bởi dấu phẩy)
        cac_ban = ten_ban_tong_so_luong.split(',')
        
        for ban in cac_ban:
            ban = ban.strip()
            if not ban:
                continue
                
            try:
                # Tách thông tin bàn và số lượng
                parts = ban.split(':')
                if len(parts) != 2:
                    continue
                    
                # Lấy số bàn (A11, C14,...)
                so_ban = parts[0].replace('Bàn', '').strip()
                
                # Lấy số lượng (1) - chỉ lấy phần số, bỏ qua đơn vị
                so_luong_str = parts[1].strip().split()[0]  # Lấy phần tử đầu tiên (số lượng)
                so_luong = float(so_luong_str)
                
                result.append({
                    "ten_ban": so_ban,
                    "so_luong": so_luong
                })
            except Exception as e:
                print(f"Lỗi khi parse thông tin bàn: {ban}, error: {str(e)}")
                
        return result

    def print_all_orders_for_item(self, mon):
        """In tất cả các đơn của một món cho tất cả các bàn"""
        try:
            # Gọi API trước
            if self.call_api_xong_mon_theo_nhom(mon["chi_tiet_ban_hang_ids"]):
                # Nếu API thành công, tiến hành in
                chi_tiet_cac_ban = self.parse_ten_ban_tong_so_luong(mon["ten_ban_tong_so_luong"])
                
                # In cho từng bàn
                for chi_tiet in chi_tiet_cac_ban:
                    mon_can_in = [{
                        "ten_mat_hang": mon["ten_mat_hang"],
                        "so_luong": chi_tiet["so_luong"],
                        "ghi_chu": "",
                        "ten_ban": "Bàn " + chi_tiet["ten_ban"]
                    }]
                    
                    # In hóa đơn cho bàn này
                    ket_qua = self.in_hoa_don_may_mac_dinh(so_ban=chi_tiet["ten_ban"], mon_an=mon_can_in)
                    if not ket_qua:
                        print(f"Lỗi khi in hóa đơn cho món {mon['ten_mat_hang']} - Bàn {chi_tiet['ten_ban']}")
                
                # Cập nhật lại dữ liệu sau khi in xong tất cả
                self.update_data()
                    
        except Exception as e:
            print(f"Lỗi khi xử lý in tất cả đơn hàng: {str(e)}")

    def update_right_table(self, mon_an_theo_nhom):
        """Cập nhật bảng bên phải với dữ liệu mới"""
        # Xóa dữ liệu cũ
        self.right_table.setRowCount(0)
        
        # Cập nhật với dữ liệu mới
        self.right_table.setRowCount(len(mon_an_theo_nhom))
        for i, mon in enumerate(mon_an_theo_nhom):
            # Tên món
            ten_mon_item = QTableWidgetItem(mon["ten_mat_hang"])
            self.right_table.setItem(i, 0, ten_mon_item)
            
            # Số lượng
            so_luong_item = QTableWidgetItem(str(mon["tong_so_luong"]))
            so_luong_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.right_table.setItem(i, 1, so_luong_item)
            
            # Danh sách bàn
            ban_item = QTableWidgetItem(mon["ten_ban_tong_so_luong"])
            self.right_table.setItem(i, 2, ban_item)
            
            # Nút Xong tất cả
            btn = QPushButton("Xong tất cả")
            btn.mon = mon  # Lưu thông tin món vào button
            btn.clicked.connect(lambda checked, m=mon: self.print_all_orders_for_item(m))
            self.right_table.setCellWidget(i, 3, btn)
            
            # Thiết lập chiều cao cho hàng
            self.right_table.setRowHeight(i, 35)

    def play_notification_sound(self):
        """Phát âm thanh thông báo"""
        self.sound_effect.play()

    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ"""
        try:
            # Dừng WebSocket thread
            if hasattr(self, 'ws_thread'):
                self.ws_thread.stop()
                self.ws_thread.wait(1000)
                if self.ws_thread.isRunning():
                    self.ws_thread.terminate()
                    
            # Dừng IP check thread
            if hasattr(self, 'ip_thread'):
                self.ip_thread.stop()
                self.ip_thread.wait(1000)
                if self.ip_thread.isRunning():
                    self.ip_thread.terminate()
        except:
            pass
        event.accept()

    def refresh_waiting_time(self):
        """Cập nhật lại thời gian chờ mà không cần gọi API"""
        if len(self.mon_an_theo_ban) == 0:
            return
            
        for row in range(self.left_table.rowCount()):
            # Bỏ qua các dòng ngăn cách
            if self.left_table.item(row, 0) and not self.left_table.item(row, 1):
                continue
                
            # Lấy thời gian tạo từ dữ liệu gốc
            for mon in self.mon_an_theo_ban:
                if (self.left_table.item(row, 0) and 
                    self.left_table.item(row, 3) and 
                    mon["ten_mat_hang"] == self.left_table.item(row, 0).text() and
                    mon["ten_ban"] == self.left_table.item(row, 3).text()):
                    
                    # Cập nhật thời gian chờ
                    thoi_gian_cho = self.tinh_thoi_gian_cho(mon["created_at"])
                    thoi_gian_item = QTableWidgetItem(f"{thoi_gian_cho} phút")
                    thoi_gian_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.left_table.setItem(row, 4, thoi_gian_item)
                    break

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = OrderManagementWindow()
    window.show()
    sys.exit(app.exec()) 