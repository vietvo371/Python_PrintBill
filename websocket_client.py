import asyncio
from websockets.sync.client import connect
import json

def listen_to_socket():
    uri = "ws://127.0.0.1:8080/app/hioxd1v9gttoxqpkmzkb"
    
    while True:
        try:
            with connect(uri) as websocket:
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
                
                while True:
                    try:
                        # Nhận message từ server
                        message = websocket.recv()
                        
                        # Parse JSON message
                        try:
                            data = json.loads(message)
                            
                            # Kiểm tra nếu là message từ kênh in-bep
                            if "event" in data and data["event"] == "in-bep":
                                print("Nhận được lệnh in từ bếp:", data["data"])
                                # TODO: Xử lý in ở đây
                            else:
                                print("Nhận được dữ liệu:", data)
                                
                        except json.JSONDecodeError:
                            print("Dữ liệu không phải JSON:", message)
                            
                    except Exception as e:
                        print(f"Lỗi khi nhận dữ liệu: {str(e)}")
                        break
                        
        except Exception as e:
            print(f"Lỗi kết nối: {str(e)}")
            
        print("Đang thử kết nối lại sau 5 giây...")
        import time
        time.sleep(5)

if __name__ == "__main__":
    print("Bắt đầu lắng nghe WebSocket...")
    listen_to_socket()
