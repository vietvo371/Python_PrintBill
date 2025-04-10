import win32print
import win32ui
import win32con
import win32gui
from PIL import Image, ImageWin, ImageDraw, ImageFont
import requests
from io import BytesIO
import tempfile
import os
from datetime import datetime
import qrcode
import unicodedata
import barcode
from barcode.writer import ImageWriter
import time

def remove_accents(input_str):
    """
    Loại bỏ dấu tiếng Việt, giữ nguyên chữ cái
    """
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def in_hoa_don_qua_hinh_anh(so_ban="D11", mon_an=None):
    """
    Tạo hóa đơn dạng hình ảnh, rồi in hình ảnh đó qua máy in.
    Hóa đơn được định dạng giống mẫu nhà hàng Bé Biển Seafood.
    """
    if mon_an is None:
        mon_an = [
            {"ten": "Lẩu Tomyum Hải Sản (Nhỏ)", "so_luong": 1, "dvt": "Phần", "gia": 219000},
            {"ten": "Cơm Chiên Hải Sản", "so_luong": 1, "dvt": "Phần", "gia": 119000}, 
            {"ten": "Tôm Sú", "so_luong": 0.3, "dvt": "Kg", "gia": 749000},
            {"ten": "Khăn Lạnh", "so_luong": 3, "dvt": "Cái", "gia": 5000},
            {"ten": "Nước Ngọt", "so_luong": 4, "dvt": "Lon", "gia": 15000}
        ]
    
    try:
        # Lấy thông tin thời gian và mã số
        now = datetime.now()
        ngay_gio = now.strftime("%H:%M %d/%m/%Y")
        ma_so = now.strftime("%d%m%Y00PN")
        
        # Tính tổng tiền
        tong_tien = sum(mon["so_luong"] * mon["gia"] for mon in mon_an)
        
        # Tạo hình ảnh hóa đơn
        # Kích thước hóa đơn chuẩn cho máy in K80 (80mm)
        # 1mm = ~8 pixels ở 203 dpi (máy in nhiệt thường dùng 203 dpi)
        # Chiều rộng giấy 80mm ~ 640 pixels
        width = 600  # Giảm kích thước xuống để phù hợp với máy in
        height = 1200
        
        # Tạo hình ảnh trắng
        img = Image.new('RGB', (width, height), color='white')
        d = ImageDraw.Draw(img)
        
        # Tải font
        try:
            # Thử tải font Arial
            font_title = ImageFont.truetype("arial.ttf", 28)
            font_header = ImageFont.truetype("arial.ttf", 20)
            font_normal = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            # Nếu không có, dùng font mặc định
            font_title = ImageFont.load_default()
            font_header = ImageFont.load_default()
            font_normal = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Tiêu đề
        title_text = "BÉ BIỂN"
        title_width = d.textlength(title_text, font=font_title)
        d.text(((width - title_width) / 2, 40), title_text, font=font_title, fill='black')
        
        subtitle_text = "SEAFOOD"
        subtitle_width = d.textlength(subtitle_text, font=font_header)
        d.text(((width - subtitle_width) / 2, 75), subtitle_text, font=font_header, fill='black')
        
        # Địa chỉ và số điện thoại
        address_text = "Địa chỉ: 202 Võ Nguyên Giáp, TP Đà Nẵng"
        address_width = d.textlength(address_text, font=font_normal)
        d.text(((width - address_width) / 2, 105), address_text, font=font_normal, fill='black')
        
        phone_text = "Điện thoại: 0935.618.949 (Hotline) - 02362.800.777"
        phone_width = d.textlength(phone_text, font=font_normal)
        d.text(((width - phone_width) / 2, 130), phone_text, font=font_normal, fill='black')
        
        # Tiêu đề hóa đơn
        bill_title = "PHIẾU TẠM TÍNH"
        bill_title_width = d.textlength(bill_title, font=font_title)
        d.text(((width - bill_title_width) / 2, 170), bill_title, font=font_title, fill='black')
        
        # Số bàn
        table_text = f"BÀN {so_ban}"
        table_width = d.textlength(table_text, font=font_title)
        d.text(((width - table_width) / 2, 205), table_text, font=font_title, fill='black')
        
        # Ngày giờ và mã số
        date_text = f"Ngày: {ngay_gio}"
        d.text((20, 250), date_text, font=font_normal, fill='black')
        
        code_text = f"Mã Số: {ma_so}"
        code_width = d.textlength(code_text, font=font_normal)
        d.text((width - code_width - 20, 250), code_text, font=font_normal, fill='black')
        
        # Vẽ bảng
        y_start = 290
        table_margin = 20
        table_width = width - 2 * table_margin
        
        # Định nghĩa độ rộng các cột
        col_item_width = int(table_width * 0.45)
        col_qty_width = int(table_width * 0.1)
        col_unit_width = int(table_width * 0.15)
        col_price_width = int(table_width * 0.15)
        col_total_width = table_width - col_item_width - col_qty_width - col_unit_width - col_price_width
        
        # Tính toán vị trí x của các cột
        x_item = table_margin
        x_qty = x_item + col_item_width
        x_unit = x_qty + col_qty_width
        x_price = x_unit + col_unit_width
        x_total = x_price + col_price_width
        
        # Chiều cao dòng tiêu đề
        header_height = 30
        
        # Vẽ khung bảng và tiêu đề
        # Viền ngoài
        d.rectangle((x_item, y_start, x_item + table_width, y_start + header_height), outline='black', width=1)
        
        # Đường dọc giữa các cột
        d.line((x_qty, y_start, x_qty, y_start + header_height), fill='black', width=1)
        d.line((x_unit, y_start, x_unit, y_start + header_height), fill='black', width=1)
        d.line((x_price, y_start, x_price, y_start + header_height), fill='black', width=1)
        d.line((x_total, y_start, x_total, y_start + header_height), fill='black', width=1)
        
        # Viết tiêu đề cột
        # Căn giữa chữ trong ô
        item_text = "Mặt hàng"
        item_text_width = d.textlength(item_text, font=font_header)
        item_text_x = x_item + (col_item_width - item_text_width) / 2
        d.text((item_text_x, y_start + 5), item_text, font=font_header, fill='black')
        
        qty_text = "SL"
        qty_text_width = d.textlength(qty_text, font=font_header)
        qty_text_x = x_qty + (col_qty_width - qty_text_width) / 2
        d.text((qty_text_x, y_start + 5), qty_text, font=font_header, fill='black')
        
        unit_text = "ĐVT"
        unit_text_width = d.textlength(unit_text, font=font_header)
        unit_text_x = x_unit + (col_unit_width - unit_text_width) / 2
        d.text((unit_text_x, y_start + 5), unit_text, font=font_header, fill='black')
        
        price_text = "Giá"
        price_text_width = d.textlength(price_text, font=font_header)
        price_text_x = x_price + (col_price_width - price_text_width) / 2
        d.text((price_text_x, y_start + 5), price_text, font=font_header, fill='black')
        
        total_text = "T.tiền"
        total_text_width = d.textlength(total_text, font=font_header)
        total_text_x = x_total + (col_total_width - total_text_width) / 2
        d.text((total_text_x, y_start + 5), total_text, font=font_header, fill='black')
        
        # Vẽ dữ liệu món ăn
        y_current = y_start + header_height
        row_height = 50
        
        for mon in mon_an:
            # Tính thành tiền
            thanh_tien = mon["so_luong"] * mon["gia"]
            
            # Vẽ viền ô
            d.rectangle((x_item, y_current, x_item + table_width, y_current + row_height), outline='black', width=1)
            
            # Vẽ đường dọc giữa các cột
            d.line((x_qty, y_current, x_qty, y_current + row_height), fill='black', width=1)
            d.line((x_unit, y_current, x_unit, y_current + row_height), fill='black', width=1)
            d.line((x_price, y_current, x_price, y_current + row_height), fill='black', width=1)
            d.line((x_total, y_current, x_total, y_current + row_height), fill='black', width=1)
            
            # Điền dữ liệu vào ô
            # Tên món
            d.text((x_item + 5, y_current + 15), mon["ten"], font=font_normal, fill='black')
            
            # Số lượng (căn giữa)
            sl_text = str(mon["so_luong"])
            sl_text_width = d.textlength(sl_text, font=font_normal)
            sl_text_x = x_qty + (col_qty_width - sl_text_width) / 2
            d.text((sl_text_x, y_current + 15), sl_text, font=font_normal, fill='black')
            
            # Đơn vị tính (căn giữa)
            dvt_text = mon["dvt"]
            dvt_text_width = d.textlength(dvt_text, font=font_normal)
            dvt_text_x = x_unit + (col_unit_width - dvt_text_width) / 2
            d.text((dvt_text_x, y_current + 15), dvt_text, font=font_normal, fill='black')
            
            # Giá (căn phải)
            gia_text = f"{mon['gia']:,}"
            gia_text_width = d.textlength(gia_text, font=font_normal)
            gia_text_x = x_price + col_price_width - gia_text_width - 5
            d.text((gia_text_x, y_current + 15), gia_text, font=font_normal, fill='black')
            
            # Thành tiền (căn phải)
            tt_text = f"{int(thanh_tien):,}"
            tt_text_width = d.textlength(tt_text, font=font_normal)
            tt_text_x = x_total + col_total_width - tt_text_width - 5
            d.text((tt_text_x, y_current + 15), tt_text, font=font_normal, fill='black')
            
            # Tăng vị trí y cho dòng tiếp theo
            y_current += row_height
        
        # Thêm phần tổng tiền
        y_current += 20
        
        thanh_tien_text = f"Thành Tiền: {int(tong_tien):,} đ"
        thanh_tien_width = d.textlength(thanh_tien_text, font=font_header)
        d.text(((width - thanh_tien_width) / 2, y_current), thanh_tien_text, font=font_header, fill='black')
        
        y_current += 30
        tien_giam_text = f"Tiền Giảm: 0 đ"
        tien_giam_width = d.textlength(tien_giam_text, font=font_header)
        d.text(((width - tien_giam_width) / 2, y_current), tien_giam_text, font=font_header, fill='black')
        
        y_current += 30
        tong_tien_text = f"T.Tiền: {int(tong_tien):,} đ"
        tong_tien_width = d.textlength(tong_tien_text, font=font_header)
        d.text(((width - tong_tien_width) / 2, y_current), tong_tien_text, font=font_header, fill='black')
        
        # Tạo mã QR
        y_current += 50
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=4,
        )
        qr.add_data("https://bebienseafood.com")
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((150, 150))
        
        # Paste mã QR vào hình chính
        qr_x = (width - qr_img.width) // 2
        img.paste(qr_img, (qr_x, y_current))
        
        # Thêm chú thích và lời cảm ơn
        y_current += qr_img.height + 20
        
        note1 = "Phiếu tạm tính chỉ có tác dụng kiểm tính"
        note1_width = d.textlength(note1, font=font_small)
        d.text(((width - note1_width) / 2, y_current), note1, font=font_small, fill='black')
        
        y_current += 20
        note2 = "Hóa đơn tính tiền chưa bao gồm viết hóa đơn Thuế"
        note2_width = d.textlength(note2, font=font_small)
        d.text(((width - note2_width) / 2, y_current), note2, font=font_small, fill='black')
        
        y_current += 20
        thanks = "Cảm ơn quý khách. Hẹn gặp lại!"
        thanks_width = d.textlength(thanks, font=font_small)
        d.text(((width - thanks_width) / 2, y_current), thanks, font=font_small, fill='black')
        
        # Thêm mã vạch ở cuối
        y_current += 30
        
        # Tạo mã vạch
        barcode_writer = ImageWriter()
        ean = barcode.get('code128', ma_so, writer=barcode_writer)
        
        # Lưu tạm mã vạch
        barcode_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        ean.write(barcode_file.name)
        barcode_file.close()
        
        # Đọc mã vạch từ file và paste vào hình chính
        barcode_img = Image.open(barcode_file.name)
        barcode_img = barcode_img.resize((300, 60))
        
        barcode_x = (width - barcode_img.width) // 2
        img.paste(barcode_img, (barcode_x, y_current))
        
        os.unlink(barcode_file.name)  # Xóa file tạm
        
        # Cắt hình ảnh theo nội dung thực tế để không in thừa giấy
        actual_height = y_current + barcode_img.height + 30
        img = img.crop((0, 0, width, actual_height))
        
        # Lưu hình ảnh vào file tạm
        fd, image_filename = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        img.save(image_filename)
        
        # In hình ảnh
        printer_name = win32print.GetDefaultPrinter()
        print(f"Đang in qua máy in: {printer_name}")
        
        # Lấy thông số máy in
        hPrinter = win32print.OpenPrinter(printer_name)
        printer_info = win32print.GetPrinter(hPrinter, 2)
        win32print.ClosePrinter(hPrinter)
        
        # Lấy kích thước giấy in thực tế
        try:
            printer_width = win32print.GetDeviceCaps(printer_name, win32con.PHYSICALWIDTH)
            printer_height = win32print.GetDeviceCaps(printer_name, win32con.PHYSICALHEIGHT)
            print(f"Kích thước giấy in: {printer_width}x{printer_height}")
        except:
            print("Không thể lấy kích thước giấy in")
        
        # Tạo DC cho máy in
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)
        
        # Lấy độ phân giải của máy in
        printer_dpi_x = hDC.GetDeviceCaps(win32con.LOGPIXELSX)
        printer_dpi_y = hDC.GetDeviceCaps(win32con.LOGPIXELSY)
        
        # Tính toán kích thước in thực tế dựa trên DPI
        print_width = int(width * printer_dpi_x / 96)  # 96 DPI là độ phân giải màn hình thông thường
        print_height = int(img.height * printer_dpi_y / 96)
        
        # Bắt đầu công việc in
        hDC.StartDoc('Hóa đơn Bé Biển')
        hDC.StartPage()
        
        # Lấy kích thước trang in
        page_width = hDC.GetDeviceCaps(win32con.PHYSICALWIDTH)
        page_height = hDC.GetDeviceCaps(win32con.PHYSICALHEIGHT)
        
        # Tính toán vị trí để in ở giữa trang
        x_offset = max(0, (page_width - print_width) // 2)
        y_offset = 0  # Bắt đầu từ đầu trang
        
        # In hình ảnh với tỷ lệ co giãn phù hợp
        dib = ImageWin.Dib(Image.open(image_filename))
        
        # Nếu máy in có chiều rộng nhỏ hơn hình ảnh, co hình lại
        if page_width < print_width:
            scale_factor = page_width / print_width
            print_width = page_width
            print_height = int(print_height * scale_factor)
            x_offset = 0
        
        print(f"In hình với kích thước: {print_width}x{print_height}, vị trí: ({x_offset}, {y_offset})")
        dib.draw(hDC.GetHandleOutput(), (x_offset, y_offset, x_offset + print_width, y_offset + print_height))
        
        # Kết thúc trang và công việc in
        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()
        
        # Xóa file tạm
        os.unlink(image_filename)
        
        print(f"Đã in hóa đơn bàn {so_ban} qua máy in mặc định: {printer_name}")
        return True
        
    except Exception as e:
        print(f"Lỗi khi in hóa đơn: {e}")
        import traceback
        traceback.print_exc()
        return False

# Hàm in ESC/POS trực tiếp đến máy in nhiệt (phương pháp thay thế)
def in_hoa_don_truc_tiep(so_ban="D11", mon_an=None):
    """
    In hóa đơn trực tiếp đến máy in nhiệt sử dụng mã lệnh ESC/POS
    Đây là phương pháp thay thế nếu in qua hình ảnh không hoạt động
    """
    if mon_an is None:
        mon_an = [
            {"ten": "Lẩu Tomyum Hải Sản (Nhỏ)", "so_luong": 1, "dvt": "Phần", "gia": 219000},
            {"ten": "Cơm Chiên Hải Sản", "so_luong": 1, "dvt": "Phần", "gia": 119000}, 
            {"ten": "Tôm Sú", "so_luong": 0.3, "dvt": "Kg", "gia": 749000},
            {"ten": "Khăn Lạnh", "so_luong": 3, "dvt": "Cái", "gia": 5000},
            {"ten": "Nước Ngọt", "so_luong": 4, "dvt": "Lon", "gia": 15000}
        ]
    
    try:
        # Tính tổng tiền
        tong_tien = sum(mon["so_luong"] * mon["gia"] for mon in mon_an)
        
        # Format tiền
        tong_tien_format = "{:,}".format(tong_tien)
        
        # Lấy thời gian hiện tại
        now = datetime.now()
        ngay_gio = now.strftime("%H:%M %d/%m/%Y")
        ma_so = now.strftime("%d%m%Y00PN")
        
        # Lấy tên máy in
        printer_name = win32print.GetDefaultPrinter()
        print(f"Máy in mặc định: {printer_name}")
        
        # Tạo file tạm
        fd, filename = tempfile.mkstemp(suffix='.bin')
        os.close(fd)
        
        # Các mã ESC/POS
        ESC = b'\x1B'
        GS = b'\x1D'
        
        # Định dạng
        RESET = ESC + b'@'                # Khởi tạo máy in
        CENTER = ESC + b'a' + b'\x01'     # Căn giữa
        LEFT = ESC + b'a' + b'\x00'       # Căn trái
        RIGHT = ESC + b'a' + b'\x02'      # Căn phải
        BOLD_ON = ESC + b'E' + b'\x01'    # Bật chữ đậm
        BOLD_OFF = ESC + b'E' + b'\x00'   # Tắt chữ đậm
        DOUBLE_WIDTH = ESC + b'!' + b'\x20'  # Chữ gấp đôi chiều rộng
        NORMAL = ESC + b'!' + b'\x00'     # Chữ bình thường
        UNDERLINE_ON = ESC + b'-' + b'\x01' # Bật gạch chân
        UNDERLINE_OFF = ESC + b'-' + b'\x00' # Tắt gạch chân
        CUT_PAPER = GS + b'V' + b'\x42' + b'\x00' # Cắt giấy
        
        # Tạo dữ liệu
        data = bytearray()
        
        # Khởi tạo máy in
        data.extend(RESET)
        
        # Tiêu đề
        data.extend(CENTER)
        data.extend(BOLD_ON)
        data.extend(DOUBLE_WIDTH)
        data.extend("BÉ BIỂN".encode('utf-8', 'replace'))
        data.extend(b'\n')
        data.extend(NORMAL)
        data.extend(BOLD_ON)
        data.extend("SEAFOOD".encode('utf-8', 'replace'))
        data.extend(b'\n\n')
        
        # Địa chỉ
        data.extend(NORMAL)
        data.extend("Địa chỉ: 202 Võ Nguyên Giáp, TP Đà Nẵng".encode('utf-8', 'replace'))
        data.extend(b'\n')
        data.extend("Điện thoại: 0935.618.949 (Hotline) - 02362.800.777".encode('utf-8', 'replace'))
        data.extend(b'\n\n')
        
        # Tiêu đề hóa đơn
        data.extend(BOLD_ON)
        data.extend(DOUBLE_WIDTH)
        data.extend("PHIẾU TẠM TÍNH".encode('utf-8', 'replace'))
        data.extend(b'\n')
        data.extend(f"BÀN {so_ban}".encode('utf-8', 'replace'))
        data.extend(b'\n\n')
        
        # Ngày và mã số
        data.extend(NORMAL)
        data.extend(LEFT)
        data.extend(f"Ngày: {ngay_gio}".encode('utf-8', 'replace'))
        data.extend(b'\n')
        data.extend(f"Mã Số: {ma_so}".encode('utf-8', 'replace'))
        data.extend(b'\n')
        
        # Vẽ đường kẻ
        data.extend(b'-' * 42)
        data.extend(b'\n')
        
        # Tiêu đề bảng
        data.extend(BOLD_ON)
        data.extend(b'Mat hang'.ljust(20))
        data.extend(b'SL'.ljust(5))
        data.extend(b'DVT'.ljust(7))
        data.extend(b'Gia'.rjust(10))
        data.extend(b'\n')
        
        # Đường kẻ
        data.extend(b'-' * 42)
        data.extend(b'\n')
        data.extend(BOLD_OFF)
        
        # Dữ liệu món ăn
        for mon in mon_an:
            # Format tiền
            gia_format = "{:,}".format(mon["gia"])
            thanh_tien = mon["so_luong"] * mon["gia"]
            thanh_tien_format = "{:,}".format(int(thanh_tien))
            
            # Tên món (có thể quá dài)
            ten_mon = mon["ten"]
            if len(ten_mon) > 20:
                # Chia thành nhiều dòng
                data.extend(ten_mon[:20].encode('utf-8', 'replace').ljust(20))
            else:
                data.extend(ten_mon.encode('utf-8', 'replace').ljust(20))
            
            # Số lượng
            data.extend(str(mon["so_luong"]).encode('utf-8', 'replace').ljust(5))
            
            # ĐVT
            data.extend(mon["dvt"].encode('utf-8', 'replace').ljust(7))
            
            # Giá
            data.extend(gia_format.encode('utf-8', 'replace').rjust(10))
            data.extend(b'\n')
            
            # Nếu tên quá dài, in dòng tiếp
            if len(ten_mon) > 20:
                data.extend(ten_mon[20:].encode('utf-8', 'replace').ljust(20))
                data.extend(b' ' * 22)
                data.extend(b'\n')
            
            # Thành tiền
            data.extend(b' ' * 20)
            data.extend(thanh_tien_format.encode('utf-8', 'replace').rjust(22))
            data.extend(b'\n')
        
        # Kẻ đường dưới bảng
        data.extend(b'-' * 42)
        data.extend(b'\n')
        
        # Thông tin tổng tiền
        data.extend(CENTER)
        data.extend(BOLD_ON)
        data.extend(f"Thành Tiền: {tong_tien_format} đ".encode('utf-8', 'replace'))
        data.extend(b'\n')
        data.extend(f"Tiền Giảm: 0 đ".encode('utf-8', 'replace'))
        data.extend(b'\n')
        data.extend(UNDERLINE_ON)
        data.extend(f"T.Tiền: {tong_tien_format} đ".encode('utf-8', 'replace'))
        data.extend(b'\n')
        data.extend(UNDERLINE_OFF)
        data.extend(b'\n')
        
        # Ghi chú
        data.extend(NORMAL)
        data.extend("Phiếu tạm tính chỉ có tác dụng kiểm tính".encode('utf-8', 'replace'))
        data.extend(b'\n')
        data.extend("Hóa đơn tính tiền chưa bao gồm viết hóa đơn Thuế".encode('utf-8', 'replace'))
        data.extend(b'\n')
        data.extend(BOLD_ON)
        data.extend("Cảm ơn quý khách. Hẹn gặp lại!".encode('utf-8', 'replace'))
        data.extend(b'\n\n\n')
        
        # Cắt giấy
        data.extend(CUT_PAPER)
        
        # Ghi vào file tạm
        with open(filename, 'wb') as f:
            f.write(data)
        
        # In
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("BILL", None, "RAW"))
            try:
                win32print.StartPagePrinter(hPrinter)
                with open(filename, 'rb') as f:
                    content = f.read()
                win32print.WritePrinter(hPrinter, content)
                win32print.EndPagePrinter(hPrinter)
            finally:
                win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
        
        # Xóa file tạm
        os.remove(filename)
        
        print(f"Đã in hóa đơn bàn {so_ban} qua máy in mặc định")
        return True
        
    except Exception as e:
        print(f"Lỗi khi in hóa đơn: {e}")
        import traceback
        traceback.print_exc()
        return False

# Mã thử nghiệm
if __name__ == "__main__":
    mon_an = [
        {"ten": "Lẩu Tomyum Hải Sản (Nhỏ)", "so_luong": 1, "dvt": "Phần", "gia": 219000},
        {"ten": "Cơm Chiên Hải Sản", "so_luong": 1, "dvt": "Phần", "gia": 119000}, 
        {"ten": "Tôm Sú", "so_luong": 0.3, "dvt": "Kg", "gia": 749000},
        {"ten": "Khăn Lạnh", "so_luong": 3, "dvt": "Cái", "gia": 5000},
        {"ten": "Nước Ngọt", "so_luong": 4, "dvt": "Lon", "gia": 15000}
    ]
    
    # Thử phương pháp 1: In qua hình ảnh (Điều chỉnh)
    success = in_hoa_don_qua_hinh_anh(so_ban="D11", mon_an=mon_an)
    
    # Nếu không thành công, thử phương pháp 2
    if not success:
        print("Thử phương pháp in trực tiếp...")
        in_hoa_don_truc_tiep(so_ban="D11", mon_an=mon_an)