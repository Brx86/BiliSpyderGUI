import PySimpleGUI as sg
import os, re, time, requests, threadpool


class Spyder:
    """
    定义爬虫类
    """

    # 进度条函数
    def bar(self):
        val = 50 * self.n / self.total
        text = f" {val/50:.2%}[{'='*int(val)}>{' '*(50-int(val))}] {self.n} of {self.total}\r"
        print(text, end="", flush=True)

    # 下载图片
    def downPic(self, line):
        line = line.split(",")
        url = line[1].strip()
        file_type = url.split(".")[-1]
        file_name = f"{line[0]}.{file_type}"
        raw = self.session.get(url)
        # 保存文件
        with open(f"{self.uid}/{file_name}", "wb+") as f:
            f.write(raw.content)
        self.n += 1
        # 打印进度条
        self.bar()

    # 创建下载任务
    def downTask(self):
        self.n = 0
        start_time = time.time()
        if not os.path.exists(self.uid):
            os.mkdir(self.uid)
        with open(f"{self.uid}.txt", "r") as f:
            pic_list = f.readlines()
        self.total = len(pic_list)
        # 创建任务，使用进程池
        pool = threadpool.ThreadPool(8)
        task_list = threadpool.makeRequests(self.downPic, pic_list)
        [pool.putRequest(task) for task in task_list]
        pool.wait()
        cost = time.time() - start_time
        print(f"\n全部图片下载完成, 用时{cost:.2f}秒!")

    # 定义页面生成器
    def getPage(self):
        p, offset = 0, ""
        while 1:
            p += 1
            params = {
                "host_uid": self.uid,
                "need_top": 1,
                "offset_dynamic_id": offset,
            }
            # 获取当前页面数据
            page = self.session.get(
                "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history",
                params=params,
                timeout=5,
            ).json()["data"]
            # 通过偏移值推算下一页地址
            offset = page["next_offset"]
            if page["has_more"]:
                print(f"正在处理第{p}页, 下一页offset为{offset}")
                # 暂时返回页面数据
                yield page["cards"]
            else:
                print(f"共{p-1}页, 爬取完成!")
                break

    # 获取下载地址
    def getCard(self):
        num = 0
        page_gen = self.getPage()
        partten = re.compile(r"album\\/([0-9A-z]{40}).(jpg|png|gif)")
        # 遍历生成页面
        for page in page_gen:
            for card in page:
                # 处理页面，获得图片列表
                img_list = partten.findall(str(card["card"]))
                if img_list:
                    x = 0
                    tTime = time.strftime(
                        "%Y%m%d%H%M%S", time.localtime(card["desc"]["timestamp"])
                    )
                    # 保存下载地址列表
                    for img in img_list:
                        x += 1
                        num += 1
                        pic = f"{img[0]}.{img[1]}"
                        with open(f"{self.uid}.txt", "a+") as f:
                            f.write(
                                f"{tTime}-{x},http://i0.hdslb.com/bfs/album/{pic}\n"
                            )
        if num:
            print(f"总共有{num}张图片!")
        else:
            print("该用户动态没有图片!")

    # 运行爬虫
    def run(self, folder_path, uid):
        self.uid = uid
        self.session = requests.session()
        os.chdir(folder_path)
        # 删除重复列表
        if os.path.exists(f"{uid}.txt"):
            os.remove(f"{uid}.txt")
        self.getCard()
        self.downTask()


class BaseGUI(object):
    """
    基本的一个pysimplegui界面类
    """

    def __init__(self):
        # 设置pysimplegui主题，不设置的话就用默认主题
        sg.ChangeLookAndFeel("BlueMono")
        # 字体和字体大小
        self.FONT = ("微软雅黑", 16)
        # 可视化界面上元素的大小
        self.SIZE = (20, 1)
        # 界面布局
        self.layout = (
            [
                # sg.Image()插入图片，支持gif和png
                [
                    sg.Image(
                        filename="ff.png",
                        pad=(150, 0),
                    )
                ],
                # sg.Text()显示文本
                # sg.Input()是输入框
                [sg.Text("")],
                [
                    sg.Text(" 请输入用户UID:", font=self.FONT, size=self.SIZE),
                    sg.Input(key="_UID_", font=self.FONT, size=(20, 1)),
                ],
                [
                    sg.Text(" 用户名:", font=self.FONT, size=self.SIZE),
                    sg.Input(
                        key="_USERNAME_", font=self.FONT, size=(20, 1), readonly=True
                    ),
                ],
                # 添加选择文件夹按钮，使用sg.FolderBrowse()
                [sg.Text(" 请选择保存文件夹：", font=self.FONT, size=(30, 1))],
                [
                    sg.Input(
                        " 默认为当前位置",
                        key="_FOLDER_",
                        readonly=True,
                        text_color="gray",
                        size=(36, 1),
                        font=self.FONT,
                    ),
                    sg.FolderBrowse(button_text="选择文件夹", size=(10, 1), font=self.FONT),
                ],
                # sg.Btn()是按钮
                [sg.Btn("开始下载", key="_START_", font=self.FONT, size=(20, 1))],
                # sg.Output()可以在程序运行时，将原本在控制台上显示的内容输出到一个图形文本框里（如print命令的输出）
                [
                    sg.Output(
                        size=(72, 6), font=("微软雅黑", 10), background_color="light gray"
                    )
                ],
            ],
        )
        # 创建窗口，引入布局，定义名称，并进行初始化
        self.window = sg.Window("Bilibili动态图片爬虫", layout=self.layout, finalize=True)

    # 获取用户名
    def getName(self, uid):
        userApi = f"https://api.bilibili.com/x/web-interface/card?mid={uid}"
        try:
            up = requests.get(userApi).json()["data"]["card"]["name"]
        except TypeError:
            print("该用户不存在!")
        return up

    # 窗口持久化
    def run(self):
        # 创建一个事件循环，否则窗口运行一次就会被关闭
        while True:
            # 监控窗口情况
            event, value = self.window.Read()
            # 当获取到事件时，处理逻辑（按钮绑定事件，点击按钮即触发事件）
            if event == "_START_":
                folder_path = value["_FOLDER_"]
                uid = value["_UID_"]
                # 获取到这些信息后，就可以进行处理了。
                # 处理完毕，若要返回结果到图形界面上,使用self.window.Element().Updata()进行更新：
                up_name = self.getName(uid)
                self.window.Element("_USERNAME_").Update(up_name)
                # 使用print()让sg.Output()捕获信息，直接print就可以了。哪里print都可以。
                if folder_path == " 默认为当前位置":
                    folder_path = "."
                else:
                    print(f"保存路径:{folder_path}")
            # 运行爬虫，获取图片
            spyder = Spyder()
            spyder.run(folder_path, uid)
            # 如果事件的值为 None，表示点击了右上角的关闭按钮，则会退出窗口循环
            if event is None:
                break
        self.window.close()


if __name__ == "__main__":
    # 实例化后运行
    tablegui = BaseGUI()
    tablegui.run()
