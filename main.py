import win32print
import win32ui
from win32con import MM_TEXT
import win32con
import requests
from io import BytesIO
from PIL import Image, ImageWin  # Đảm bảo đã import ImageWin

def chia_van_ban_thanh_dong(dc, van_ban, max_width):
    """
    Chia văn bản thành các dòng phù hợp với chiều rộng tối đa
    
    Args:
        dc: Device context
        van_ban: Văn bản cần chia
        max_width: Chiều rộng tối đa cho phép
        
    Returns:
        list: Danh sách các dòng văn bản đã chia
    """
    # Nếu văn bản rỗng, trả về một mảng có một phần tử rỗng
    if not van_ban:
        return [""]
    
    # Nếu văn bản đã nằm trong giới hạn, không cần chia
    if dc.GetTextExtent(van_ban)[0] <= max_width:
        return [van_ban]
    
    # Chia văn bản thành các từ
    cac_tu = van_ban.split()
    cac_dong = []
    dong_hien_tai = ""
    
    for tu in cac_tu:
        # Thêm từ vào dòng hiện tại để kiểm tra
        dong_kiem_tra = dong_hien_tai + " " + tu if dong_hien_tai else tu
        
        # Nếu dòng kiểm tra vẫn nằm trong giới hạn, cập nhật dòng hiện tại
        if dc.GetTextExtent(dong_kiem_tra)[0] <= max_width:
            dong_hien_tai = dong_kiem_tra
        else:
            # Nếu dòng hiện tại đã có giá trị, thêm vào danh sách các dòng
            if dong_hien_tai:
                cac_dong.append(dong_hien_tai)
            
            # Kiểm tra xem từ đơn có vượt quá giới hạn không
            if dc.GetTextExtent(tu)[0] <= max_width:
                dong_hien_tai = tu
            else:
                # Nếu từ đơn vượt quá giới hạn, cần cắt từ
                tu_tam = ""
                for ky_tu in tu:
                    if dc.GetTextExtent(tu_tam + ky_tu)[0] <= max_width:
                        tu_tam += ky_tu
                    else:
                        cac_dong.append(tu_tam)
                        tu_tam = ky_tu
                
                # Thêm phần còn lại của từ (nếu có)
                if tu_tam:
                    dong_hien_tai = tu_tam
    
    # Thêm dòng cuối cùng (nếu có)
    if dong_hien_tai:
        cac_dong.append(dong_hien_tai)
    
    return cac_dong

def in_hoa_don_may_mac_dinh(so_ban="01", mon_an=None):
    if mon_an is None:
        mon_an = [{"ten": "Phở bò", "so_luong": 2, "ghi_chu": ""}]
        
    try:
        may_in_mac_dinh = win32print.GetDefaultPrinter()
        hprinter = win32print.OpenPrinter(may_in_mac_dinh)
        printer_info = win32print.GetPrinter(hprinter, 2)
        dc = win32ui.CreateDC()
        dc.CreatePrinterDC(may_in_mac_dinh)
        dc.StartDoc('Hóa đơn')
        dc.StartPage()
        
        # Lấy kích thước trang in
        page_width = dc.GetDeviceCaps(win32con.PHYSICALWIDTH)
        
        # Font sizes cho máy POS
        font_logo = win32ui.CreateFont({
            "name": "Arial",
            "height": 28,
            "weight": 700,
        })
        
        font_dia_chi = win32ui.CreateFont({
            "name": "Arial",
            "height": 16,
            "weight": 400,
        })
        
        font_tieu_de = win32ui.CreateFont({
            "name": "Arial",
            "height": 22,
            "weight": 700,
        })
        
        font_bang = win32ui.CreateFont({
            "name": "Arial",
            "height": 18,
            "weight": 400,
        })
        
        font_chu_thich = win32ui.CreateFont({
            "name": "Arial",
            "height": 14,
            "weight": 400,
        })

        # Vị trí bắt đầu
        y_offset = 10
        
        # Logo
        dc.SelectObject(font_logo)
        logo_text = "BÉ BIỂN"
        logo_width = dc.GetTextExtent(logo_text)[0]
        x_logo = (page_width - logo_width) // 2
        dc.TextOut(x_logo, y_offset, logo_text)
        
        # Subtitle
        y_offset += 25
        subtitle_text = "SEAFOOD"
        dc.SelectObject(font_dia_chi)
        subtitle_width = dc.GetTextExtent(subtitle_text)[0]
        x_subtitle = (page_width - subtitle_width) // 2
        dc.TextOut(x_subtitle, y_offset, subtitle_text)
        
        # Địa chỉ
        y_offset += 20
        dia_chi = "Địa chỉ: 202 Võ Nguyên Giáp, TP Đà Nẵng"
        dia_chi_width = dc.GetTextExtent(dia_chi)[0]
        x_dia_chi = (page_width - dia_chi_width) // 2
        dc.TextOut(x_dia_chi, y_offset, dia_chi)
        
        # Điện thoại
        y_offset += 20
        dien_thoai = "Điện thoại: 0935.618.949 (Hotline) - 02362.800.777"
        dien_thoai_width = dc.GetTextExtent(dien_thoai)[0]
        x_dien_thoai = (page_width - dien_thoai_width) // 2
        dc.TextOut(x_dien_thoai, y_offset, dien_thoai)
        
        # Tiêu đề phiếu
        y_offset += 25
        dc.SelectObject(font_tieu_de)
        tieu_de = "PHIẾU TẠM TÍNH"
        tieu_de_width = dc.GetTextExtent(tieu_de)[0]
        x_tieu_de = (page_width - tieu_de_width) // 2
        dc.TextOut(x_tieu_de, y_offset, tieu_de)
        
        # Số bàn
        y_offset += 25
        ban_text = f"BÀN {so_ban}"
        ban_width = dc.GetTextExtent(ban_text)[0]
        x_ban = (page_width - ban_width) // 2
        dc.TextOut(x_ban, y_offset, ban_text)
        
        # Thời gian và mã số
        y_offset += 25
        dc.SelectObject(font_bang)
        from datetime import datetime
        now = datetime.now()
        ngay_gio = now.strftime("Ngày: %H:%M %d/%m/%Y")
        ma_so = now.strftime("Mã Số: %d%H%M00PN")
        dc.TextOut(30, y_offset, ngay_gio)
        y_offset += 20
        dc.TextOut(30, y_offset, ma_so)
        
        # Bảng dữ liệu
        y_offset += 25
        col_x = [30, 280, 330, 380, 480]  # Vị trí x của các cột
        
        # Header bảng
        dc.TextOut(col_x[0], y_offset, "Mặt hàng")
        dc.TextOut(col_x[1], y_offset, "SL")
        dc.TextOut(col_x[2], y_offset, "ĐVT")
        dc.TextOut(col_x[3], y_offset, "Giá")
        dc.TextOut(col_x[4], y_offset, "T.tiền")
        
        # Dữ liệu bảng
        y_offset += 20
        for mon in mon_an:
            thanh_tien = mon["so_luong"] * mon["gia"]
            dc.TextOut(col_x[0], y_offset, mon["ten"])
            dc.TextOut(col_x[1], y_offset, str(mon["so_luong"]))
            dc.TextOut(col_x[2], y_offset, mon["dvt"])
            dc.TextOut(col_x[3], y_offset, f"{mon['gia']:,}")
            dc.TextOut(col_x[4], y_offset, f"{thanh_tien:,}")
            y_offset += 20
        
        # Tổng tiền
        y_offset += 10
        tong_tien = sum(mon["so_luong"] * mon["gia"] for mon in mon_an)
        dc.TextOut(30, y_offset, "Thành Tiền:")
        dc.TextOut(col_x[4], y_offset, f"{tong_tien:,} đ")
        
        y_offset += 20
        dc.TextOut(30, y_offset, "Tiền Giảm:")
        dc.TextOut(col_x[4], y_offset, "0 đ")
        
        y_offset += 20
        dc.TextOut(30, y_offset, "T.Tiền:")
        dc.TextOut(col_x[4], y_offset, f"{tong_tien:,} đ")
        
        # Ghi chú cuối
        y_offset += 30
        dc.SelectObject(font_chu_thich)
        ghi_chu = [
            "Phiếu tạm tính chỉ có tác dụng kiểm tính",
            "Hóa đơn tính tiền chưa bao gồm viết hóa đơn Thuế",
            "Cảm ơn quý khách. Hẹn gặp lại!"
        ]
        
        for line in ghi_chu:
            line_width = dc.GetTextExtent(line)[0]
            x_line = (page_width - line_width) // 2
            dc.TextOut(x_line, y_offset, line)
            y_offset += 15
        
        # Thêm QR code từ URL - phương pháp chính xác
        try:
            # Tải ảnh QR từ URL
            qr_url = "https://img.vietqr.io/image/970415-113366668888-compact.png"
            response = requests.get(qr_url)
            qr_image = Image.open(BytesIO(response.content))
            
            # Điều chỉnh kích thước QR code
            qr_size = 200
            qr_image = qr_image.resize((qr_size, qr_size))
            
            # Tính toán vị trí để căn giữa QR code
            x_qr = (page_width - qr_size) // 2
            y_offset += 20
            
            # Cách đúng để vẽ ảnh lên Windows DC:
            dib = ImageWin.Dib(qr_image)
            
            # Lấy device context handle
            dc_handle = dc.GetHandleOutput()
            
            # Vẽ trực tiếp lên DC chính
            dib.draw(dc_handle, (x_qr, y_offset, x_qr + qr_size, y_offset + qr_size))
            
            # Cập nhật vị trí y sau khi vẽ QR
            y_offset += qr_size + 20
            
        except Exception as e:
            print(f"Lỗi khi vẽ QR code: {e}")
            import traceback
            traceback.print_exc()  # In chi tiết lỗi để debug
        
        dc.EndPage()
        dc.EndDoc()
        win32print.ClosePrinter(hprinter)
        return True
        
    except Exception as e:
        print(f"Lỗi khi in hóa đơn: {e}")
        import traceback
        traceback.print_exc()  # In chi tiết lỗi để debug
        return False

def in_hoa_don_rieng_le(so_ban="01", mon_an=None):
    """
    In mỗi món ăn thành một hóa đơn riêng biệt.
    
    Args:
        so_ban (str): Số bàn cần in hóa đơn
        mon_an (list): Danh sách các món ăn cần in, mỗi món là một dict
                      với các khóa "ten", "so_luong", và "ghi_chu"
                      
    Returns:
        bool: True nếu in thành công tất cả các hóa đơn, False nếu có lỗi
    """
    if mon_an is None:
        mon_an = [{"ten": "Phở bò", "so_luong": 2, "ghi_chu": ""}]
    
    ket_qua = True
    for mon in mon_an:
        mon_don_le = [mon]
        ket_qua_in = in_hoa_don_may_mac_dinh(so_ban=so_ban, mon_an=mon_don_le)
        if not ket_qua_in:
            ket_qua = False
            print(f"Lỗi khi in hóa đơn cho món {mon['ten']}")
    
    return ket_qua

if __name__ == "__main__":
    mon_an = [
        {
            "ten": "Lẩu Tomyum Hải Sản (Nhỏ)",
            "so_luong": 1,
            "dvt": "Phần",
            "gia": 219000,
            "ghi_chu": ""
        },
        {
            "ten": "Cơm Chiên Hải Sản",
            "so_luong": 1,
            "dvt": "Phần",
            "gia": 119000,
            "ghi_chu": ""
        },
        {
            "ten": "Tôm Sú",
            "so_luong": 0.3,
            "dvt": "Kg",
            "gia": 749000,
            "ghi_chu": ""
        },
        {
            "ten": "Khăn Lạnh",
            "so_luong": 3,
            "dvt": "Cái",
            "gia": 5000,
            "ghi_chu": ""
        },
        {
            "ten": "Nước Ngọt",
            "so_luong": 4,
            "dvt": "Lon",
            "gia": 15000,
            "ghi_chu": ""
        }
    ]
    
    # Đặt máy in PDF để test
    current_printer = win32print.GetDefaultPrinter()
    try:
        win32print.SetDefaultPrinter("Microsoft Print to PDF")
        
        # In hóa đơn
        in_hoa_don_may_mac_dinh(so_ban="D11", mon_an=mon_an)
    finally:
        # Khôi phục máy in mặc định
        win32print.SetDefaultPrinter(current_printer)
