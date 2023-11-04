from pythonosc.udp_client import SimpleUDPClient
from pythonosc import dispatcher as dp
from pythonosc import osc_server
import time
import sqlite3, re, threading, sys
from pathlib import Path

Om = None

# 连接本地 VRCHAT 的 OSC 服务器
server_IP = "127.0.0.1"
client_port = 9000  # 连接 VRChat OSC 的端口
server_port = 9001  # VRChat 发数据到本程序的端口

# 只关注这些地址，通过映射判断
watch_addresses = {"/avatar/parameters/MuteSelf",
                   "/avatar/change",
                   "/avatar/parameters/AFK",
                   }


# 接收信息
def handle_osc_query(address: str, *args):
    _status = {
        "address": address,
        "message": args[0]
    }

    # print(_status)
    # 如果是上面值得关注的地址的话，再处理
    if address in watch_addresses:
        message = process_message(methods="OSC", message=_status)
        Om.send(message)


# 预处理信息
def process_message(methods, **kwargs):
    print(kwargs)
    # 处理 VRChat 发过来的信息
    if methods == 'OSC':
        _status = kwargs['message']
        match _status['address']:
            case '/avatar/parameters/MuteSelf':
                if _status['message']:
                    return '我先关麦克风啦！'
                else:
                    return '我开麦了！'
            case '/avatar/change':
                return "我要换模型啦！"
            case '/avatar/parameters/AFK':
                if _status['message']:
                    return '先摆烂一会，稍后回来ε=ε=ε=(~￣▽￣)~ '
                else:
                    return "我回来了！"
    # 处理 VRCX 的 EVENT 信息
    elif methods == "VRCX":
        mes = kwargs['message']
        if re.match(r'Unsupported URL', mes):
            Om.send(message="视频地址似乎出错，我看不到视频...")
        elif re.match(r'Unable to download', mes):
            Om.send(message="我似乎没法看到该视频...")


# 实时观察 VRCX 的日志
class watch_VRCX:
    def __init__(self):
        self.file = Path(r"VRCX.sqlite3")
        self.conn = sqlite3.connect(self.file, uri=True, check_same_thread=False)
        self.cursor = self.conn.cursor()

    def watch_event(self):
        last_data = None

        while True:
            # 查看 Event 事件
            self.cursor.execute("SELECT data FROM gamelog_event ORDER BY created_at DESC LIMIT 1")
            latest_data = self.cursor.fetchone()

            # 如果上一个事件与现在的时间内容不同的话
            if latest_data != last_data:
                # 数据发生变化，触发你的函数
                if latest_data:
                    process_message(methods="VRCX", message=latest_data[0])  # 调用你的函数，传递最新数据

                last_data = latest_data

            # 一些等待时间，避免不必要的循环
            time.sleep(3)


class OSC_message:
    def __init__(self, client):
        self.client = client

    def send(self, message):
        print(f" - 发送消息到 Chatbox: {message}")
        self.client.send_message('/chatbox/input', [message, True])
        time.sleep(3)
        self.client.send_message('/chatbox/input', ["", True])


def main():
    global Om
    # 创建客户端，接收 OSC 信息
    client = SimpleUDPClient(server_IP, client_port)
    Om = OSC_message(client)
    print("已创建客户端")

    # 创建调度者
    dispatcher = dp.Dispatcher()
    dispatcher.map("/avatar/*", handle_osc_query)

    # 监控 VRCX 事件日志
    VRCX = watch_VRCX()
    thread = threading.Thread(target=VRCX.watch_event)
    thread.start()
    print('正在观察 VRCX 的日志...')

    # 创建服务端，侦听来自 VRChat 的消息
    server = osc_server.ThreadingOSCUDPServer((server_IP, server_port), dispatcher)
    print("已创建服务端")
    Om.send("我的小工具成功与 VRChat-OSC 建立连接啦！")
    try:
        server.serve_forever()
    except KeyboardInterrupt as e:
        Om.send("我的小工具下线了")
        time.sleep(3)
        sys.exit()


if __name__ == '__main__':
    main()
